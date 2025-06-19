import React, { useEffect, useState } from 'react';
import { X, FileText, Loader2, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

interface MessageDetailsViewProps {
  isOpen: boolean;
  onClose: () => void;
  messageId?: string;
  onRequestDetails?: (messageId: string) => Promise<any>;
}

// Parse ISO 8601 duration format (e.g., "PT3.448383S") to seconds
const parseISODuration = (duration: string | number): number => {
  if (typeof duration === 'number') {
    return duration;
  }
  
  // Parse "PT3.448383S" format
  const match = duration.match(/PT(\d+\.?\d*)S/);
  return match ? parseFloat(match[1]) : 0;
};

export function MessageDetailsView({ isOpen, onClose, messageId, onRequestDetails }: MessageDetailsViewProps) {
  const [loading, setLoading] = useState(false);
  const [debugData, setDebugData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedItems, setCopiedItems] = useState<Set<string>>(new Set());
  
  // Copy to clipboard utility
  const copyToClipboard = async (text: string, itemId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedItems(prev => new Set(prev).add(itemId));
      // Reset after 2 seconds
      setTimeout(() => {
        setCopiedItems(prev => {
          const next = new Set(prev);
          next.delete(itemId);
          return next;
        });
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };
  // Load debug data when opened
  useEffect(() => {
    if (isOpen && messageId && onRequestDetails) {
      setLoading(true);
      setError(null);
      onRequestDetails(messageId)
        .then(data => {
          console.log('[MessageDetailsView] Received debug data:', data);
          console.log('[MessageDetailsView] Response data:', data?.response);
          console.log('[MessageDetailsView] Thinking content:', data?.response?.thinking_content);
          console.log('[MessageDetailsView] Final response:', data?.response?.final_response);
          setDebugData(data);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message || 'Failed to load message details');
          setLoading(false);
        });
    }
  }, [isOpen, messageId, onRequestDetails]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);
  
  if (!isOpen) return null;

  // Use real data if available, otherwise fall back to hardcoded
  const promptData = debugData?.prompt || null;
  const responseData = debugData?.response || null;
  const toolCalls = debugData?.tool_calls || [];
  const crewOutput = debugData?.crew_output || [];
  const grounding = debugData?.grounding || [];
  
  // Log what we're displaying
  if (responseData) {
    console.log('[MessageDetailsView] Response data structure:', {
      hasThinkingContent: !!responseData.thinking_content,
      thinkingLength: responseData.thinking_content?.length,
      hasCleanContent: !!responseData.clean_content,
      cleanLength: responseData.clean_content?.length,
      hasChoices: !!(responseData.choices && responseData.choices.length > 0),
      firstChoiceContent: responseData.choices?.[0]?.message?.content?.substring(0, 100)
    });
  }

  // Fallback data for demonstration
  const fallbackSystemPrompt = `You are a helpful and knowledgeable customer service agent for an e-commerce platform.

Your primary goals are to:
- Assist customers with product inquiries
- Help resolve order issues
- Provide personalized recommendations
- Maintain a friendly and professional tone

Always remember to:
- Ask clarifying questions when needed
- Reference customer history when available
- Escalate complex issues appropriately`;

  const fallbackMessages = [
    { role: 'USER', content: "Hey, I'm looking for a new laptop for work. What do you recommend?" },
    { role: 'ASSISTANT', content: "I'd be happy to help you find a laptop! What's your budget and main use cases?" },
    { role: 'USER', content: "Budget is around $1500. I need it for coding and video editing." }
  ];

  const fallbackResponse = "For that budget, I'd suggest the MacBook Pro 14\" or Dell XPS 15. Both are excellent for coding and video editing.";

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      
      {/* Main Content */}
      <div className="fixed inset-0 bg-background z-50 flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-300">
      {/* Header */}
      <div className="border-b p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          <h2 className="text-lg font-semibold">MESSAGE DETAILS - LLM Prompt & Response</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            Message: "For that budget, I'd suggest the MacBook Pro 14"..."
          </span>
          <Button variant="ghost" size="sm" onClick={onClose}>
            [← Back to Playground]
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main Content - Split View */}
      <div className="flex-1 flex">
        {/* Loading State */}
        {loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
              <p className="text-muted-foreground">Loading message details...</p>
            </div>
          </div>
        )}
        
        {/* Error State */}
        {error && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-destructive mb-4">{error}</p>
              <Button variant="outline" onClick={onClose}>Close</Button>
            </div>
          </div>
        )}
        
        {/* Content */}
        {!loading && !error && (
          <>
            {/* Left Panel - Outgoing Prompt */}
            <div className="flex-1 border-r flex flex-col">
              <div className="p-4 border-b bg-muted/30">
                <h3 className="font-medium text-sm uppercase tracking-wider">OUTGOING PROMPT TO LLM</h3>
              </div>
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  {promptData ? (
                    <>
                      {/* Model Info */}
                      <div>
                        <p className="font-medium text-sm text-muted-foreground mb-2">MODEL:</p>
                        <div className="bg-muted/50 rounded-lg p-3">
                          <p className="text-sm">{promptData.model}</p>
                          {promptData.temperature !== undefined && (
                            <p className="text-xs text-muted-foreground mt-1">Temperature: {promptData.temperature}</p>
                          )}
                        </div>
                      </div>
                      
                      <Separator />
                      
                      {/* Messages */}
                      {promptData.messages?.map((msg: any, idx: number) => (
                        <div key={idx}>
                          <p className="font-medium text-sm text-muted-foreground mb-2">{msg.role?.toUpperCase()}:</p>
                          <div className="bg-muted rounded-lg p-3">
                            <pre className="text-sm whitespace-pre-wrap">{typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2)}</pre>
                          </div>
                        </div>
                      ))}
                      
                      {/* Tools if available */}
                      {promptData.tools && promptData.tools.length > 0 && (
                        <>
                          <Separator />
                          <div>
                            <p className="font-medium text-sm text-muted-foreground mb-2">AVAILABLE TOOLS:</p>
                            <div className="space-y-2">
                              {promptData.tools.map((tool: any, idx: number) => (
                                <div key={idx} className="bg-muted/50 rounded-lg p-3">
                                  <p className="text-sm font-medium">{tool.function?.name || 'Unknown'}</p>
                                  <p className="text-xs text-muted-foreground mt-1">{tool.function?.description || ''}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        </>
                      )}
                    </>
                  ) : (
                    /* Fallback data */
                    <>
                      <div>
                        <p className="font-medium text-sm text-muted-foreground mb-2">SYSTEM:</p>
                        <pre className="text-sm whitespace-pre-wrap bg-muted/50 rounded-lg p-3">{fallbackSystemPrompt}</pre>
                      </div>
                      
                      <Separator />
                      
                      {fallbackMessages.map((msg, idx) => {
                        const copyId = `prompt-${idx}`;
                        return (
                          <div key={idx}>
                            <p className="font-medium text-sm text-muted-foreground mb-2">{msg.role}:</p>
                            <div className="relative bg-muted rounded-lg p-3">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="absolute top-2 right-2 h-8 w-8 p-0"
                                onClick={() => copyToClipboard(msg.content, copyId)}
                              >
                                {copiedItems.has(copyId) ? (
                                  <Check className="h-4 w-4 text-green-600" />
                                ) : (
                                  <Copy className="h-4 w-4" />
                                )}
                              </Button>
                              <p className="text-sm pr-10">{msg.content}</p>
                            </div>
                          </div>
                        );
                      })}
                    </>
                  )}
                  
                  {promptData && (
                    <div className="text-xs text-muted-foreground mt-4">
                      [Timestamp: {promptData.timestamp}]
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>

            {/* Right Panel - Incoming Response */}
            <div className="flex-1 flex flex-col">
              <div className="p-4 border-b bg-muted/30">
                <h3 className="font-medium text-sm uppercase tracking-wider">LLM EXECUTION & RESPONSE</h3>
              </div>
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  {responseData ? (
                    <>
                      {/* Explanation of CrewAI's multi-step process */}
                      <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-4">
                        <p className="text-xs text-blue-700 dark:text-blue-300">
                          <strong>Note:</strong> CrewAI agents use a multi-step reasoning process. They may generate multiple intermediate responses before arriving at the final answer.
                        </p>
                      </div>
                      
                      {/* Final Response - What User Actually Saw */}
                      {responseData.final_response && (
                        <>
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="font-medium text-sm uppercase tracking-wider text-green-700 dark:text-green-400">✓ FINAL RESPONSE SENT TO USER</h4>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => copyToClipboard(responseData.final_response, 'final-response')}
                              >
                                {copiedItems.has('final-response') ? (
                                  <Check className="h-4 w-4 text-green-600" />
                                ) : (
                                  <Copy className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                            <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
                              <p className="text-sm whitespace-pre-wrap">{responseData.final_response}</p>
                            </div>
                          </div>
                          <Separator />
                        </>
                      )}
                      
                      {/* Raw LLM Response Content */}
                      {responseData.choices?.map((choice: any, idx: number) => (
                        <div key={idx}>
                          {choice.message?.content && (
                            <div className="mb-4">
                              <h4 className="font-medium text-sm uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-2">⚡ INTERMEDIATE LLM RESPONSE</h4>
                              <div className="relative bg-muted/50 rounded-lg p-4">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="absolute top-2 right-2 h-8 w-8 p-0"
                                  onClick={() => copyToClipboard(choice.message.content, `response-${idx}`)}
                                >
                                  {copiedItems.has(`response-${idx}`) ? (
                                    <Check className="h-4 w-4 text-green-600" />
                                  ) : (
                                    <Copy className="h-4 w-4" />
                                  )}
                                </Button>
                                <p className="text-sm whitespace-pre-wrap pr-10">{choice.message.content}</p>
                              </div>
                            </div>
                          )}
                          
                          {/* Tool Calls */}
                          {choice.message?.tool_calls && choice.message.tool_calls.length > 0 && (
                            <div>
                              <p className="font-medium text-sm text-muted-foreground mb-2">TOOL CALLS:</p>
                              <div className="space-y-2">
                                {choice.message.tool_calls.map((tc: any, tcIdx: number) => {
                                  const toolCopyId = `tool-${idx}-${tcIdx}`;
                                  let formattedArgs = tc.function?.arguments;
                                  try {
                                    // Try to parse and format JSON
                                    const parsed = JSON.parse(tc.function?.arguments || '{}');
                                    formattedArgs = JSON.stringify(parsed, null, 2);
                                  } catch (e) {
                                    // Keep original if not valid JSON
                                  }
                                  
                                  return (
                                    <div key={tcIdx} className="bg-muted/50 rounded-lg p-3 relative">
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="absolute top-2 right-2 h-8 w-8 p-0"
                                        onClick={() => copyToClipboard(formattedArgs, toolCopyId)}
                                      >
                                        {copiedItems.has(toolCopyId) ? (
                                          <Check className="h-4 w-4 text-green-600" />
                                        ) : (
                                          <Copy className="h-4 w-4" />
                                        )}
                                      </Button>
                                      <p className="text-sm font-medium">{tc.function?.name}</p>
                                      <pre className="text-xs mt-1 text-muted-foreground overflow-x-auto pr-10">
                                        <code>{formattedArgs}</code>
                                      </pre>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                          
                          {choice.finish_reason && (
                            <p className="text-xs text-muted-foreground mt-2">Finish reason: {choice.finish_reason}</p>
                          )}
                        </div>
                      ))}
                      
                      {/* Usage Stats */}
                      {responseData.usage && (
                        <>
                          <Separator />
                          <div className="text-xs text-muted-foreground">
                            <p>Prompt tokens: {responseData.usage.prompt_tokens}</p>
                            <p>Completion tokens: {responseData.usage.completion_tokens}</p>
                            <p>Total tokens: {responseData.usage.total_tokens}</p>
                          </div>
                        </>
                      )}
                      
                      {/* Thinking Token Details */}
                      {responseData.usage?.completion_tokens_details && (
                        <>
                          <Separator className="my-2" />
                          <div className="text-xs text-muted-foreground">
                            <p className="font-medium mb-1">Thinking Breakdown:</p>
                            <p>Reasoning tokens: {responseData.usage.completion_tokens_details.reasoning_tokens}</p>
                            <p>Output tokens: {responseData.usage.completion_tokens_details.output_tokens}</p>
                          </div>
                        </>
                      )}
                      
                      {/* Agent Thinking Process */}
                      {responseData.thinking_content && (
                        <>
                          <Separator className="my-4" />
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <h4 className="font-medium text-sm uppercase tracking-wider text-blue-600 dark:text-blue-400">🤔 AGENT REASONING & THOUGHTS</h4>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => copyToClipboard(responseData.thinking_content, 'thinking')}
                              >
                                {copiedItems.has('thinking') ? (
                                  <Check className="h-4 w-4 text-green-600" />
                                ) : (
                                  <Copy className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                            <div className="bg-muted/50 rounded-lg p-4 max-h-96 overflow-y-auto">
                              <pre className="text-xs whitespace-pre-wrap font-mono text-muted-foreground">
                                <code>{responseData.thinking_content}</code>
                              </pre>
                            </div>
                          </div>
                        </>
                      )}
                      
                      {/* Knowledge Base Grounding */}
                      {grounding.length > 0 && (
                        <>
                          <Separator className="my-4" />
                          <div className="space-y-2">
                            <h4 className="font-medium text-sm uppercase tracking-wider text-purple-600 dark:text-purple-400">📚 KNOWLEDGE BASE GROUNDING</h4>
                            <div className="space-y-3">
                              {grounding.map((g: any, idx: number) => {
                                const groundingCopyId = `grounding-${idx}`;
                                return (
                                  <div key={idx} className="bg-muted/50 rounded-lg p-4">
                                    <div className="flex items-start justify-between mb-2">
                                      <div>
                                        <p className="text-sm font-medium">Namespace: {g.namespace}</p>
                                        <p className="text-xs text-muted-foreground mt-1">Query: {g.query}</p>
                                      </div>
                                      <div className="flex items-center gap-2">
                                        {g.cache_hit && (
                                          <span className="text-xs text-green-600 dark:text-green-400">Cached</span>
                                        )}
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-8 w-8 p-0"
                                          onClick={() => copyToClipboard(g.results_preview || '', groundingCopyId)}
                                        >
                                          {copiedItems.has(groundingCopyId) ? (
                                            <Check className="h-4 w-4 text-green-600" />
                                          ) : (
                                            <Copy className="h-4 w-4" />
                                          )}
                                        </Button>
                                      </div>
                                    </div>
                                    {g.error ? (
                                      <p className="text-xs text-destructive">Error: {g.error}</p>
                                    ) : (
                                      <>
                                        <p className="text-xs text-muted-foreground mb-2">
                                          Found {g.results_count} result{g.results_count !== 1 ? 's' : ''}
                                        </p>
                                        {g.results_preview && (
                                          <div className="bg-background/50 rounded p-3 max-h-48 overflow-y-auto">
                                            <pre className="text-xs whitespace-pre-wrap font-mono text-muted-foreground">
                                              <code>{g.results_preview}</code>
                                            </pre>
                                          </div>
                                        )}
                                      </>
                                    )}
                                    <p className="text-xs text-muted-foreground mt-2">{g.timestamp}</p>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </>
                      )}
                      
                      {/* Timing */}
                      {responseData.duration && (
                        <p className="text-xs text-muted-foreground">Duration: {parseISODuration(responseData.duration).toFixed(2)}s</p>
                      )}
                    </>
                  ) : (
                    /* Fallback */
                    <p className="text-sm">{fallbackResponse}</p>
                  )}
                  
                  {/* Tool Execution Results */}
                  {toolCalls.length > 0 && (
                    <>
                      <Separator />
                      <div>
                        <p className="font-medium text-sm text-muted-foreground mb-2">TOOL EXECUTION LOG:</p>
                        <div className="space-y-2">
                          {toolCalls.map((call: any, idx: number) => {
                            const execCopyId = `exec-${idx}`;
                            const outputText = call.tool_output ? 
                              (typeof call.tool_output === 'string' ? call.tool_output : JSON.stringify(call.tool_output, null, 2)) :
                              call.error || '';
                            
                            return (
                              <div key={idx} className="bg-muted/50 rounded-lg p-3 text-xs relative">
                                {outputText && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="absolute top-2 right-2 h-8 w-8 p-0"
                                    onClick={() => copyToClipboard(outputText, execCopyId)}
                                  >
                                    {copiedItems.has(execCopyId) ? (
                                      <Check className="h-4 w-4 text-green-600" />
                                    ) : (
                                      <Copy className="h-4 w-4" />
                                    )}
                                  </Button>
                                )}
                                <div className="flex items-center justify-between">
                                  <p className="font-medium">{call.tool_name}</p>
                                  {call.duration && (
                                    <span className="text-xs text-muted-foreground">{(call.duration * 1000).toFixed(0)}ms</span>
                                  )}
                                </div>
                                {call.tool_output && (
                                  <pre className="mt-1 text-muted-foreground overflow-x-auto pr-10">
                                    <code>{typeof call.tool_output === 'string' ? call.tool_output : JSON.stringify(call.tool_output, null, 2)}</code>
                                  </pre>
                                )}
                                {call.error && (
                                  <p className="mt-1 text-destructive">Error: {call.error}</p>
                                )}
                                <p className="text-xs text-muted-foreground mt-1">{call.timestamp}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </ScrollArea>
            </div>
          </>
        )}
      </div>

      {/* Bottom Metadata */}
      {!loading && !error && (promptData || responseData) && (
        <div className="border-t grid grid-cols-2">
          <div className="p-4 border-r bg-muted/20">
            <h4 className="font-medium text-sm mb-2 uppercase tracking-wider text-muted-foreground">MODEL METADATA</h4>
            <div className="space-y-1 text-sm">
              {promptData && (
                <>
                  <p>Model: {promptData.model || 'Unknown'}</p>
                  <p>Temperature: {promptData.temperature || 'Default'}</p>
                  {promptData.max_tokens && <p>Max Tokens: {promptData.max_tokens}</p>}
                  <p>Timestamp: {promptData.timestamp || 'Unknown'}</p>
                </>
              )}
            </div>
          </div>
          <div className="p-4 bg-muted/20">
            <h4 className="font-medium text-sm mb-2 uppercase tracking-wider text-muted-foreground">PERFORMANCE METRICS</h4>
            <div className="space-y-1 text-sm">
              {responseData && (
                <>
                  {responseData.duration && <p>Latency: {parseISODuration(responseData.duration).toFixed(2)}s</p>}
                  <p>Tool Calls: {toolCalls.length}</p>
                  {responseData.usage && (
                    <>
                      <p>Total Tokens: {responseData.usage.total_tokens}</p>
                      {responseData.usage.completion_tokens_details && (
                        <p className="text-xs text-muted-foreground">
                          ({responseData.usage.completion_tokens_details.reasoning_tokens} thinking)
                        </p>
                      )}
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
    </>
  );
}