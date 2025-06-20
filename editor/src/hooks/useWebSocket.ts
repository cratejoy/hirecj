import { useContext, useEffect } from 'react';
import { WebSocketContext } from '@/providers/WebSocketProvider';
import { PlaygroundOutgoingMessage } from '@/protocol';
import { ConnectionState } from '@/services/WebSocketManager';

export interface UseWebSocketReturn {
  isConnected: boolean;
  connectionState: ConnectionState;
  send: (data: string | object) => boolean;
  subscribe: (handler: (message: PlaygroundOutgoingMessage) => void) => () => void;
}

/**
 * Hook to access the WebSocket connection managed by WebSocketProvider.
 * Must be used within a WebSocketProvider context.
 * 
 * @returns Object with WebSocket connection state and methods
 * @throws Error if used outside of WebSocketProvider
 * 
 * @example
 * ```tsx
 * const { isConnected, send, subscribe } = useWebSocket();
 * 
 * useEffect(() => {
 *   const unsubscribe = subscribe((message) => {
 *     console.log('Received:', message);
 *   });
 *   return unsubscribe;
 * }, []);
 * ```
 */
export function useWebSocket(): UseWebSocketReturn {
  const context = useContext(WebSocketContext);

  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }

  const isConnected = context.connectionState === 'connected';

  return {
    isConnected,
    connectionState: context.connectionState,
    send: context.send,
    subscribe: context.subscribe
  };
}

// Convenience hook for subscribing to specific message types
export function useWebSocketMessages<T extends PlaygroundOutgoingMessage['type']>(
  messageType: T | T[],
  handler: (message: Extract<PlaygroundOutgoingMessage, { type: T }>) => void
) {
  const { subscribe } = useWebSocket();

  useEffect(() => {
    const types = Array.isArray(messageType) ? messageType : [messageType];
    
    const unsubscribe = subscribe((message) => {
      if (types.includes(message.type as T)) {
        handler(message as Extract<PlaygroundOutgoingMessage, { type: T }>);
      }
    });

    return unsubscribe;
  }, [messageType, handler, subscribe]);
}

// Hook for tracking connection state changes
export function useWebSocketConnectionState(
  handler: (state: ConnectionState) => void
) {
  const context = useContext(WebSocketContext);

  if (!context) {
    throw new Error('useWebSocketConnectionState must be used within a WebSocketProvider');
  }

  useEffect(() => {
    return context.subscribeToConnectionState(handler);
  }, [context, handler]);
}