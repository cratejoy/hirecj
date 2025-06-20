/**
 * WebSocket configuration constants
 * Centralized timeout and interval values for consistency
 */

export const WEBSOCKET_CONFIG = {
  // Reconnection settings
  MAX_RECONNECT_ATTEMPTS: 10,
  MAX_RECONNECT_DELAY: 30000, // 30 seconds
  INITIAL_RECONNECT_DELAY: 1000, // 1 second
  
  // Heartbeat settings
  PING_INTERVAL: 15000, // 15 seconds - must be less than server timeout
  
  // Message queue settings
  MESSAGE_QUEUE_MAX_AGE: 60000, // 1 minute
  
  // Connection settings
  CLOSE_TIMEOUT: 10000, // 10 seconds
} as const;