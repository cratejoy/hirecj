import yaml from 'js-yaml';

export interface InitialAction {
  type: 'static_message' | 'process_message';
  content?: string;
  message?: string;
  sender?: string;
  add_to_history?: boolean;
}

export interface WorkflowBehavior {
  initiator?: string;
  initial_action?: InitialAction;
  transitions?: Record<string, any>;
}

export interface WorkflowConfig {
  name: string;
  description: string;
  behavior?: WorkflowBehavior;
  requirements?: {
    merchant?: boolean;
    scenario?: boolean;
    authentication?: boolean;
  };
  workflow?: string;
  data_requirements?: any[];
  available_tools?: string[];
}

/**
 * Parse YAML content into a WorkflowConfig object
 */
export const parseWorkflow = (yamlContent: string): WorkflowConfig => {
  try {
    return yaml.load(yamlContent) as WorkflowConfig;
  } catch (error) {
    console.error('Failed to parse workflow YAML:', error);
    throw new Error('Invalid workflow YAML format');
  }
};

/**
 * Determine if a workflow is agent-initiated based on its configuration
 */
export const isAgentInitiated = (workflow: WorkflowConfig): boolean => {
  // A workflow is agent-initiated if it has an initial_action defined
  return !!workflow.behavior?.initial_action;
};

/**
 * Get the initial message preview for agent-initiated workflows
 */
export const getInitialMessage = (workflow: WorkflowConfig): string | null => {
  const action = workflow.behavior?.initial_action;
  if (!action) return null;
  
  if (action.type === 'static_message') {
    // Return the static message content
    return action.content || null;
  } else if (action.type === 'process_message') {
    // For process_message, we can't preview the actual message
    return '[CJ will generate an opening message based on current data]';
  }
  
  return null;
};

/**
 * Get a description of how the workflow starts
 */
export const getWorkflowStartDescription = (workflow: WorkflowConfig): string => {
  const action = workflow.behavior?.initial_action;
  
  if (!action) {
    return 'You start the conversation';
  }
  
  if (action.type === 'static_message') {
    return 'CJ will greet you with a message';
  } else if (action.type === 'process_message') {
    return 'CJ will analyze current data and start the conversation';
  }
  
  return 'Workflow will start';
};