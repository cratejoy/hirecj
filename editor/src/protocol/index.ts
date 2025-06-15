/**
 * Editor Protocol type exports
 * Focused subset for playground functionality
 */

// Re-export all generated types
export * from './generated';

// Import types for playground functionality
import type {
  PlaygroundStartMsg,
  PlaygroundResetMsg,
  UserMsg as MessageMsg,  // Rename for consistency
  ConversationStartedMsg,
  CJMessageMsg,
  CJThinkingMsg,
  ErrorMsg,
  SystemMsg
} from './generated';

// Playground-specific discriminated unions
export type PlaygroundIncomingMessage = 
  | PlaygroundStartMsg 
  | PlaygroundResetMsg 
  | MessageMsg;
  
export type PlaygroundOutgoingMessage =
  | ConversationStartedMsg
  | CJMessageMsg
  | CJThinkingMsg
  | ErrorMsg
  | SystemMsg;

// Type guards for message discrimination
export function isPlaygroundStart(msg: any): msg is PlaygroundStartMsg {
  return msg?.type === 'playground_start';
}

export function isPlaygroundReset(msg: any): msg is PlaygroundResetMsg {
  return msg?.type === 'playground_reset';
}

export function isMessage(msg: any): msg is MessageMsg {
  return msg?.type === 'message';
}

export function isCjMessage(msg: any): msg is CJMessageMsg {
  return msg?.type === 'cj_message';
}

export function isCjThinking(msg: any): msg is CJThinkingMsg {
  return msg?.type === 'cj_thinking';
}

export function isConversationStarted(msg: any): msg is ConversationStartedMsg {
  return msg?.type === 'conversation_started';
}

export function isError(msg: any): msg is ErrorMsg {
  return msg?.type === 'error';
}

export function isSystem(msg: any): msg is SystemMsg {
  return msg?.type === 'system';
}

// Helper to check if a message is a playground incoming message
export function isPlaygroundIncomingMessage(msg: any): msg is PlaygroundIncomingMessage {
  return isPlaygroundStart(msg) || isPlaygroundReset(msg) || isMessage(msg);
}

// Helper to check if a message is a playground outgoing message
export function isPlaygroundOutgoingMessage(msg: any): msg is PlaygroundOutgoingMessage {
  return isConversationStarted(msg) || isCjMessage(msg) || isCjThinking(msg) || 
         isError(msg) || isSystem(msg);
}

// Re-export MessageMsg as UserMsg for clarity in editor context
export type { MessageMsg };