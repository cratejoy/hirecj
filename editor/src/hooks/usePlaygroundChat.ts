import { useCallback, useEffect, useRef, useState } from 'react';
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
import { useWebSocket } from './useWebSocket';

interface PlaygroundConfig {
  workflow: string;
  personaId: string;
  scenarioId: string;
  trustLevel: number;
}

export function usePlaygroundChat() {
  const [messages, setMessages] = useState<CJMessageMsg[]>([]);
  const [thinking, setThinking] = useState<CJThinkingMsg | null>(null);
  const [conversationStarted, setConversationStarted] = useState(false);
  const [debugData, setDebugData] = useState<Record<string, any>>({});
  
  const { isConnected, send, subscribe } = useWebSocket();
  
  // Queue for messages sent before conversation starts
  const messageQueue = useRef<string[]>([]);
  
  // Promise resolver for conversation start
  const conversationStartResolver = useRef<(() => void) | null>(null);
  const conversationStartPromise = useRef<Promise<void> | null>(null);
  
  // Ref to track conversation started state for immediate access
  const conversationStartedRef = useRef(false);
  
  // Debug request promise management
  const debugRequestResolvers = useRef<Map<string, (data: any) => void>>(new Map());
  
  // Subscribe to WebSocket messages
  useEffect(() => {
    const unsubscribe = subscribe((msg: PlaygroundOutgoingMessage) => {
      console.log('📥 WebSocket message', {
        type: msg.type,
        data: msg
      });
      
      switch (msg.type) {
        case 'ping':
          // Server sends pings to keep connection alive - we need to respond with pong
          console.log('🎱 Received server ping', msg);
          const pingData = msg as any;
          const pongResponse = {
            type: 'pong',
            timestamp: new Date().toISOString()
          };
          console.log('🏓 Sending pong response:', pongResponse);
          send(pongResponse);
          break;
          
        case 'pong':
          // Response to our client pings
          console.log('🎱 Received pong');
          break;
          
        case 'conversation_started':
          console.log('🎉 Conversation started!', msg);
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
              sendMessageInternal(text);
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
          console.error('🚫 WebSocket error message:', msg);
          // If we get an error while trying to start conversation, reject the promise
          if (!conversationStarted && conversationStartResolver.current) {
            console.log('❌ Clearing conversation start promise due to error');
            conversationStartResolver.current = null;
            conversationStartPromise.current = null;
          }
          break;
          
        case 'system':
          console.log('ℹ️ System message:', msg);
          break;
          
        case 'debug_response':
          console.log('🐛 Debug response received');
          const debugMsg = msg as DebugResponseMsg;
          const debugInfo = debugMsg.data as any;
          
          // Store in debugData state by message_id if available
          if (debugInfo.message_id) {
            setDebugData(prev => ({
              ...prev,
              [debugInfo.message_id]: debugInfo
            }));
          }
          
          // Resolve any pending promise for this debug request
          const messageId = debugInfo.message_id || debugInfo.type;
          if (messageId && typeof messageId === 'string') {
            const resolver = debugRequestResolvers.current.get(messageId);
            if (resolver) {
              resolver(debugInfo);
              debugRequestResolvers.current.delete(messageId);
            }
          }
          break;
          
        default:
          console.warn('⚠️ Unknown message type:', (msg as any).type, msg);
      }
    });

    return unsubscribe;
  }, [subscribe]);

  // Helper for internal message sending
  const sendMessageInternal = useCallback((text: string) => {
    const msg: MessageMsg = {
      type: 'message',
      text
    };
    
    console.log('✅ Sending message immediately:', msg);
    
    if (!send(msg)) {
      console.error('❌ Failed to send message');
    }
    
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
  }, [send]);
  
  
  // Action functions
  const startConversation = useCallback((config: PlaygroundConfig): Promise<void> => {
    console.group('🚀 usePlaygroundChat.startConversation');
    console.log('Config:', config);
    console.log('Current conversationStarted:', conversationStarted);
    console.log('Is connected:', isConnected);
    
    // Create a promise that resolves when conversation_started is received
    conversationStartPromise.current = new Promise<void>((resolve, reject) => {
      conversationStartResolver.current = resolve;
      console.log('✅ Created conversation start promise');
      
      // Set a timeout for the conversation start
      setTimeout(() => {
        if (conversationStartResolver.current) {
          console.error('❌ Conversation start timeout');
          conversationStartResolver.current = null;
          conversationStartPromise.current = null;
          reject(new Error('Conversation start timeout'));
        }
      }, 10000); // 10 second timeout
    });
    
    if (!isConnected) {
      console.error('❌ WebSocket not connected');
      conversationStartResolver.current = null;
      conversationStartPromise.current = null;
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    const msg: PlaygroundStartMsg = {
      type: 'playground_start',
      workflow: config.workflow,
      persona_id: config.personaId,
      scenario_id: config.scenarioId,
      trust_level: config.trustLevel
    };
    
    console.log('📤 Sending playground_start message:', msg);
    
    if (!send(msg)) {
      console.error('❌ Failed to send playground_start');
      conversationStartResolver.current = null;
      conversationStartPromise.current = null;
      return Promise.reject(new Error('Failed to send playground_start'));
    }
    
    console.log('🧹 Clearing messages and queue');
    setMessages([]);
    setThinking(null);
    messageQueue.current = []; // Clear any old queued messages
    
    const promise = conversationStartPromise.current;
    console.groupEnd();
    return promise;
  }, [conversationStarted, isConnected, send]);
  
  const sendMessage = useCallback((text: string) => {
    const sendTime = new Date().toISOString();
    console.group('📤 usePlaygroundChat.sendMessage');
    console.log('Send time:', sendTime);
    console.log('Text:', text);
    console.log('Text length:', text.length);
    console.log('Is connected:', isConnected);
    console.log('conversationStarted:', conversationStarted);
    console.log('conversationStartedRef:', conversationStartedRef.current);
    
    if (!isConnected) {
      console.error('❌ WebSocket not connected');
      console.groupEnd();
      return;
    }
    
    // If conversation hasn't started yet, queue the message
    if (!conversationStartedRef.current) {
      console.log('⏳ Conversation not started yet, queueing message');
      messageQueue.current.push(text);
      console.log('📬 Message queued', { queueLength: messageQueue.current.length });
      console.groupEnd();
      return;
    }
    
    sendMessageInternal(text);
    console.groupEnd();
  }, [conversationStarted, isConnected, sendMessageInternal]);
  
  const resetConversation = useCallback((
    reason: 'workflow_change' | 'user_clear', 
    new_workflow?: string
  ) => {
    if (!isConnected) {
      console.error('WebSocket not connected');
      return;
    }
    
    const msg: PlaygroundResetMsg = {
      type: 'playground_reset',
      reason,
      new_workflow
    };
    
    console.log('Sending reset:', msg);
    send(msg);
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
  }, [isConnected, send]);
  
  const requestMessageDetails = useCallback((messageId: string): Promise<any> => {
    console.group('🔍 usePlaygroundChat.requestMessageDetails');
    console.log('Message ID:', messageId);
    
    if (!isConnected) {
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
    const promise = new Promise<any>((resolve, reject) => {
      debugRequestResolvers.current.set(messageId, resolve);
      
      // Set timeout for debug request
      setTimeout(() => {
        if (debugRequestResolvers.current.has(messageId)) {
          debugRequestResolvers.current.delete(messageId);
          reject(new Error('Debug request timeout'));
        }
      }, 5000); // 5 second timeout
    });
    
    const msg: DebugRequestMsg = {
      type: 'debug_request',
      data: {
        type: 'message_details',
        message_id: messageId
      }
    };
    
    console.log('📤 Sending debug request:', msg);
    if (!send(msg)) {
      console.error('❌ Failed to send debug request');
      debugRequestResolvers.current.delete(messageId);
      return Promise.reject(new Error('Failed to send debug request'));
    }
    
    console.groupEnd();
    return promise;
  }, [debugData, isConnected, send]);
  
  // Reset conversation state when connection is lost
  useEffect(() => {
    if (!isConnected && conversationStartedRef.current) {
      console.log('🔄 Connection lost, resetting conversation state');
      setConversationStarted(false);
      conversationStartedRef.current = false;
      
      // Clear any pending conversation start promises
      if (conversationStartResolver.current) {
        conversationStartResolver.current = null;
        conversationStartPromise.current = null;
      }
      
      // Clear message queue
      messageQueue.current = [];
    }
  }, [isConnected]);
  
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