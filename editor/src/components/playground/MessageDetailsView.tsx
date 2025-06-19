import React, { useEffect, useState } from 'react';
import { X, FileText, Loader2 } from 'lucide-react';
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
  // Load debug data when opened
  useEffect(() => {
    if (isOpen && messageId && onRequestDetails) {
      setLoading(true);
      setError(null);
      onRequestDetails(messageId)
        .then(data => {
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
                      
                      {fallbackMessages.map((msg, idx) => (
                        <div key={idx}>
                          <p className="font-medium text-sm text-muted-foreground mb-2">{msg.role}:</p>
                          <div className="bg-muted rounded-lg p-3">
                            <p className="text-sm">{msg.content}</p>
                          </div>
                        </div>
                      ))}
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
                <h3 className="font-medium text-sm uppercase tracking-wider">INCOMING RESPONSE FROM LLM</h3>
              </div>
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  {responseData ? (
                    <>
                      {/* Response Content */}
                      {responseData.choices?.map((choice: any, idx: number) => (
                        <div key={idx}>
                          {choice.message?.content && (
                            <div className="mb-4">
                              <p className="text-sm whitespace-pre-wrap">{choice.message.content}</p>
                            </div>
                          )}
                          
                          {/* Tool Calls */}
                          {choice.message?.tool_calls && choice.message.tool_calls.length > 0 && (
                            <div>
                              <p className="font-medium text-sm text-muted-foreground mb-2">TOOL CALLS:</p>
                              <div className="space-y-2">
                                {choice.message.tool_calls.map((tc: any, tcIdx: number) => (
                                  <div key={tcIdx} className="bg-muted/50 rounded-lg p-3">
                                    <p className="text-sm font-medium">{tc.function?.name}</p>
                                    <pre className="text-xs mt-1 text-muted-foreground">{tc.function?.arguments}</pre>
                                  </div>
                                ))}
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
                          {toolCalls.map((call: any, idx: number) => (
                            <div key={idx} className="bg-muted/50 rounded-lg p-3 text-xs">
                              <p className="font-medium">{call.tool_name}</p>
                              {call.tool_output && (
                                <pre className="mt-1 text-muted-foreground">{typeof call.tool_output === 'string' ? call.tool_output : JSON.stringify(call.tool_output, null, 2)}</pre>
                              )}
                              {call.error && (
                                <p className="mt-1 text-destructive">Error: {call.error}</p>
                              )}
                              <p className="text-xs text-muted-foreground mt-1">{call.timestamp}</p>
                            </div>
                          ))}
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
                    <p>Total Tokens: {responseData.usage.total_tokens}</p>
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