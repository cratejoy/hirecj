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
import { debug } from '@/utils/debug';

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
  const isStartingConversation = useRef(false);
  
  // Ref to track conversation started state for immediate access
  const conversationStartedRef = useRef(false);
  
  // Debug request promise management
  const debugRequestResolvers = useRef<Map<string, (data: any) => void>>(new Map());
  
  // Subscribe to WebSocket messages
  useEffect(() => {
    const unsubscribe = subscribe((msg: PlaygroundOutgoingMessage) => {
      debug.log('📥 WebSocket message', {
        type: msg.type,
        data: msg
      });
      
      switch (msg.type) {
        case 'ping':
          // Server sends pings to keep connection alive
          // The proxy just sends these as heartbeats, doesn't expect responses
          debug.log('🎱 Received server ping (heartbeat)', msg);
          break;
          
        case 'pong':
          // Response to our client pings
          debug.log('🎱 Received pong');
          break;
          
        case 'conversation_started':
          debug.log('🎉 Conversation started!', msg);
          setConversationStarted(true);
          conversationStartedRef.current = true;  // Update ref immediately
          
          // Resolve the conversation start promise
          if (conversationStartResolver.current) {
            debug.log('✅ Resolving conversation start promise');
            conversationStartResolver.current();
            conversationStartResolver.current = null;
            conversationStartPromise.current = null;
          } else {
            debug.warn('⚠️ No conversation start resolver found');
          }
          
          // Send any queued messages
          if (messageQueue.current.length > 0) {
            debug.log(`📤 Sending ${messageQueue.current.length} queued messages`);
            const queue = [...messageQueue.current];
            messageQueue.current = [];
            queue.forEach(text => {
              debug.log('  - Sending queued message:', text);
              sendMessageInternal(text);
            });
          } else {
            debug.log('📭 No queued messages to send');
          }
          break;
          
        case 'cj_message':
          debug.log('💬 CJ message received');
          // Filter out any thinking messages before adding the new message
          setMessages(prev => [
            ...prev.filter(m => m.data.content !== 'CJ is thinking...'),
            msg
          ]);
          setThinking(null);
          break;
          
        case 'cj_thinking':
          debug.log('🤔 CJ thinking update');
          setThinking(msg);
          break;
          
        case 'error':
          debug.error('🚫 WebSocket error message:', msg);
          // If we get an error while trying to start conversation, reject the promise
          if (!conversationStarted && conversationStartResolver.current) {
            debug.log('❌ Clearing conversation start promise due to error');
            conversationStartResolver.current = null;
            conversationStartPromise.current = null;
            isStartingConversation.current = false;
          }
          break;
          
        case 'system':
          debug.log('ℹ️ System message:', msg);
          break;
          
        case 'debug_response':
          debug.log('🐛 Debug response received');
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
          debug.warn('⚠️ Unknown message type:', (msg as any).type, msg);
      }
    });

    // Clean up subscription on unmount
    return unsubscribe;
  }, [subscribe]);

  // Helper for internal message sending
  const sendMessageInternal = useCallback((text: string) => {
    const msg: MessageMsg = {
      type: 'message',
      text
    };
    
    debug.log('✅ Sending message immediately:', msg);
    
    if (!send(msg)) {
      debug.error('❌ Failed to send message');
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
    debug.group('🚀 usePlaygroundChat.startConversation');
    debug.log('Config:', config);
    debug.log('Current conversationStarted:', conversationStarted);
    debug.log('Is connected:', isConnected);
    
    // Check if already starting a conversation
    if (isStartingConversation.current && conversationStartPromise.current) {
      debug.log('⏳ Already starting conversation, returning existing promise');
      debug.groupEnd();
      return conversationStartPromise.current;
    }
    
    // Check if conversation already started
    if (conversationStartedRef.current) {
      debug.log('✅ Conversation already started');
      debug.groupEnd();
      return Promise.resolve();
    }
    
    if (!isConnected) {
      debug.error('❌ WebSocket not connected');
      debug.groupEnd();
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    // Mark as starting
    isStartingConversation.current = true;
    
    // Create a promise that resolves when conversation_started is received
    conversationStartPromise.current = new Promise<void>((resolve, reject) => {
      conversationStartResolver.current = () => {
        isStartingConversation.current = false;
        resolve();
      };
      debug.log('✅ Created conversation start promise');
      // No timeout - let the server handle timeouts
    });
    
    const msg: PlaygroundStartMsg = {
      type: 'playground_start',
      workflow: config.workflow,
      persona_id: config.personaId,
      scenario_id: config.scenarioId,
      trust_level: config.trustLevel
    };
    
    debug.log('📤 Sending playground_start message:', msg);
    
    if (!send(msg)) {
      debug.error('❌ Failed to send playground_start');
      conversationStartResolver.current = null;
      conversationStartPromise.current = null;
      isStartingConversation.current = false;
      debug.groupEnd();
      return Promise.reject(new Error('Failed to send playground_start'));
    }
    
    debug.log('🧹 Clearing messages and queue');
    setMessages([]);
    setThinking(null);
    messageQueue.current = []; // Clear any old queued messages
    
    const promise = conversationStartPromise.current;
    debug.groupEnd();
    return promise;
  }, [conversationStarted, isConnected, send]);
  
  const sendMessage = useCallback((text: string) => {
    const sendTime = new Date().toISOString();
    debug.group('📤 usePlaygroundChat.sendMessage');
    debug.log('Send time:', sendTime);
    debug.log('Text:', text);
    debug.log('Text length:', text.length);
    debug.log('Is connected:', isConnected);
    debug.log('conversationStarted:', conversationStarted);
    debug.log('conversationStartedRef:', conversationStartedRef.current);
    
    if (!isConnected) {
      debug.error('❌ WebSocket not connected');
      debug.groupEnd();
      return;
    }
    
    // If conversation hasn't started yet, queue the message
    if (!conversationStartedRef.current) {
      debug.log('⏳ Conversation not started yet, queueing message');
      messageQueue.current.push(text);
      debug.log('📬 Message queued', { queueLength: messageQueue.current.length });
      debug.groupEnd();
      return;
    }
    
    sendMessageInternal(text);
    debug.groupEnd();
  }, [conversationStarted, isConnected, sendMessageInternal]);
  
  const resetConversation = useCallback((
    reason: 'workflow_change' | 'user_clear', 
    new_workflow?: string
  ) => {
    if (!isConnected) {
      debug.error('WebSocket not connected');
      return;
    }
    
    const msg: PlaygroundResetMsg = {
      type: 'playground_reset',
      reason,
      new_workflow
    };
    
    debug.log('Sending reset:', msg);
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
    debug.group('🔍 usePlaygroundChat.requestMessageDetails');
    debug.log('Message ID:', messageId);
    
    if (!isConnected) {
      debug.error('❌ WebSocket not connected');
      debug.groupEnd();
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    // Check if we already have the data cached
    if (debugData[messageId]) {
      debug.log('✅ Returning cached debug data');
      debug.groupEnd();
      return Promise.resolve(debugData[messageId]);
    }
    
    // Create promise for this request
    const promise = new Promise<any>((resolve) => {
      debugRequestResolvers.current.set(messageId, resolve);
      // No timeout - let the server handle it
    });
    
    const msg: DebugRequestMsg = {
      type: 'debug_request',
      data: {
        type: 'message_details',
        message_id: messageId
      }
    };
    
    debug.log('📤 Sending debug request:', msg);
    if (!send(msg)) {
      debug.error('❌ Failed to send debug request');
      debugRequestResolvers.current.delete(messageId);
      return Promise.reject(new Error('Failed to send debug request'));
    }
    
    debug.groupEnd();
    return promise;
  }, [debugData, isConnected, send]);
  
  // Reset conversation state when connection is lost
  useEffect(() => {
    if (!isConnected && conversationStartedRef.current) {
      debug.log('🔄 Connection lost, resetting conversation state');
      setConversationStarted(false);
      conversationStartedRef.current = false;
      
      // Clear any pending conversation start promises
      if (conversationStartResolver.current) {
        conversationStartResolver.current = null;
        conversationStartPromise.current = null;
        isStartingConversation.current = false;
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