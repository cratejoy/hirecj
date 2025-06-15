import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { 
  PlaygroundOutgoingMessage,
  PlaygroundStartMsg,
  PlaygroundResetMsg,
  MessageMsg,
  CJMessageMsg,
  CJThinkingMsg
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
  const reconnectAttempts = useRef(0);
  
  // Compute WebSocket base URL similar to homepage
  const WS_BASE_URL = useMemo(() => {
    // Check if we have a backend URL configured
    const backendUrl = import.meta.env.VITE_EDITOR_BACKEND_URL;
    
    // In proxy mode, VITE_EDITOR_BACKEND_URL is set to empty string
    if (backendUrl && backendUrl !== '') {
      // Use direct backend URL (cross-domain)
      const url = new URL(backendUrl);
      return url.protocol === 'https:' ? `wss://${url.host}` : `ws://${url.host}`;
    }
    
    // Use same-origin WebSocket (through Vite proxy)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}`;
  }, []);
  
  // Connection management
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    
    const wsUrl = `${WS_BASE_URL}/ws/playground`;
    console.log('  Full URL:', window.location.href);
    
    try {
      ws.current = new WebSocket(wsUrl);
    } catch (error) {
      console.error('❌ Failed to create WebSocket:', error);
      return;
    }
    
    ws.current.onopen = () => {
      console.log('✅ WebSocket connected successfully');
      setIsConnected(true);
      clearTimeout(reconnectTimeout.current);
      reconnectAttempts.current = 0; // Reset reconnect attempts on successful connection
    };
    
    ws.current.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      console.error('  Type:', error.type);
      console.error('  Target:', error.target);
      if (error.target) {
        console.error('  URL:', (error.target as WebSocket).url);
        console.error('  ReadyState:', (error.target as WebSocket).readyState);
      }
    };
    
    ws.current.onclose = (event) => {
      console.log(`🔒 WebSocket closed: code=${event.code}, reason=${event.reason}, wasClean=${event.wasClean}`);
      setIsConnected(false);
      setConversationStarted(false);
      clearTimeout(reconnectTimeout.current);
      
      // Different reconnect strategies based on close code
      if (event.code === 1006) {
        console.log('⚠️  Abnormal closure - likely connection refused or network error');
      }
      
      // Reconnect with exponential backoff
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
      console.log(`⏳ Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current + 1})`);
      reconnectTimeout.current = setTimeout(() => {
        reconnectAttempts.current++;
        connect();
      }, delay);
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
          console.log('Unknown message type:', (msg as any).type);
      }
    };
  }, [WS_BASE_URL]);
  
  
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
    // Set conversation started optimistically - server will confirm
    setConversationStarted(true);
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