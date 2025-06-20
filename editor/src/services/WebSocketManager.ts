import { PlaygroundOutgoingMessage } from '@/protocol';
import { WEBSOCKET_CONFIG } from '@/constants/websocket';
import { debug } from '@/utils/debug';

type MessageHandler = (message: PlaygroundOutgoingMessage) => void;
type ConnectionStateHandler = (state: ConnectionState) => void;

export type ConnectionState = 'disconnected' | 'connecting' | 'connected';

interface QueuedMessage {
  data: string;
  timestamp: number;
}

/**
 * Singleton WebSocket manager that handles all WebSocket connections
 * outside of React component lifecycle. This ensures a single connection
 * is maintained across the entire application, preventing duplicate
 * connections from React StrictMode or component remounts.
 * 
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Message queuing for offline sending
 * - Heartbeat/ping mechanism to keep connection alive
 * - Observable connection state
 * - Type-safe message handling
 */
export class WebSocketManager {
  private static instance: WebSocketManager | null = null;
  private ws: WebSocket | null = null;
  private messageHandlers = new Set<MessageHandler>();
  private connectionStateHandlers = new Set<ConnectionStateHandler>();
  private connectionState: ConnectionState = 'disconnected';
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private messageQueue: QueuedMessage[] = [];
  private isIntentionalClose = false;
  private wsUrl: string;


  private constructor() {
    // Compute WebSocket URL
    const backendUrl = import.meta.env.VITE_EDITOR_BACKEND_URL;
    
    try {
      if (backendUrl && backendUrl !== '') {
        const url = new URL(backendUrl);
        const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        this.wsUrl = `${wsProtocol}//${url.host}/ws/playground`;
      } else {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        this.wsUrl = `${protocol}//${host}/ws/playground`;
      }
    } catch (error) {
      debug.error('❌ Invalid backend URL configuration:', backendUrl, error);
      // Fallback to same-origin
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      this.wsUrl = `${protocol}//${host}/ws/playground`;
    }

    debug.log('🔧 WebSocketManager initialized with URL:', this.wsUrl);
  }

  static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      WebSocketManager.instance = new WebSocketManager();
    }
    return WebSocketManager.instance;
  }

  connect(): void {
    if (this.connectionState === 'connected' || this.connectionState === 'connecting') {
      debug.log('✅ WebSocket already ' + this.connectionState);
      return;
    }

    this.isIntentionalClose = false;
    this.setConnectionState('connecting');
    
    debug.log('🔌 WebSocketManager.connect', {
      url: this.wsUrl,
      attemptNumber: this.reconnectAttempts + 1
    });

    try {
      this.ws = new WebSocket(this.wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      debug.error('❌ Failed to create WebSocket:', error);
      this.handleConnectionFailure();
    }
  }

  disconnect(): void {
    debug.log('🔒 WebSocketManager.disconnect');
    this.isIntentionalClose = true;
    this.cleanup();
  }

  send(data: string | object): boolean {
    const message = typeof data === 'string' ? data : JSON.stringify(data);
    
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      debug.log('⏳ WebSocket not ready, queueing message');
      this.messageQueue.push({
        data: message,
        timestamp: Date.now()
      });
      this.cleanMessageQueue();
      return false;
    }

    try {
      this.ws.send(message);
      debug.log('📤 Message sent:', message);
      return true;
    } catch (error) {
      debug.error('❌ Failed to send message:', error);
      return false;
    }
  }

  subscribe(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  subscribeToConnectionState(handler: ConnectionStateHandler): () => void {
    this.connectionStateHandlers.add(handler);
    // Immediately call with current state
    handler(this.connectionState);
    return () => {
      this.connectionStateHandlers.delete(handler);
    };
  }

  getConnectionState(): ConnectionState {
    return this.connectionState;
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      debug.log('✅ WebSocket connected');
      this.setConnectionState('connected');
      this.reconnectAttempts = 0;
      this.startPingInterval();
      this.flushMessageQueue();
    };

    this.ws.onclose = (event) => {
      debug.log('🔒 WebSocket closed', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      
      this.setConnectionState('disconnected');
      this.stopPingInterval();

      if (!this.isIntentionalClose && this.reconnectAttempts < WEBSOCKET_CONFIG.MAX_RECONNECT_ATTEMPTS) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      debug.error('❌ WebSocket error:', error);
    };

    this.ws.onmessage = (event) => {
      try {
        const message: PlaygroundOutgoingMessage = JSON.parse(event.data);
        debug.log('📥 WebSocket message:', message);
        
        // Notify all subscribers
        this.messageHandlers.forEach(handler => {
          try {
            handler(message);
          } catch (error) {
            debug.error('Error in message handler:', error);
          }
        });
      } catch (error) {
        debug.error('Failed to parse WebSocket message:', error);
      }
    };
  }

  private setConnectionState(state: ConnectionState): void {
    if (this.connectionState !== state) {
      this.connectionState = state;
      this.connectionStateHandlers.forEach(handler => {
        try {
          handler(state);
        } catch (error) {
          debug.error('Error in connection state handler:', error);
        }
      });
    }
  }

  private startPingInterval(): void {
    // Disabled client-side ping - server handles keepalive
    // The server sends pings and expects pong responses
    // which are handled in usePlaygroundChat
    debug.log('📌 Ping interval disabled - server handles keepalive');
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private flushMessageQueue(): void {
    if (this.messageQueue.length === 0) return;

    debug.log(`📤 Flushing ${this.messageQueue.length} queued messages`);
    const messages = [...this.messageQueue];
    this.messageQueue = [];

    messages.forEach(({ data }) => {
      this.send(data);
    });
  }

  private cleanMessageQueue(): void {
    const now = Date.now();
    this.messageQueue = this.messageQueue.filter(
      msg => now - msg.timestamp < WEBSOCKET_CONFIG.MESSAGE_QUEUE_MAX_AGE
    );
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = Math.min(
      WEBSOCKET_CONFIG.INITIAL_RECONNECT_DELAY * Math.pow(2, this.reconnectAttempts - 1),
      WEBSOCKET_CONFIG.MAX_RECONNECT_DELAY
    );

    debug.log(`⏳ Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private handleConnectionFailure(): void {
    this.setConnectionState('disconnected');
    if (!this.isIntentionalClose && this.reconnectAttempts < this.MAX_RECONNECT_ATTEMPTS) {
      this.scheduleReconnect();
    }
  }

  private cleanup(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    this.stopPingInterval();

    if (this.ws) {
      if (this.ws.readyState === WebSocket.OPEN || 
          this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close(1000, 'Intentional disconnect');
      }
      this.ws = null;
    }

    this.setConnectionState('disconnected');
    this.messageQueue = [];
    this.reconnectAttempts = 0;
    
    // Clear all handlers to prevent memory leaks
    this.messageHandlers.clear();
    this.connectionStateHandlers.clear();
  }
}