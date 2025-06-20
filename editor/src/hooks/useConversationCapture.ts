import { useCallback, useRef } from 'react';
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
  cjPrompt?: string;
  cjPromptVersion?: string;
  cjPromptFile?: string;
  workflowPrompt?: string;
  workflowPromptFile?: string;
  toolDefinitions?: any[];
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
  const { 
    workflow, 
    persona, 
    scenario, 
    trustLevel, 
    model = 'gpt-4-turbo', 
    temperature = 0.7,
    cjPrompt,
    cjPromptVersion,
    cjPromptFile,
    workflowPrompt,
    workflowPromptFile,
    toolDefinitions
  } = props;
  
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
    
    console.log('[ConversationCapture] Starting message', { turn, userInput: userInput.substring(0, 50) + '...' });
    
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
  const completeMessage = useCallback((finalResponse: string, tokenMetrics?: any, debugData?: any) => {
    if (!currentMessage.current.agent_processing) {
      console.warn('[ConversationCapture] No current message to complete');
      return;
    }
    
    console.log('[ConversationCapture] Completing message', { 
      turn: currentMessage.current.turn,
      response: finalResponse.substring(0, 50) + '...',
      hasDebugData: !!debugData
    });
    
    currentMessage.current.agent_processing.final_response = finalResponse;
    
    // Extract processing details from debug data if available
    if (debugData) {
      // Extract thinking content
      if (debugData.response?.thinking_content) {
        currentMessage.current.agent_processing.thinking = debugData.response.thinking_content;
      } else if (debugData.thinking_content) {
        currentMessage.current.agent_processing.thinking = debugData.thinking_content;
      }
      
      // Extract intermediate responses
      if (debugData.response?.choices) {
        const intermediateResponses: string[] = [];
        debugData.response.choices.forEach((choice: any) => {
          if (choice.message?.content) {
            intermediateResponses.push(choice.message.content);
          }
        });
        currentMessage.current.agent_processing.intermediate_responses = intermediateResponses;
        
        // Extract tool calls
        const toolCalls: any[] = [];
        debugData.response.choices.forEach((choice: any) => {
          if (choice.message?.tool_calls) {
            choice.message.tool_calls.forEach((tc: any) => {
              toolCalls.push({
                tool: tc.function?.name || 'unknown',
                args: JSON.parse(tc.function?.arguments || '{}'),
                result: null, // Tool results not available in this data
                error: null,
                duration_ms: null
              });
            });
          }
        });
        currentMessage.current.agent_processing.tool_calls = toolCalls;
      }
      
      // Extract grounding queries
      if (debugData.grounding && Array.isArray(debugData.grounding)) {
        const groundingQueries = debugData.grounding.map((g: any) => ({
          query: g.query || '',
          response: g.results_preview || '',
          sources: g.namespace ? [g.namespace] : []
        }));
        currentMessage.current.agent_processing.grounding_queries = groundingQueries;
      }
      
      // Extract token metrics
      if (debugData.response?.usage) {
        const usage = debugData.response.usage;
        currentMessage.current.metrics!.tokens = {
          prompt: usage.prompt_tokens || 0,
          completion: usage.completion_tokens || 0,
          thinking: usage.completion_tokens_details?.reasoning_tokens || 0
        };
      }
    }
    
    // Calculate latency
    if (currentMessage.current.metrics) {
      currentMessage.current.metrics.latency_ms = Date.now() - messageStartTime.current;
      
      // Override with token metrics if provided separately
      if (tokenMetrics) {
        currentMessage.current.metrics.tokens = {
          prompt: tokenMetrics.prompt || currentMessage.current.metrics.tokens.prompt || 0,
          completion: tokenMetrics.completion || currentMessage.current.metrics.tokens.completion || 0,
          thinking: tokenMetrics.thinking || currentMessage.current.metrics.tokens.thinking || 0
        };
      }
    }
    
    // Add completed message to conversation
    conversationData.current.messages.push(currentMessage.current as CapturedMessage);
    console.log('[ConversationCapture] Message added. Total messages:', conversationData.current.messages.length);
    currentMessage.current = {};
  }, []);
  
  // Export the full conversation
  const captureConversation = useCallback(async (source: CaptureSource = 'playground'): Promise<ConversationCapture> => {
    console.log('[ConversationCapture] Exporting conversation', {
      id: conversationData.current.id,
      messageCount: conversationData.current.messages.length,
      source
    });
    
    // Use actual prompts passed to the hook
    const prompts = {
      cj_prompt: cjPrompt || 'CJ prompt not available',
      cj_prompt_file: cjPromptFile,
      workflow_prompt: workflowPrompt || workflow.description || '',
      workflow_prompt_file: workflowPromptFile,
      tool_definitions: toolDefinitions || []
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
    // Using relative path to work with the proxy
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
      
      // Add the file path to the conversation object
      return {
        ...conversation,
        filePath: result.path
      };
    } catch (error) {
      console.error('Error capturing conversation:', error);
      throw error;
    }
  }, [workflow, persona, scenario, trustLevel, model, temperature, cjPrompt, cjPromptFile, workflowPrompt, workflowPromptFile, toolDefinitions]);
  
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