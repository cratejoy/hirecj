// Types for the Eval Designer interface

export interface EvalCase {
  id: string;
  eval_id: string;
  sample_id: string;
  
  // Input context from the conversation
  input: {
    messages: Array<{
      role: 'system' | 'user' | 'assistant';
      content: string;
    }>;
    context: {
      workflow: string;
      available_tools?: string[];
      persona?: string;
      scenario?: string;
      trust_level?: number;
    };
  };
  
  // Expected behavior/output
  ideal: {
    tool_selection?: {
      should_use_tool: boolean;
      acceptable_tools?: string[];
      unacceptable_tools?: string[];
    };
    response_criteria?: {
      must_include?: string[];
      must_not_include?: string[];
      tone?: string;
      explains_choice?: boolean;
    };
    grounding?: {
      should_query: boolean;
      expected_topics?: string[];
    };
  };
  
  // Actual output from the conversation (for reference)
  actual?: {
    thinking?: string;
    tool_calls?: string[];
    grounding_queries?: string[];
    response: string;
  };
  
  // Metadata
  metadata: {
    source_conversation: string;
    turn: number;
    timestamp: string;
    created_by?: string;
    modified_at?: string;
    notes?: string;
  };
}

export interface EvalDataset {
  id: string;
  name: string;
  description: string;
  category: 'golden' | 'generated' | 'regression';
  cases: EvalCase[];
  metadata: {
    created_at: string;
    updated_at: string;
    version: string;
    tags?: string[];
  };
}

export interface ConversationSummary {
  id: string;
  timestamp: string;
  source: 'playground' | 'production' | 'synthetic';
  workflow: string;
  persona?: string;
  message_count: number;
  has_tool_calls: boolean;
  has_grounding: boolean;
  file_path: string;
}

export interface EvalPreviewResult {
  case_id: string;
  passed: boolean;
  score?: number;
  details: {
    tool_selection?: {
      expected: string[];
      actual: string[];
      matched: boolean;
    };
    response_quality?: {
      criteria_met: string[];
      criteria_missed: string[];
    };
    errors?: string[];
  };
}

export interface EvalDesignerState {
  // Currently selected conversation
  selectedConversation?: ConversationSummary;
  
  // Cases being edited
  editingCases: EvalCase[];
  
  // Current dataset being worked on
  currentDataset?: EvalDataset;
  
  // Preview results
  previewResults?: EvalPreviewResult[];
}