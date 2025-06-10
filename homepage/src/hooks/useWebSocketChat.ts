import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { logger } from '@/lib/logger';
import { WorkflowType } from '@/constants/workflow';
import { WorkflowTransitionMessage } from '@/types/websocket';

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

interface WebSocketMessage {
  type: 'system' | 'cj_thinking' | 'cj_message' | 'error' | 'fact_check_status' | 'oauth_complete' | 'conversation_started' | 'oauth_processed' | 'workflow_updated' | 'debug_response' | 'debug_event';
  message?: string;
  text?: string;
  progress?: Progress;
  data?: any;
  error?: string;
  fact_check_status?: any;
  [key: string]: any;
}

interface UseWebSocketChatProps {
  enabled?: boolean;
  conversationId: string;
  merchantId: string;
  scenario: string;
  workflow: 'ad_hoc_support' | 'daily_briefing' | 'shopify_onboarding' | 'support_daily';
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
}

export function useWebSocketChat({ 
  enabled = false,
  conversationId, 
  merchantId, 
  scenario,
  workflow,
  onError,
  onWorkflowUpdated,
  onOAuthProcessed
}: UseWebSocketChatProps) {
  // Debug initial props
  wsLogger.debug('🎯 useWebSocketChat initialized', {
    enabled,
    conversationId,
    merchantId,
    scenario,
    workflow
  });
  const [state, setState] = useState<State>({
    connectionState: 'idle',
    messages: [],
    isTyping: false,
    progress: null,
    error: null,
    retryCount: 0
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
  
  // Use environment variable with fallback to backend default port
  const WS_BASE_URL = useMemo(() => {
    // First check for explicit WebSocket URL
    if (import.meta.env.VITE_WS_BASE_URL) {
      return import.meta.env.VITE_WS_BASE_URL;
    }
    
    // If we have an API base URL, convert it to WebSocket URL
    if (import.meta.env.VITE_API_BASE_URL) {
      const apiUrl = import.meta.env.VITE_API_BASE_URL;
      // Convert https:// to wss:// or http:// to ws://
      return apiUrl.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
    }
    
    // If we have a public URL (from ngrok), convert it to WebSocket URL
    if (import.meta.env.VITE_PUBLIC_URL) {
      const publicUrl = import.meta.env.VITE_PUBLIC_URL;
      // Convert https:// to wss:// or http:// to ws://
      return publicUrl.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
    }
    
    // Default to localhost
    return 'ws://localhost:8000';
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
  const connectionKey = useMemo(
    () => {
      wsLogger.debug('Computing connection key', {
        enabled,
        conversationId,
        merchantId,
        scenario,
        workflow
      });
      
      if (!enabled || !conversationId || !workflow) {
        wsLogger.debug('Connection key null - missing required fields', {
          enabled,
          hasConversationId: !!conversationId,
          hasWorkflow: !!workflow
        });
        return null;
      }
      
      // For onboarding and support_daily workflows, we don't need merchant/scenario
      if (workflow === 'shopify_onboarding' || workflow === 'support_daily') {
        const key = `${conversationId}`;
        wsLogger.info('Connection key for ${workflow}', { key });
        return key;
      }
      
      // For other workflows, require merchant/scenario (not empty strings)
      if (!merchantId || !scenario || merchantId === '' || scenario === '') {
        wsLogger.warn('Connection key null - missing merchant/scenario for non-onboarding workflow', {
          workflow,
          merchantId,
          scenario,
          hasMerchantId: !!merchantId && merchantId !== '',
          hasScenario: !!scenario && scenario !== ''
        });
        return null;
      }
      
      // Don't include workflow in key - we want to keep same connection during transitions
      const key = `${conversationId}-${merchantId}-${scenario}`;
      wsLogger.info('Connection key computed (workflow excluded for transitions)', { key });
      return key;
    },
    [enabled, conversationId, merchantId, scenario] // workflow removed - we don't want reconnections on workflow change
  );

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
        console.log('[WebSocket] Sending queued message:', msg);
        wsRef.current!.send(msg);
      });
      messageQueueRef.current = [];
    }
  }, []);

  // Handle WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WebSocketMessage = JSON.parse(event.data);
      wsLogger.debug('Received message', { type: data.type, data });
      
      switch (data.type) {
        case 'system':
          if (data.message || data.text) {
            const message: Message = {
              id: `system-${Date.now()}`,
              sender: 'system',
              content: data.message || data.text || '',
              timestamp: new Date().toISOString()
            };
            setState(prev => ({ ...prev, messages: [...prev.messages, message] }));
          }
          break;
          
        case 'cj_thinking':
          setState(prev => ({ 
            ...prev, 
            messages: prev.messages.filter(msg => !msg.metadata?.isThinking),
            isTyping: true,
            progress: data.progress || (data.data && 'status' in data.data ? data.data as Progress : null)
          }));
          break;
          
        case 'cj_message':
          const messageData = data.data as { content?: string; timestamp?: string; factCheckStatus?: string; ui_elements?: any[] } | undefined;
          console.log('[WebSocket] Parsing cj_message:', { messageData, fullData: data });
          const cjMessage: Message = {
            id: `cj-${Date.now()}`,
            sender: 'cj',
            content: messageData?.content || data.message || data.text || '',
            timestamp: messageData?.timestamp || new Date().toISOString(),
            metadata: {
              ...data.metadata,
              factCheckAvailable: messageData?.factCheckStatus === 'available'
            },
            ui_elements: messageData?.ui_elements
          };
          console.log('[WebSocket] Created cj_message:', cjMessage);
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
          const errorMsg = data.error || data.message || 'Unknown error';
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
          
        case 'fact_check_status':
          wsLogger.info('Received fact check status', data.fact_check_status);
          break;
          
        case 'conversation_started':
          wsLogger.info('Conversation started', data.data);
          break;
          
        case 'workflow_updated':
          const { workflow: updatedWorkflow, previous } = data.data;
          wsLogger.info('Workflow updated by backend', { 
            from: previous, 
            to: updatedWorkflow 
          });
          // Trigger callback to parent component
          if (onWorkflowUpdatedRef.current) {
            onWorkflowUpdatedRef.current(updatedWorkflow, previous);
          }
          break;
        
        case 'oauth_processed':
          wsLogger.info('OAuth processed by backend', data.data);
          if (onOAuthProcessedRef.current) {
            onOAuthProcessedRef.current(data.data);
          }
          break;
        
        case 'debug_response':
          // Format and log debug response
          const debugData = data.data;
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
          const event = data.data;
          console.log(`%c[${event.timestamp || new Date().toISOString()}]`, 'color: gray', event.type, event.data || '');
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
    wsLogger.debug('Connect function called', { 
      hasConnectionKey: !!connectionKey,
      connectionKey 
    });
    
    if (!connectionKey) {
      wsLogger.warn('Connect aborted - no connection key');
      return;
    }
    
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
    wsLogger.info('🚀 Connecting to WebSocket', { connectionKey });

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

    const wsUrl = `${WS_BASE_URL}/ws/chat/${conversationId}`;
    wsLogger.info('🔌 Creating WebSocket', { 
      url: wsUrl,
      baseUrl: WS_BASE_URL,
      conversationId 
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
      
      // Send user session info if available
      // IMPORTANT: Frontend NEVER generates user IDs - this is backend's responsibility
      // We only send raw merchant data (shop_domain, merchant_id) to the backend
      // The backend will use shared.user_identity.get_or_create_user() to generate proper IDs
      const merchantId = localStorage.getItem('merchantId');
      const shopDomain = localStorage.getItem('shopDomain');
      
      if (merchantId && shopDomain) {
        // WARNING: Do NOT attempt to generate user_id here!
        // User IDs must be generated by backend using the authoritative
        // generate_user_id() function to ensure consistency (usr_xxxxxxxx format)
        const sessionUpdate = {
          type: 'session_update',
          data: {
            merchant_id: merchantId,  // Raw merchant ID from localStorage
            shop_domain: shopDomain   // Raw shop domain from localStorage
            // NO user_id field! Backend generates this.
          }
        };
        wsLogger.info('📤 Sending session update (backend will generate user_id):', sessionUpdate);
        if (wsRef.current) {
          wsRef.current.send(JSON.stringify(sessionUpdate));
        }
      } else {
        wsLogger.info('📤 No merchant session found in localStorage');
      }
      
      // Small delay to ensure session update is processed
      setTimeout(() => {
        // Send start_conversation message
        const currentWorkflow = workflowRef.current;
        const startData = {
          conversation_id: conversationId,
          merchant_id: merchantId || ((currentWorkflow === 'shopify_onboarding' || currentWorkflow === 'support_daily') ? 'onboarding_user' : null),
          scenario: scenario || ((currentWorkflow === 'shopify_onboarding' || currentWorkflow === 'support_daily') ? 'onboarding' : null),
          workflow: currentWorkflow,
        };
        
        // DEBUG TRAP 5: start_conversation on WebSocket connect
        const urlParams = new URLSearchParams(window.location.search);
        const isOAuthReturn = urlParams.get('oauth') === 'complete';
        if (isOAuthReturn) {
          console.error('🚨 DEBUG TRAP 5: Starting conversation after OAuth!', {
            conversationId,
            merchantId: merchantId,
            workflow: currentWorkflow,
            urlParams: Object.fromEntries(urlParams.entries()),
            reason: 'WebSocket onopen handler'
          });
          alert(`DEBUG: Starting NEW conversation after OAuth!\nConversation ID: ${conversationId}`);
        }
        
        // Debug: Log what we're sending
        wsLogger.info('📤 start_conversation data:', startData);
        wsLogger.info('📤 Current user session:', {
          merchantId: localStorage.getItem('merchantId'),
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
        console.log('[WebSocket] Sending start_conversation message:', startMessage);
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
      // DEBUG TRAP 6: WebSocket close
      const urlParams = new URLSearchParams(window.location.search);
      const isOAuthReturn = urlParams.get('oauth') === 'complete';
      if (isOAuthReturn) {
        console.error('🚨 DEBUG TRAP 6: WebSocket CLOSED after OAuth!', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
          conversationId,
          urlParams: Object.fromEntries(urlParams.entries())
        });
      }
      
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
  }, [connectionKey, conversationId, merchantId, scenario, WS_BASE_URL, handleMessage, flushMessageQueue]); // Removed workflow to prevent reconnection on workflow change

  // Effect to manage connection lifecycle
  useEffect(() => {
    wsLogger.debug('🔄 Connection lifecycle effect triggered', { 
      hasConnectionKey: !!connectionKey,
      connectionKey 
    });
    
    if (connectionKey) {
      wsLogger.info('📞 Initiating connection for key:', connectionKey);
      connect();
    } else {
      wsLogger.warn('⚠️ No connection key - skipping connection');
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
  }, [connectionKey, connect]); // Only reconnect when connectionKey actually changes

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
      console.log('[WebSocket] Sending chat message:', wsMessage);
      wsRef.current.send(wsMessage);
    } else {
      console.log('[WebSocket] WebSocket not connected, queueing message:', wsMessage);
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
      console.log('[WebSocket] Sending fact check message:', factCheckMessage);
      wsRef.current.send(factCheckMessage);
    } else {
      console.log('[WebSocket] WebSocket not connected, cannot send fact check:', factCheckMessage);
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
      retryCount: 0
    });
  }, []);
  
  // Send workflow transition request
  const sendWorkflowTransition = useCallback((newWorkflow: WorkflowType) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message: WorkflowTransitionMessage = {
        type: 'workflow_transition',
        data: {
          new_workflow: newWorkflow,
          user_initiated: true
        }
      };
      wsRef.current.send(JSON.stringify(message));
      wsLogger.info('📤 Sent workflow transition request', { newWorkflow });
    } else {
      wsLogger.warn('Cannot send workflow transition - WebSocket not connected');
    }
  }, []);

  return {
    messages: state.messages,
    sendMessage,
    sendFactCheck,
    sendSpecialMessage,
    sendWorkflowTransition,
    isConnected: state.connectionState === 'connected',
    connectionState: state.connectionState,
    isTyping: state.isTyping,
    progress: state.progress,
    clearMessages,
    endConversation
  };
}
