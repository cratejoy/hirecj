import { useCallback, useEffect, useRef, useState } from 'react';
import { 
  PlaygroundIncomingMessage, 
  PlaygroundOutgoingMessage,
  PlaygroundStartMsg,
  PlaygroundResetMsg,
  MessageMsg,
  CJMessageMsg,
  CJThinkingMsg,
  ConversationStartedMsg
} from '@/protocol';

interface PlaygroundConfig {
  workflow: string;
  personaId: string;
  scenarioId: string;
  trustLevel: number;
}

export function usePlaygroundChat() {
  const [messages, setMessages] = useState<CJMessageMsg[]>([]);
  const [thinking, setThinking] = useState<CJThinkingMsg | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  
  // Connection management
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/playground`;
    ws.current = new WebSocket(wsUrl);
    
    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      clearTimeout(reconnectTimeout.current);
    };
    
    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.current.onclose = (event) => {
      console.log(`WebSocket closed: code=${event.code}, reason=${event.reason}`);
      setIsConnected(false);
      setConversationStarted(false);
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = setTimeout(connect, 1000);
    };
    
    ws.current.onmessage = (event) => {
      const msg: PlaygroundOutgoingMessage = JSON.parse(event.data);
      console.log('Received message:', msg.type, msg);
      
      switch (msg.type) {
        case 'conversation_started':
          setConversationStarted(true);
          break;
          
        case 'cj_message':
          setMessages(prev => [...prev, msg]);
          setThinking(null);
          break;
          
        case 'cj_thinking':
          setThinking(msg);
          break;
          
        case 'error':
          console.error('WebSocket error:', msg.text);
          break;
          
        case 'system':
          console.log('System message:', msg.text);
          break;
          
        default:
          // TypeScript exhaustiveness check
          const _exhaustive: never = msg;
          console.log('Unknown message type:', (msg as any).type);
      }
    };
  }, []);
  
  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimeout.current);
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, []);
  
  // Action functions
  const startConversation = useCallback((config: PlaygroundConfig) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected. Current state:', ws.current?.readyState);
      // If we're in CONNECTING state, retry in a moment
      if (ws.current?.readyState === WebSocket.CONNECTING) {
        setTimeout(() => startConversation(config), 500);
      }
      return;
    }
    
    const msg: PlaygroundStartMsg = {
      type: 'playground_start',
      workflow: config.workflow,
      persona_id: config.personaId,
      scenario_id: config.scenarioId,
      trust_level: config.trustLevel
    };
    
    console.log('Sending start conversation:', msg);
    ws.current.send(JSON.stringify(msg));
    setMessages([]);
    setThinking(null);
    // Reset conversation started flag to allow re-starting
    setConversationStarted(false);
  }, []);
  
  const sendMessage = useCallback((text: string) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return;
    }
    
    const msg: MessageMsg = {
      type: 'message',
      text
    };
    
    ws.current.send(JSON.stringify(msg));
  }, []);
  
  const resetConversation = useCallback((
    reason: 'workflow_change' | 'user_clear', 
    new_workflow?: string
  ) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return;
    }
    
    const msg: PlaygroundResetMsg = {
      type: 'playground_reset',
      reason,
      new_workflow
    };
    
    console.log('Sending reset:', msg);
    ws.current.send(JSON.stringify(msg));
    setMessages([]);
    setThinking(null);
    setConversationStarted(false);
    
    // The server will close the connection after reset, so disconnect and let auto-reconnect handle it
    setTimeout(() => {
      if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
        console.log('Closing WebSocket after reset to force reconnect');
        ws.current.close();
      }
    }, 100); // Small delay to ensure reset message is sent
  }, []);
  
  // Lifecycle management
  useEffect(() => {
    connect();
    
    return () => {
      clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, [connect]);
  
  return {
    messages,
    thinking,
    isConnected,
    conversationStarted,
    startConversation,
    sendMessage,
    resetConversation
  };
}