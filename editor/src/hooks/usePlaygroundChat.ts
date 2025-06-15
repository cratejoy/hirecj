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
    
    ws.current.onclose = () => {
      setIsConnected(false);
      setConversationStarted(false);
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = setTimeout(connect, 1000);
    };
    
    ws.current.onmessage = (event) => {
      const msg: PlaygroundOutgoingMessage = JSON.parse(event.data);
      
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
  
  // Placeholder return for now
  return {
    messages,
    thinking,
    isConnected,
    conversationStarted,
    // Action functions will be added in Phase 13
    startConversation: () => {},
    sendMessage: () => {},
    resetConversation: () => {}
  };
}