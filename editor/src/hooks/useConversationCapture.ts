import { useCallback, useRef } from 'react';
import { CJMessageMsg } from '@/protocol';
import { ConversationCapture, CaptureSource, Persona, Scenario } from '../evals/core/types';
import { WorkflowConfig } from '../utils/workflowParser';

// Utility to generate unique conversation IDs
const generateConversationId = (): string => {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 9);
  return `conv_${timestamp}_${random}`;
};

interface UseConversationCaptureProps {
  workflow: WorkflowConfig;
  persona: Persona;
  scenario: Scenario;
  trustLevel: number;
  model?: string;
  temperature?: number;
}

interface CapturedMessage {
  turn: number;
  user_input: string;
  agent_processing: {
    thinking: string;
    intermediate_responses: string[];
    tool_calls: any[]; // Will be properly typed when we have tool response data
    grounding_queries: any[]; // Will be properly typed when we have grounding data
    final_response: string;
  };
  metrics: {
    latency_ms: number;
    tokens: {
      prompt: number;
      completion: number;
      thinking: number;
    };
  };
}

export function useConversationCapture(props: UseConversationCaptureProps) {
  const { workflow, persona, scenario, trustLevel, model = 'gpt-4-turbo', temperature = 0.7 } = props;
  
  // Store conversation data as it's being built
  const conversationData = useRef<{
    id: string;
    messages: CapturedMessage[];
    startTime: number;
  }>({
    id: generateConversationId(),
    messages: [],
    startTime: Date.now()
  });
  
  // Track current message being processed
  const currentMessage = useRef<Partial<CapturedMessage>>({});
  const messageStartTime = useRef<number>(0);
  
  // Start capturing a new user message
  const startMessage = useCallback((userInput: string) => {
    messageStartTime.current = Date.now();
    const turn = conversationData.current.messages.length + 1;
    
    currentMessage.current = {
      turn,
      user_input: userInput,
      agent_processing: {
        thinking: '',
        intermediate_responses: [],
        tool_calls: [],
        grounding_queries: [],
        final_response: ''
      },
      metrics: {
        latency_ms: 0,
        tokens: {
          prompt: 0,
          completion: 0,
          thinking: 0
        }
      }
    };
  }, []);
  
  // Capture thinking updates
  const captureThinking = useCallback((thinking: string) => {
    if (currentMessage.current.agent_processing) {
      currentMessage.current.agent_processing.thinking = thinking;
    }
  }, []);
  
  // Capture intermediate responses
  const captureIntermediateResponse = useCallback((response: string) => {
    if (currentMessage.current.agent_processing) {
      currentMessage.current.agent_processing.intermediate_responses.push(response);
    }
  }, []);
  
  // Capture tool calls
  const captureToolCall = useCallback((toolCall: any) => {
    if (currentMessage.current.agent_processing) {
      currentMessage.current.agent_processing.tool_calls.push(toolCall);
    }
  }, []);
  
  // Capture the final response and complete the message
  const completeMessage = useCallback((finalResponse: string, tokenMetrics?: any) => {
    if (!currentMessage.current.agent_processing) return;
    
    currentMessage.current.agent_processing.final_response = finalResponse;
    
    // Calculate latency
    if (currentMessage.current.metrics) {
      currentMessage.current.metrics.latency_ms = Date.now() - messageStartTime.current;
      
      // Add token metrics if provided
      if (tokenMetrics) {
        currentMessage.current.metrics.tokens = {
          prompt: tokenMetrics.prompt || 0,
          completion: tokenMetrics.completion || 0,
          thinking: tokenMetrics.thinking || 0
        };
      }
    }
    
    // Add completed message to conversation
    conversationData.current.messages.push(currentMessage.current as CapturedMessage);
    currentMessage.current = {};
  }, []);
  
  // Export the full conversation
  const captureConversation = useCallback(async (source: CaptureSource = 'playground'): Promise<ConversationCapture> => {
    // Get current prompts (in a real implementation, these would come from the system)
    const prompts = {
      cj_prompt: 'You are CJ, an autonomous CX & Growth Officer...', // Placeholder
      workflow_prompt: workflow.description || '',
      tool_definitions: [] // Will be populated from actual tool definitions
    };
    
    const conversation: ConversationCapture = {
      id: conversationData.current.id,
      timestamp: new Date().toISOString(),
      context: {
        workflow,
        persona,
        scenario,
        trustLevel,
        model,
        temperature
      },
      prompts,
      messages: conversationData.current.messages
    };
    
    // Send to backend for file storage
    try {
      const response = await fetch('/api/v1/conversations/capture', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation,
          source
        })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to capture conversation: ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('Conversation captured:', result);
      
      return conversation;
    } catch (error) {
      console.error('Error capturing conversation:', error);
      throw error;
    }
  }, [workflow, persona, scenario, trustLevel, model, temperature]);
  
  // Reset conversation capture
  const resetCapture = useCallback(() => {
    conversationData.current = {
      id: generateConversationId(),
      messages: [],
      startTime: Date.now()
    };
    currentMessage.current = {};
    messageStartTime.current = 0;
  }, []);
  
  return {
    startMessage,
    captureThinking,
    captureIntermediateResponse,
    captureToolCall,
    completeMessage,
    captureConversation,
    resetCapture,
    conversationId: conversationData.current.id
  };
}