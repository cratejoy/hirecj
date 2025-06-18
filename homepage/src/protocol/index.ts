/**
 * Protocol type exports
 * Auto-generated types from shared/protocol/models.py
 */

// Re-export all interfaces from generated file
export * from './generated';

// Define discriminated unions based on our protocol
import type {
  StartConversationMsg,
  UserMsg,
  EndConversationMsg,
  FactCheckMsg,
  DebugRequestMsg,
  WorkflowTransitionMsg,
  PingMsg,
  LogoutMsg,
  OAuthCompleteMsg,
  SystemEventMsg,
  ConversationStartedMsg,
  CJMessageMsg,
  CJThinkingMsg,
  ThinkingTokenMsg,
  ToolCallMsg,
  FactCheckStartedMsg,
  FactCheckCompleteMsg,
  FactCheckErrorMsg,
  FactCheckStatusMsg,
  WorkflowUpdatedMsg,
  WorkflowTransitionCompleteMsg,
  OAuthProcessedMsg,
  LogoutCompleteMsg,
  PongMsg,
  DebugResponseMsg,
  DebugEventMsg,
  ErrorMsg,
  SystemMsg
} from './generated';

export type IncomingMessage =
  | StartConversationMsg
  | UserMsg
  | EndConversationMsg
  | FactCheckMsg
  | DebugRequestMsg
  | WorkflowTransitionMsg
  | PingMsg
  | LogoutMsg
  | OAuthCompleteMsg
  | SystemEventMsg;

export type OutgoingMessage =
  | ConversationStartedMsg
  | CJMessageMsg
  | CJThinkingMsg
  | ThinkingTokenMsg
  | ToolCallMsg
  | FactCheckStartedMsg
  | FactCheckCompleteMsg
  | FactCheckErrorMsg
  | FactCheckStatusMsg
  | WorkflowUpdatedMsg
  | WorkflowTransitionCompleteMsg
  | OAuthProcessedMsg
  | LogoutCompleteMsg
  | PongMsg
  | DebugResponseMsg
  | DebugEventMsg
  | ErrorMsg
  | SystemMsg;

// Type guards
export function isIncomingMessage(msg: any): msg is IncomingMessage {
  const validTypes = [
    'start_conversation', 'message', 'end_conversation', 'fact_check',
    'debug_request', 'workflow_transition', 'ping', 'logout',
    'oauth_complete', 'system_event'
  ];
  return msg && typeof msg.type === 'string' && validTypes.includes(msg.type);
}

export function isOutgoingMessage(msg: any): msg is OutgoingMessage {
  const validTypes = [
    'conversation_started', 'cj_message', 'cj_thinking', 'thinking_token', 'tool_call',
    'fact_check_started', 'fact_check_complete', 'fact_check_error', 'fact_check_status',
    'workflow_updated', 'workflow_transition_complete', 'oauth_processed',
    'logout_complete', 'pong', 'debug_response', 'debug_event', 'error', 'system'
  ];
  return msg && typeof msg.type === 'string' && validTypes.includes(msg.type);
}
