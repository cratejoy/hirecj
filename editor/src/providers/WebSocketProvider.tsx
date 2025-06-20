import React, { createContext, useEffect, useRef, useState, ReactNode } from 'react';
import { WebSocketManager, ConnectionState } from '@/services/WebSocketManager';
import { PlaygroundOutgoingMessage } from '@/protocol';

interface WebSocketContextValue {
  connectionState: ConnectionState;
  send: (data: string | object) => boolean;
  subscribe: (handler: (message: PlaygroundOutgoingMessage) => void) => () => void;
  subscribeToConnectionState: (handler: (state: ConnectionState) => void) => () => void;
}

export const WebSocketContext = createContext<WebSocketContextValue | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
  autoConnect?: boolean;
}

/**
 * WebSocket Provider component that manages the WebSocket connection
 * at the application level. This provider ensures that only one
 * WebSocket connection is created and maintained throughout the app
 * lifecycle, preventing duplicate connections from React StrictMode.
 * 
 * Usage:
 * ```tsx
 * <WebSocketProvider>
 *   <App />
 * </WebSocketProvider>
 * ```
 */
export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ 
  children, 
  autoConnect = true 
}) => {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [isInitialized, setIsInitialized] = useState(false);
  const managerRef = useRef<WebSocketManager | null>(null);
  const hasInitialized = useRef(false);

  useEffect(() => {
    console.log('🌟 WebSocketProvider effect running');

    // Get singleton instance
    const manager = WebSocketManager.getInstance();
    managerRef.current = manager;

    // Subscribe to connection state changes
    const unsubscribeState = manager.subscribeToConnectionState((state) => {
      console.log('🔄 Connection state changed:', state);
      setConnectionState(state);
    });

    // Get current state immediately
    const currentState = manager.getConnectionState();
    console.log('📊 Current connection state:', currentState);
    setConnectionState(currentState);

    // Mark as initialized
    setIsInitialized(true);

    // Auto-connect if enabled and not already connected/connecting
    if (autoConnect && currentState === 'disconnected') {
      console.log('🤖 Auto-connecting WebSocket');
      manager.connect();
    }

    // Cleanup function
    return () => {
      console.log('🧹 WebSocketProvider cleanup');
      unsubscribeState();
      // Note: We don't disconnect here because the WebSocketManager is a singleton
      // and might be used by other components. The app-level cleanup should handle
      // the final disconnect.
    };
  }, []); // Empty deps - only run once

  // Get the manager instance directly for methods
  const manager = managerRef.current || WebSocketManager.getInstance();

  // Context value that exposes WebSocketManager methods
  const contextValue: WebSocketContextValue = {
    connectionState,
    send: (data: string | object) => {
      return manager.send(data);
    },
    subscribe: (handler: (message: PlaygroundOutgoingMessage) => void) => {
      return manager.subscribe(handler);
    },
    subscribeToConnectionState: (handler: (state: ConnectionState) => void) => {
      return manager.subscribeToConnectionState(handler);
    }
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};