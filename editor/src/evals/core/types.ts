import { WorkflowConfig } from '../../utils/workflowParser';

// Placeholder types until we find the actual definitions
export interface Persona {
  id: string;
  name: string;
  business: string;
  role: string;
  industry: string;
  communicationStyle: string[];
  traits: string[];
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters?: Record<string, any>;
}

export interface ToolCall {
  tool: string;
  args: Record<string, any>;
  result?: any;
  error?: string;
  duration_ms?: number;
}

export interface GroundingQuery {
  query: string;
  response: string;
  sources?: string[];
}

// Main conversation capture interface
export interface ConversationCapture {
  // Unique identifier
  id: string;
  timestamp: string;
  
  // Full execution context
  context: {
    workflow: WorkflowConfig;
    persona: Persona;
    scenario: Scenario;
    trustLevel: number;
    model: string;
    temperature: number;
  };
  
  // System prompts at time of execution
  prompts: {
    cj_prompt: string;
    cj_prompt_file?: string;  // Path to CJ prompt file
    workflow_prompt: string;
    workflow_prompt_file?: string;  // Path to workflow file
    tool_definitions: ToolDefinition[];
  };
  
  // Complete conversation history
  messages: Array<{
    turn: number;
    user_input: string;
    
    // Full agent processing chain
    agent_processing: {
      thinking: string;
      intermediate_responses: string[];
      tool_calls: ToolCall[];
      grounding_queries: GroundingQuery[];
      final_response: string;
    };
    
    // Performance metrics
    metrics: {
      latency_ms: number;
      tokens: {
        prompt: number;
        completion: number;
        thinking: number;
      };
    };
  }>;
  
  // File path where conversation is saved (added by capture process)
  filePath?: string;
}

// Export type for the capture source
export type CaptureSource = 'playground' | 'production' | 'synthetic';