/**
 * WebSocket message types and interfaces
 */

import { WorkflowType } from '../constants/workflow';

// Base message interface
interface BaseMessage {
  type: string;
}

// Workflow transition message
export interface WorkflowTransitionMessage extends BaseMessage {
  type: 'workflow_transition';
  data: {
    new_workflow: WorkflowType;
    user_initiated: boolean;
  };
}

// Other message types can be added here as needed
export interface TextMessage extends BaseMessage {
  type: 'message';
  text: string;
  merchant_id?: string;
  scenario?: string;
}

// Union type of all possible messages
export type WebSocketMessage = WorkflowTransitionMessage | TextMessage;

// Type guard functions
export function isWorkflowTransitionMessage(msg: any): msg is WorkflowTransitionMessage {
  return msg?.type === 'workflow_transition' && 
         msg?.data?.new_workflow !== undefined &&
         typeof msg?.data?.user_initiated === 'boolean';
}

export function isTextMessage(msg: any): msg is TextMessage {
  return msg?.type === 'message' && typeof msg?.text === 'string';
}