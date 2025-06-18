import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { logger } from '@/lib/logger';
import { WorkflowType } from '@/constants/workflow';
import { 
  OutgoingMessage, 
  IncomingMessage,
  isOutgoingMessage,
  CJMessageMsg,
  CJThinkingMsg,
  ConversationStartedMsg,
  ErrorMsg,
  SystemMsg,
  FactCheckStatusMsg,
  FactCheckStartedMsg,
  FactCheckCompleteMsg,
  FactCheckErrorMsg,
  WorkflowUpdatedMsg,
  OAuthProcessedMsg,
  DebugResponseMsg,
  DebugEventMsg,
  StartConversationData
} from '@/protocol';

const wsLogger = logger.child('websocket');

interface Message {
  id: string;
  sender: 'user' | 'cj' | 'system';
  content: string;
  timestamp: string;
  metadata?: {
    metrics?: {
      prompts: number;
      tools: number;
      time: number;
    };
    turn?: number;
    messageIndex?: number;
    factCheckAvailable?: boolean;
    isThinking?: boolean;
  };
  ui_elements?: Array<{
    id: string;
    type: string;
    provider: string;
    placeholder: string;
  }>;
}

interface Progress {
  status: 'initializing' | 'creating agent' | 'generating response' | 'using tool';
  toolsCalled?: number;
  currentTool?: string;
  elapsed?: number;
}

interface UseWebSocketChatProps {
  enabled?: boolean;
  shopSubdomain: string;
  scenario: string;
  workflow: WorkflowType;
  onError?: (error: string) => void;
  onWorkflowUpdated?: (newWorkflow: string, previousWorkflow: string) => void;
  onOAuthProcessed?: (data: any) => void;
}

type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error' | 'closed';
type ErrorType = 'connection' | 'universe_not_found' | 'timeout' | 'unknown';

interface State {
  connectionState: ConnectionState;
  messages: Message[];
  isTyping: boolean;
  progress: Progress | null;
  error: { type: ErrorType; message: string } | null;
  retryCount: number;
  conversationId: string | null;
}

export function useWebSocketChat({ 
  enabled = false,
  shopSubdomain, 
  scenario,
  workflow,
  onError,
  onWorkflowUpdated,
  onOAuthProcessed
}: UseWebSocketChatProps) {
  // Debug initial mount only
  useEffect(() => {
    wsLogger.debug('🎯 useWebSocketChat initialized', {
      enabled,
      shopSubdomain,
      scenario,
      workflow
    });
  }, []); // Empty dependency array = log only on mount
  const [state, setState] = useState<State>({
    connectionState: 'idle',
    messages: [],
    isTyping: false,
    progress: null,
    error: null,
    retryCount: 0,
    conversationId: null
  });
  
  const wsRef = useRef<WebSocket | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messageQueueRef = useRef<string[]>([]);
  const onErrorRef = useRef(onError);
  const onWorkflowUpdatedRef = useRef(onWorkflowUpdated);
  const onOAuthProcessedRef = useRef(onOAuthProcessed);
  const lastMessageTimeRef = useRef<number>(0);
  const sendTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const workflowRef = useRef(workflow);
  
  // Use environment variable with fallback to same-origin WebSocket
  const WS_BASE_URL = useMemo(() => {
    // When served from the same domain, use relative WebSocket URL
    // This ensures cookies are sent with the WebSocket upgrade request
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    
    // Default to same origin (best for cookie support)
    const defaultUrl = `${protocol}//${host}`;
    
    wsLogger.debug('Computing WebSocket URL', { 
      protocol, 
      host, 
      defaultUrl,
      envOverride: import.meta.env.VITE_WS_BASE_URL 
    });
    
    // Allow override for development, but prefer same-origin
    if (import.meta.env.VITE_WS_BASE_URL && import.meta.env.VITE_WS_BASE_URL !== '') {
      wsLogger.warn('Using WebSocket URL override - cookies may not work cross-domain', {
        override: import.meta.env.VITE_WS_BASE_URL
      });
      return import.meta.env.VITE_WS_BASE_URL;
    }
    
    return defaultUrl;
  }, []);
  
  // Update callback refs when they change
  useEffect(() => {
    onErrorRef.current = onError;
    onWorkflowUpdatedRef.current = onWorkflowUpdated;
    onOAuthProcessedRef.current = onOAuthProcessed;
  }, [onError, onWorkflowUpdated, onOAuthProcessed]);
  
  // Keep workflow ref updated
  useEffect(() => {
    workflowRef.current = workflow;
  }, [workflow]);

  // Create a stable connection key

  // Send queued messages when connected
  const flushMessageQueue = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN && messageQueueRef.current.length > 0) {
      wsLogger.debug('Flushing message queue', { count: messageQueueRef.current.length });
      
      // DEBUG TRAP 10: Check if system_event is in queue
      const hasSystemEvent = messageQueueRef.current.some(msg => {
        try {
          const parsed = JSON.parse(msg);
          return parsed.type === 'system_event';
        } catch {
          return false;
        }
      });
      
      if (hasSystemEvent) {
        console.error('🚨 DEBUG TRAP 10: Flushing message queue WITH system_event!', {
          queueLength: messageQueueRef.current.length,
          messages: messageQueueRef.current
        });
      }
      
      messageQueueRef.current.forEach(msg => {
        wsRef.current!.send(msg);
      });
      messageQueueRef.current = [];
    }
  }, []);

  // Handle WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      const handlerId = Math.random().toString(36).substring(7);
      console.log(`[Handler ${handlerId}] Processing message:`, data.type);
      
      // Validate it's an outgoing message (from server)
      if (!isOutgoingMessage(data)) {
        wsLogger.warn('Received invalid message format', { data });
        return;
      }
      
      
      wsLogger.debug('Received message', { type: data.type, data });
      
      // Log thinking tokens and tool calls for visibility
      if (data.type === 'thinking_token' && data.data?.token) {
        console.log(`🧠 Thinking: [${data.data.token.token_type}] ${data.data.token.content}`);
      } else if (data.type === 'tool_call' && data.data) {
        const status = data.data.status === 'started' ? '🔧' : '✅';
        console.log(`${status} Tool: ${data.data.tool_name} (${data.data.status})`);
      }
      
      switch (data.type) {
        case 'system':
          const systemMsg = data as SystemMsg;
          if (systemMsg.text) {
            const message: Message = {
              id: `system-${Date.now()}`,
              sender: 'system',
              content: systemMsg.text,
              timestamp: new Date().toISOString()
            };
            setState(prev => ({ ...prev, messages: [...prev.messages, message] }));
          }
          break;
          
        case 'cj_thinking':
          const thinkingMsg = data as CJThinkingMsg;
          setState(prev => ({ 
            ...prev, 
            messages: prev.messages.filter(msg => !msg.metadata?.isThinking),
            isTyping: true,
            progress: thinkingMsg.data ? {
              status: thinkingMsg.data.status as Progress['status'],
              toolsCalled: thinkingMsg.data.toolsCalled || undefined,
              currentTool: thinkingMsg.data.currentTool || undefined,
              elapsed: thinkingMsg.data.elapsed || undefined
            } : null
          }));
          break;
          
        case 'cj_message':
          const cjMsg = data as CJMessageMsg;
          const cjMessage: Message = {
            id: `cj-${Date.now()}`,
            sender: 'cj',
            content: cjMsg.data.content,
            timestamp: cjMsg.data.timestamp,
            metadata: {
              factCheckAvailable: cjMsg.data.factCheckStatus === 'available'
            },
            ui_elements: cjMsg.data.ui_elements || undefined
          };
          setState(prev => ({ 
            ...prev, 
            messages: [
              ...prev.messages.filter(msg => !msg.metadata?.isThinking),
              cjMessage
            ],
            isTyping: false,
            progress: null
          }));
          break;
          
        case 'error':
          const errorData = data as ErrorMsg;
          const errorMsg = errorData.text || 'Unknown error';
          const errorType: ErrorType = errorMsg.toLowerCase().includes('universe not found') 
            ? 'universe_not_found' 
            : 'unknown';
          
          setState(prev => ({ 
            ...prev, 
            error: { type: errorType, message: errorMsg }
          }));
          
          if (onErrorRef.current) {
            onErrorRef.current(errorMsg);
          }
          break;
          
        case 'fact_check_started':
          const factCheckStarted = data as FactCheckStartedMsg;
          wsLogger.info('Fact check started', factCheckStarted.data);
          // Update the message to show fact checking is in progress
          const messageIndex = factCheckStarted.data.messageIndex;
          setState(prev => ({
            ...prev,
            messages: prev.messages.map((msg, idx) => 
              idx === messageIndex && msg.metadata 
                ? { ...msg, metadata: { ...msg.metadata, isCheckingFacts: true } }
                : msg
            )
          }));
          break;
          
        case 'fact_check_complete':
          const factCheckComplete = data as FactCheckCompleteMsg;
          wsLogger.info('Fact check complete', factCheckComplete.data);
          // Update the message with fact check results
          const completeIndex = factCheckComplete.data.messageIndex;
          setState(prev => ({
            ...prev,
            messages: prev.messages.map((msg, idx) => 
              idx === completeIndex && msg.metadata 
                ? { 
                    ...msg, 
                    metadata: { 
                      ...msg.metadata, 
                      isCheckingFacts: false,
                      factCheckResult: factCheckComplete.data.result 
                    } 
                  }
                : msg
            )
          }));
          break;
          
        case 'fact_check_error':
          const factCheckError = data as FactCheckErrorMsg;
          wsLogger.error('Fact check error', factCheckError.data);
          // Update the message to show fact check failed
          const errorIndex = factCheckError.data.messageIndex;
          setState(prev => ({
            ...prev,
            messages: prev.messages.map((msg, idx) => 
              idx === errorIndex && msg.metadata 
                ? { 
                    ...msg, 
                    metadata: { 
                      ...msg.metadata, 
                      isCheckingFacts: false,
                      factCheckError: factCheckError.data.error 
                    } 
                  }
                : msg
            )
          }));
          break;
          
        case 'fact_check_status':
          const factCheckStatusMsg = data as FactCheckStatusMsg;
          wsLogger.info('Received fact check status', factCheckStatusMsg.data);
          break;
          
        case 'conversation_started':
          const conversationStarted = data as ConversationStartedMsg;
          wsLogger.info('Conversation started', conversationStarted.data);
          // Capture the server-assigned conversation ID
          const serverConversationId = conversationStarted.data.conversationId;
          if (serverConversationId) {
            setState(prev => ({ ...prev, conversationId: serverConversationId }));
            wsLogger.info('Captured server-assigned conversation ID', { conversationId: serverConversationId });
          }
          // Update workflow from backend's authoritative state
          const backendWorkflow = conversationStarted.data.workflow;
          if (backendWorkflow && onWorkflowUpdatedRef.current) {
            wsLogger.info('Updating workflow from conversation_started', {
              workflow: backendWorkflow,
              source: 'backend'
            });
            // Update our internal ref
            workflowRef.current = backendWorkflow as WorkflowType;
            // Notify parent component
            onWorkflowUpdatedRef.current(backendWorkflow as WorkflowType, workflowRef.current);
          }
          break;
          
        case 'workflow_updated':
          const workflowUpdated = data as WorkflowUpdatedMsg;
          const { workflow: updatedWorkflow, previous } = workflowUpdated.data;
          wsLogger.info('Workflow updated by backend', { 
            from: previous, 
            to: updatedWorkflow 
          });
          // Update our internal ref
          workflowRef.current = updatedWorkflow as WorkflowType;
          // Trigger callback to parent component
          if (onWorkflowUpdatedRef.current) {
            onWorkflowUpdatedRef.current(updatedWorkflow as WorkflowType, (previous || workflowRef.current) as WorkflowType);
          }
          break;
        
        case 'oauth_processed':
          const oauthProcessed = data as OAuthProcessedMsg;
          wsLogger.info('OAuth processed by backend', oauthProcessed.data);
          if (onOAuthProcessedRef.current) {
            onOAuthProcessedRef.current(oauthProcessed.data);
          }
          break;
        
        case 'debug_response':
          // Format and log debug response
          const debugResponse = data as DebugResponseMsg;
          const debugData = debugResponse.data;
          console.group('%c🔍 CJ Backend Debug Response', 'color: #00D4FF; font-size: 14px; font-weight: bold');
          
          if (debugData.session) {
            console.group('📊 Session Details');
            console.log('Session ID:', debugData.session.id);
            console.log('Merchant:', debugData.session.merchant);
            console.log('Workflow:', debugData.session.workflow);
            console.log('Connected At:', debugData.session.connected_at);
            console.groupEnd();
          }
          
          if (debugData.state) {
            console.group('🧠 CJ State');
            console.log('Model:', debugData.state.model);
            console.log('Temperature:', debugData.state.temperature);
            console.log('Tools Available:', debugData.state.tools_available);
            console.log('Memory Facts:', debugData.state.memory_facts);
            console.groupEnd();
          }
          
          if (debugData.metrics) {
            console.group('📈 Metrics');
            console.table(debugData.metrics);
            console.groupEnd();
          }
          
          if (debugData.prompts) {
            console.group('📝 Recent Prompts');
            debugData.prompts.forEach((prompt: any, idx: number) => {
              console.log(`[${idx + 1}] ${prompt.timestamp}:`, prompt.content?.substring(0, 200) + '...');
            });
            console.groupEnd();
          }
          
          console.groupEnd();
          break;
          
        case 'debug_event':
          // Live event streaming
          const debugEvent = data as DebugEventMsg;
          const event = debugEvent.data;
          console.log(`%c[${event.timestamp || new Date().toISOString()}]`, 'color: gray', event.type, event.data || '');
          break;
          
        case 'thinking_token':
          // Thinking tokens are logged in the enhanced logging section above
          // No additional state updates needed - just for streaming visibility
          break;
          
        case 'tool_call':
          // Tool calls are logged in the enhanced logging section above
          // No additional state updates needed - just for streaming visibility
          break;
          
        default:
          wsLogger.warn('Unknown message type', { type: data.type, data });
      }
    } catch (error) {
      wsLogger.error('Error parsing WebSocket message', error);
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    wsLogger.debug('Connect function called');
    
    // Check current state using setState callback
    setState(currentState => {
      wsLogger.debug('Checking current connection state', {
        currentState: currentState.connectionState
      });
      
      if (currentState.connectionState === 'connecting' || currentState.connectionState === 'connected') {
        wsLogger.info('Already connecting/connected, skipping', {
          state: currentState.connectionState
        });
        return currentState; // Don't change state if already connecting/connected
      }
      
      wsLogger.info('Setting state to connecting');
      return { ...currentState, connectionState: 'connecting' };
    });

    // Abort any pending operations
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;

    setState(prev => ({ ...prev, connectionState: 'connecting' }));
    wsLogger.info('🚀 Connecting to WebSocket');

    // Connection timeout
    const timeoutId = setTimeout(() => {
      if (!signal.aborted) {
        wsLogger.error('Connection timeout');
        abortControllerRef.current?.abort();
        setState(prev => ({ 
          ...prev, 
          connectionState: 'error',
          error: { type: 'timeout', message: 'Connection timeout. Please check your internet connection.' }
        }));
      }
    }, 10000);

    // Handle abort signal
    signal.addEventListener('abort', () => {
      clearTimeout(timeoutId);
      wsRef.current?.close();
    });

    const wsUrl = `${WS_BASE_URL}/ws/chat`;
    wsLogger.info('🔌 Creating WebSocket', { 
      url: wsUrl,
      baseUrl: WS_BASE_URL
    });
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      wsLogger.debug('WebSocket instance created');
    } catch (error) {
      wsLogger.error('Failed to create WebSocket', { error, wsUrl });
      setState(prev => ({ 
        ...prev, 
        connectionState: 'error',
        error: { type: 'connection', message: 'Failed to create WebSocket connection' }
      }));
      return;
    }

    wsRef.current.onopen = () => {
      if (signal.aborted) {
        wsLogger.debug('Connection aborted on open');
        return;
      }
      
      clearTimeout(timeoutId);
      wsLogger.info('✅ WebSocket connected successfully');
      setState(prev => ({ 
        ...prev, 
        connectionState: 'connected',
        error: null,
        retryCount: 0  // Reset retry count on successful connection
      }));
      
      // With the two-layer session pattern, user identity is now handled via
      // HTTP cookies set by the auth service. The WebSocket automatically
      // inherits the user context from the cookie - no session_update needed!
      
      // Small delay before sending start_conversation
      setTimeout(() => {
        // Send start_conversation message
        // Server determines everything from session
        const startData: StartConversationData = {};
        
        // Check if this is a post-OAuth redirect. If so, don't send a workflow preference.
        // The backend will determine the correct workflow from the session cookie.
        const params = new URLSearchParams(window.location.search);
        const isOAuthReturn = params.get('oauth') === 'complete';

        if (isOAuthReturn) {
          wsLogger.info('💡 Post-OAuth redirect detected. Letting backend determine workflow.');
        } else if (workflowRef.current) {
          // Include workflow if provided and not an OAuth return
          startData.workflow = workflowRef.current;
        }
        
        // Include subdomain if provided
        if (shopSubdomain) {
          startData.shop_subdomain = shopSubdomain;
        }
        
        // Debug: Log what we're sending
        wsLogger.info('📤 start_conversation data:', startData);
        wsLogger.info('📤 Current user session:', {
          shopSubdomain: localStorage.getItem('shopSubdomain'),
          shopDomain: localStorage.getItem('shopDomain')
        });
        
        const startMessage = JSON.stringify({
          type: 'start_conversation',
          data: startData
        });
        
        wsLogger.info('📤 Sending start_conversation', { 
          type: 'start_conversation',
          data: startData 
        });
        if (wsRef.current) {
          wsRef.current.send(startMessage);
        }
        
        // Flush any queued messages
        flushMessageQueue();
      }, 100); // 100ms delay to ensure session update is processed
    };

    wsRef.current.onmessage = handleMessage;

    wsRef.current.onerror = (error) => {
      if (signal.aborted) {
        wsLogger.debug('Connection aborted - ignoring error');
        return;
      }
      
      wsLogger.error('❌ WebSocket error', { 
        error,
        readyState: wsRef.current?.readyState,
        url: wsUrl
      });
      setState(prev => ({ ...prev, connectionState: 'error' }));
    };

    wsRef.current.onclose = (event) => {
      
      if (signal.aborted) {
        wsLogger.debug('Connection aborted - ignoring close');
        return;
      }
      
      wsLogger.info('🔒 WebSocket closed', { 
        code: event.code, 
        reason: event.reason,
        wasClean: event.wasClean
      });
      setState(prev => ({ 
        ...prev, 
        connectionState: 'closed',
        isTyping: false,
        progress: null
      }));
      
      // Handle reconnection in setState to access current state
      setState(prev => {
        // Reconnect if it was an unexpected close and we haven't exceeded retry limit
        if (event.code !== 1000 && event.code !== 1001 && prev.retryCount < 3) {
          const backoffDelay = Math.min(3000 * Math.pow(2, prev.retryCount), 15000);
          wsLogger.info('Scheduling reconnection', { retryCount: prev.retryCount, delay: backoffDelay });
          
          setTimeout(() => {
            if (!signal.aborted) {
              connect();
            }
          }, backoffDelay);
          
          return { ...prev, retryCount: prev.retryCount + 1 };
        } else if (prev.retryCount >= 3) {
          return { 
            ...prev, 
            error: { type: 'connection', message: 'Unable to connect after multiple attempts. Please refresh the page.' }
          };
        }
        return prev;
      });
    };
  }, [shopSubdomain, scenario, WS_BASE_URL, handleMessage, flushMessageQueue]); // Removed workflow to prevent reconnection on workflow change

  // Effect to manage connection lifecycle
  useEffect(() => {
    wsLogger.debug('🔄 Connection lifecycle effect triggered');
    
    if (enabled) {
      wsLogger.info('📞 Initiating connection');
      connect();
    } else {
      wsLogger.warn('⚠️ Connection disabled');
    }
    
    return () => {
      wsLogger.debug('🧹 Cleaning up WebSocket connection');
      abortControllerRef.current?.abort();
      if (wsRef.current) {
        wsLogger.info('🔌 Closing WebSocket', { 
          readyState: wsRef.current.readyState 
        });
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [enabled, connect]);

  // Send message function with debouncing
  const sendMessage = useCallback((text: string) => {
    // Clear any pending sends
    if (sendTimeoutRef.current) {
      clearTimeout(sendTimeoutRef.current);
    }
    
    const now = Date.now();
    const timeSinceLastMessage = now - lastMessageTimeRef.current;
    
    // Debounce rapid messages (within 100ms)
    if (timeSinceLastMessage < 100) {
      sendTimeoutRef.current = setTimeout(() => {
        sendMessage(text);
      }, 100 - timeSinceLastMessage);
      return;
    }
    
    lastMessageTimeRef.current = now;
    
    const userMessage: Message = {
      id: `user-${now}`,
      sender: 'user',
      content: text,
      timestamp: new Date().toISOString()
    };

    // Add a thinking message immediately for better UX
    const thinkingMessage: Message = {
      id: `thinking-${now}`,
      sender: 'cj',
      content: 'CJ is thinking...',
      timestamp: new Date().toISOString(),
      metadata: {
        isThinking: true
      }
    };
    
    setState(prev => ({ 
      ...prev, 
      messages: [...prev.messages, userMessage, thinkingMessage] 
    }));
    
    const wsMessage = JSON.stringify({ type: 'message', text });
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(wsMessage);
    } else {
      wsLogger.warn('WebSocket not connected, queueing message');
      messageQueueRef.current.push(wsMessage);
    }
  }, []);

  // Send fact check function
  const sendFactCheck = useCallback((messageIndex: number) => {
    const factCheckMessage = JSON.stringify({ 
      type: 'fact_check',
      data: { messageIndex }
    });
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(factCheckMessage);
    } else {
      wsLogger.warn('WebSocket not connected, cannot send fact check');
    }
  }, []);

  // Send special message function (for oauth_complete, etc)
  const sendSpecialMessage = useCallback((message: any) => {
    const wsMessage = typeof message === 'string' ? message : JSON.stringify(message);
    
    // DEBUG TRAP 7: Special message send attempt
    if (message.type === 'system_event') {
      console.error('🚨 DEBUG TRAP 7: sendSpecialMessage called for system_event!', {
        message,
        wsReadyState: wsRef.current?.readyState,
        wsReadyStateText: wsRef.current ? ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][wsRef.current.readyState] : 'NO WS',
        wsRef: !!wsRef.current
      });
    }
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsLogger.info('📤 Sending special message', { message });
      wsRef.current.send(wsMessage);
      
      // DEBUG TRAP 8: Confirm send
      if (message.type === 'system_event') {
        console.error('🚨 DEBUG TRAP 8: system_event SENT to WebSocket!', {
          sentData: wsMessage
        });
      }
    } else {
      wsLogger.warn('WebSocket not connected, queueing special message');
      messageQueueRef.current.push(wsMessage);
      
      // DEBUG TRAP 9: Message queued
      if (message.type === 'system_event') {
        console.error('🚨 DEBUG TRAP 9: system_event QUEUED (WebSocket not ready)!', {
          readyState: wsRef.current?.readyState,
          queueLength: messageQueueRef.current.length
        });
      }
    }
  }, []);

  // Clear messages function
  const clearMessages = useCallback(() => {
    setState(prev => ({ ...prev, messages: [] }));
  }, []);

  // End conversation function
  const endConversation = useCallback(() => {
    wsLogger.info('Ending conversation');
    abortControllerRef.current?.abort();
    wsRef.current?.close(1000, 'User ended conversation');
    setState({
      connectionState: 'idle',
      messages: [],
      isTyping: false,
      progress: null,
      error: null,
      retryCount: 0,
      conversationId: null
    });
  }, []);

  return {
    messages: state.messages,
    sendMessage,
    sendFactCheck,
    sendSpecialMessage,
    isConnected: state.connectionState === 'connected',
    connectionState: state.connectionState,
    isTyping: state.isTyping,
    progress: state.progress,
    conversationId: state.conversationId,
    clearMessages,
    endConversation
  };
}
