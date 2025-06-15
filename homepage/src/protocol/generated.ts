/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface CJMessageData {
  content: string;
  factCheckStatus?: string | null;
  timestamp: string;
  ui_elements?:
    | {
        [k: string]: unknown;
      }[]
    | null;
}
export interface CJMessageMsg {
  type: "cj_message";
  data: CJMessageData;
}
export interface CJThinkingData {
  status: string;
  elapsed?: number | null;
  toolsCalled?: number | null;
  currentTool?: string | null;
}
export interface CJThinkingMsg {
  type: "cj_thinking";
  data: CJThinkingData;
}
export interface ConversationStartedData {
  conversationId: string;
  shopSubdomain?: string | null;
  scenario?: string | null;
  workflow: string;
  sessionId?: string | null;
  resumed?: boolean | null;
  connected_at?: string | null;
  messageCount?: number | null;
  messages?:
    | {
        [k: string]: unknown;
      }[]
    | null;
  workflow_requirements?: {
    [k: string]: unknown;
  } | null;
  user_id?: string | null;
}
export interface ConversationStartedMsg {
  type: "conversation_started";
  data: ConversationStartedData;
}
export interface DebugEventMsg {
  type: "debug_event";
  data: {
    [k: string]: unknown;
  };
}
export interface DebugRequestData {
  type: "snapshot" | "session" | "state" | "metrics" | "prompts";
}
export interface DebugRequestMsg {
  type: "debug_request";
  data: DebugRequestData;
}
export interface DebugResponseMsg {
  type: "debug_response";
  data: {
    [k: string]: unknown;
  };
}
export interface EndConversationMsg {
  type: "end_conversation";
}
export interface ErrorMsg {
  type: "error";
  text: string;
}
export interface FactCheckCompleteData {
  messageIndex: number;
  result: FactCheckResultData;
}
export interface FactCheckResultData {
  overall_status: "PASS" | "WARNING" | "FAIL";
  claims: FactClaimData[];
  issues: FactIssueData[];
  execution_time: number;
  turn_number?: number | null;
  checked_at: string;
}
export interface FactClaimData {
  claim: string;
  verification: "VERIFIED" | "UNVERIFIED" | "INCORRECT";
  actual_data?: string | null;
  source?: string | null;
}
export interface FactIssueData {
  severity: "minor" | "major" | "critical";
  summary: string;
  claim?: string | null;
  expected?: string | null;
  actual?: string | null;
}
export interface FactCheckCompleteMsg {
  type: "fact_check_complete";
  data: FactCheckCompleteData;
}
export interface FactCheckData {
  messageIndex: number;
  forceRefresh?: boolean;
}
export interface FactCheckErrorData {
  messageIndex: number;
  error: string;
}
export interface FactCheckErrorMsg {
  type: "fact_check_error";
  data: FactCheckErrorData;
}
export interface FactCheckMsg {
  type: "fact_check";
  data: FactCheckData;
}
export interface FactCheckStartedData {
  messageIndex: number;
  status?: "checking";
}
export interface FactCheckStartedMsg {
  type: "fact_check_started";
  data: FactCheckStartedData;
}
export interface FactCheckStatusMsg {
  type: "fact_check_status";
  data: {
    [k: string]: unknown;
  };
}
export interface LogoutCompleteData {
  message: string;
}
export interface LogoutCompleteMsg {
  type: "logout_complete";
  data: LogoutCompleteData;
}
export interface LogoutMsg {
  type: "logout";
}
export interface OAuthCompleteMsg {
  type: "oauth_complete";
  data: {
    [k: string]: unknown;
  };
}
export interface OAuthProcessedData {
  success: boolean;
  is_new?: boolean | null;
  merchant_id?: number | null;
  shop_domain?: string | null;
  shop_subdomain?: string | null;
  error?: string | null;
}
export interface OAuthProcessedMsg {
  type: "oauth_processed";
  data: OAuthProcessedData;
}
export interface PingMsg {
  type: "ping";
}
export interface PongMsg {
  type: "pong";
  timestamp: string;
}
export interface StartConversationData {
  workflow?: string | null;
  shop_subdomain?: string | null;
  scenario_id?: string | null;
}
export interface StartConversationMsg {
  type: "start_conversation";
  data: StartConversationData;
}
export interface SystemEventMsg {
  type: "system_event";
  data: {
    [k: string]: unknown;
  };
}
export interface SystemMsg {
  type: "system";
  text: string;
}
export interface UserMsg {
  type: "message";
  text: string;
}
export interface WorkflowTransitionCompleteData {
  workflow: string;
  message: string;
}
export interface WorkflowTransitionCompleteMsg {
  type: "workflow_transition_complete";
  data: WorkflowTransitionCompleteData;
}
export interface WorkflowTransitionData {
  new_workflow: string;
  user_initiated?: boolean;
}
export interface WorkflowTransitionMsg {
  type: "workflow_transition";
  data: WorkflowTransitionData;
}
export interface WorkflowUpdatedData {
  workflow: string;
  previous?: string | null;
}
export interface WorkflowUpdatedMsg {
  type: "workflow_updated";
  data: WorkflowUpdatedData;
}
