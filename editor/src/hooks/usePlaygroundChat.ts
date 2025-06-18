import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { 
  PlaygroundOutgoingMessage,
  PlaygroundStartMsg,
  PlaygroundResetMsg,
  MessageMsg,
  CJMessageMsg,
  CJThinkingMsg,
  DebugRequestMsg,
  DebugResponseMsg
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
  const [debugData, setDebugData] = useState<Record<string, any>>({});
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  const reconnectAttempts = useRef(0);
  
  // Queue for messages sent before conversation starts
  const messageQueue = useRef<string[]>([]);
  
  // Promise resolver for conversation start
  const conversationStartResolver = useRef<(() => void) | null>(null);
  const conversationStartPromise = useRef<Promise<void> | null>(null);
  
  // Ref to track conversation started state for immediate access
  const conversationStartedRef = useRef(false);
  
  // Debug request promise management
  const debugRequestResolvers = useRef<Map<string, (data: any) => void>>(new Map());
  
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
    console.group('🔌 usePlaygroundChat.connect');
    console.log('Current WebSocket state:', ws.current?.readyState);
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('✅ Already connected, returning');
      console.groupEnd();
      return;
    }
    
    const wsUrl = `${WS_BASE_URL}/ws/playground`;
    console.log('WebSocket URL:', wsUrl);
    console.log('Full page URL:', window.location.href);
    
    try {
      ws.current = new WebSocket(wsUrl);
      console.log('📡 WebSocket created');
    } catch (error) {
      console.error('❌ Failed to create WebSocket:', error);
      console.groupEnd();
      return;
    }
    
    ws.current.onopen = () => {
      console.log('✅ WebSocket connected successfully');
      setIsConnected(true);
      clearTimeout(reconnectTimeout.current);
      reconnectAttempts.current = 0; // Reset reconnect attempts on successful connection
      console.groupEnd();
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
      conversationStartedRef.current = false;  // Reset ref
      clearTimeout(reconnectTimeout.current);
      
      // Clear any pending conversation start promises
      if (conversationStartResolver.current) {
        conversationStartResolver.current = null;
        conversationStartPromise.current = null;
      }
      
      // Clear message queue
      messageQueue.current = [];
      
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
      console.group('📥 WebSocket message received');
      console.log('Type:', msg.type);
      console.log('Full message:', msg);
      console.log('Timestamp:', new Date().toISOString());
      
      switch (msg.type) {
        case 'conversation_started':
          console.log('🎉 Conversation started!');
          setConversationStarted(true);
          conversationStartedRef.current = true;  // Update ref immediately
          
          // Resolve the conversation start promise
          if (conversationStartResolver.current) {
            console.log('✅ Resolving conversation start promise');
            conversationStartResolver.current();
            conversationStartResolver.current = null;
            conversationStartPromise.current = null;
          } else {
            console.warn('⚠️ No conversation start resolver found');
          }
          
          // Send any queued messages
          if (messageQueue.current.length > 0) {
            console.log(`📤 Sending ${messageQueue.current.length} queued messages`);
            const queue = [...messageQueue.current];
            messageQueue.current = [];
            queue.forEach(text => {
              console.log('  - Sending queued message:', text);
              sendMessage(text);
            });
          } else {
            console.log('📭 No queued messages to send');
          }
          break;
          
        case 'cj_message':
          console.log('💬 CJ message received');
          // Filter out any thinking messages before adding the new message
          setMessages(prev => [
            ...prev.filter(m => m.data.content !== 'CJ is thinking...'),
            msg
          ]);
          setThinking(null);
          break;
          
        case 'cj_thinking':
          console.log('🤔 CJ thinking update');
          setThinking(msg);
          break;
          
        case 'error':
          console.error('🚫 WebSocket error message:', msg.text);
          // If we get an error while trying to start conversation, reject the promise
          if (!conversationStarted && conversationStartResolver.current) {
            console.log('❌ Clearing conversation start promise due to error');
            conversationStartResolver.current = null;
            conversationStartPromise.current = null;
          }
          break;
          
        case 'system':
          console.log('ℹ️ System message:', msg.text);
          break;
          
        case 'debug_response':
          console.log('🐛 Debug response received');
          const debugMsg = msg as DebugResponseMsg;
          
          // Store in debugData state by message_id if available
          if (debugMsg.data.message_id) {
            setDebugData(prev => ({
              ...prev,
              [debugMsg.data.message_id]: debugMsg.data
            }));
          }
          
          // Resolve any pending promise for this debug request
          const messageId = debugMsg.data.message_id || debugMsg.data.type;
          const resolver = debugRequestResolvers.current.get(messageId);
          if (resolver) {
            resolver(debugMsg.data);
            debugRequestResolvers.current.delete(messageId);
          }
          break;
          
        default:
          console.warn('⚠️ Unknown message type:', (msg as any).type);
      }
      console.groupEnd();
    };
  }, [WS_BASE_URL]);
  
  
  // Action functions
  const startConversation = useCallback((config: PlaygroundConfig): Promise<void> => {
    console.group('🚀 usePlaygroundChat.startConversation');
    console.log('Config:', config);
    console.log('Current conversationStarted:', conversationStarted);
    
    // Create a promise that resolves when conversation_started is received
    conversationStartPromise.current = new Promise<void>((resolve) => {
      conversationStartResolver.current = resolve;
      console.log('✅ Created conversation start promise');
    });
    
    const attemptStart = () => {
      console.log('📝 attemptStart called');
      console.log('WebSocket state:', ws.current?.readyState);
      
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
        console.error('❌ WebSocket not connected. Current state:', ws.current?.readyState);
        // If we're in CONNECTING state, retry in a moment
        if (ws.current?.readyState === WebSocket.CONNECTING) {
          console.log('⏳ WebSocket is connecting, retrying in 500ms');
          setTimeout(() => attemptStart(), 500);
        } else {
          // Reject the promise if we can't connect
          console.error('❌ Cannot connect, clearing promise');
          conversationStartResolver.current = null;
          conversationStartPromise.current = null;
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
      
      console.log('📤 Sending playground_start message:', msg);
      const msgString = JSON.stringify(msg);
      console.log('📤 Message string:', msgString);
      ws.current.send(msgString);
      
      console.log('🧹 Clearing messages and queue');
      setMessages([]);
      setThinking(null);
      messageQueue.current = []; // Clear any old queued messages
    };
    
    attemptStart();
    const promise = conversationStartPromise.current || Promise.reject(new Error('Failed to start conversation'));
    console.groupEnd();
    return promise;
  }, [conversationStarted]);
  
  const sendMessage = useCallback((text: string) => {
    console.group('📤 usePlaygroundChat.sendMessage');
    console.log('Text:', text);
    console.log('WebSocket state:', ws.current?.readyState);
    console.log('conversationStarted:', conversationStarted);
    
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('❌ WebSocket not connected');
      console.groupEnd();
      return;
    }
    
    // If conversation hasn't started yet, queue the message
    if (!conversationStartedRef.current) {
      console.log('⏳ Conversation not started yet, queueing message');
      messageQueue.current.push(text);
      console.log('📬 Message queue now has', messageQueue.current.length, 'messages');
      console.groupEnd();
      return;
    }
    
    const msg: MessageMsg = {
      type: 'message',
      text
    };
    
    console.log('✅ Sending message immediately:', msg);
    const msgString = JSON.stringify(msg);
    console.log('📤 Message string:', msgString);
    ws.current.send(msgString);
    
    // Add a thinking message to indicate CJ is processing
    const thinkingMessage: CJMessageMsg = {
      type: 'cj_message',
      data: {
        content: 'CJ is thinking...',
        timestamp: new Date().toISOString(),
        factCheckStatus: null,
        ui_elements: null
      }
    };
    setMessages(prev => [...prev, thinkingMessage]);
    
    console.groupEnd();
  }, [conversationStarted]);
  
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
    conversationStartedRef.current = false;  // Reset ref
    
    // Clear any pending conversation start promises and message queue
    if (conversationStartResolver.current) {
      conversationStartResolver.current = null;
      conversationStartPromise.current = null;
    }
    messageQueue.current = [];
    
    // The server will close the connection after reset, so disconnect and let auto-reconnect handle it
    setTimeout(() => {
      if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
        console.log('Closing WebSocket after reset to force reconnect');
        ws.current.close();
      }
    }, 100); // Small delay to ensure reset message is sent
  }, []);
  
  const requestMessageDetails = useCallback((messageId: string): Promise<any> => {
    console.group('🔍 usePlaygroundChat.requestMessageDetails');
    console.log('Message ID:', messageId);
    
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('❌ WebSocket not connected');
      console.groupEnd();
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    // Check if we already have the data cached
    if (debugData[messageId]) {
      console.log('✅ Returning cached debug data');
      console.groupEnd();
      return Promise.resolve(debugData[messageId]);
    }
    
    // Create promise for this request
    const promise = new Promise<any>((resolve) => {
      debugRequestResolvers.current.set(messageId, resolve);
    });
    
    const msg: DebugRequestMsg = {
      type: 'debug_request',
      data: {
        type: 'message_details',
        message_id: messageId
      }
    };
    
    console.log('📤 Sending debug request:', msg);
    ws.current.send(JSON.stringify(msg));
    
    console.groupEnd();
    return promise;
  }, [debugData]);
  
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
    resetConversation,
    requestMessageDetails
  };
}