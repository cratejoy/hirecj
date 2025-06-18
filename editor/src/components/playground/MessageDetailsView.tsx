import React, { useEffect } from 'react';
import { X, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

interface MessageDetailsViewProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MessageDetailsView({ isOpen, onClose }: MessageDetailsViewProps) {
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

  // All data hardcoded for now
  const systemPrompt = `You are a helpful and knowledgeable customer service agent for an e-commerce platform.

Your primary goals are to:
- Assist customers with product inquiries
- Help resolve order issues
- Provide personalized recommendations
- Maintain a friendly and professional tone

Always remember to:
- Ask clarifying questions when needed
- Reference customer history when available
- Escalate complex issues appropriately`;

  const messages = [
    { role: 'USER', content: "Hey, I'm looking for a new laptop for work. What do you recommend?" },
    { role: 'ASSISTANT', content: "I'd be happy to help you find a laptop! What's your budget and main use cases?" },
    { role: 'USER', content: "Budget is around $1500. I need it for coding and video editing." }
  ];

  const response = "For that budget, I'd suggest the MacBook Pro 14\" or Dell XPS 15. Both are excellent for coding and video editing.";

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
        {/* Left Panel - Outgoing Prompt */}
        <div className="flex-1 border-r flex flex-col">
          <div className="p-4 border-b bg-muted/30">
            <h3 className="font-medium text-sm uppercase tracking-wider">OUTGOING PROMPT TO LLM</h3>
          </div>
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              <div>
                <p className="font-medium text-sm text-muted-foreground mb-2">SYSTEM:</p>
                <pre className="text-sm whitespace-pre-wrap bg-muted/50 rounded-lg p-3">{systemPrompt}</pre>
              </div>
              
              <Separator />
              
              {messages.map((msg, idx) => (
                <div key={idx}>
                  <p className="font-medium text-sm text-muted-foreground mb-2">{msg.role}:</p>
                  <div className="bg-muted rounded-lg p-3">
                    <p className="text-sm">{msg.content}</p>
                  </div>
                </div>
              ))}
              
              <Separator />
              
              <p className="font-medium text-sm text-muted-foreground mb-2">ASSISTANT:</p>
              
              <div className="text-xs text-muted-foreground mt-4">
                [Total prompt: 1,247 tokens]
              </div>
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
              <p className="text-sm">{response}</p>
              
              <div className="border rounded-lg p-3 bg-muted/50">
                <p className="font-medium text-sm mb-2">TOOL CALL: search_products</p>
                <div className="bg-black/5 dark:bg-white/5 rounded p-3 font-mono text-xs overflow-x-auto">
                  <pre className="text-green-600 dark:text-green-400">{`Input:
{
  "category": "laptops",
  "price_range": {
    "min": 1200,
    "max": 1700
  },
  "features": ["video_editing", "programming"]
}`}</pre>
                </div>
              </div>
              
              <div className="border rounded-lg p-3 bg-muted/50">
                <p className="font-medium text-sm mb-2">TOOL OUTPUT:</p>
                <div className="bg-black/5 dark:bg-white/5 rounded p-3 font-mono text-xs overflow-x-auto">
                  <pre className="text-green-600 dark:text-green-400">{`Results:
[
  {
    "name": "MacBook Pro 14\"",
    "price": 1599,
    "specs": {
      "cpu": "M3 Pro",
      "ram": "18GB",
      "gpu": "11-core"
    }
  },
  {
    "name": "Dell XPS 15",
    "price": 1499,
    "specs": {
      "cpu": "i7-13700H",
      "ram": "16GB",
      "gpu": "RTX 4050"
    }
  }
]`}</pre>
                </div>
              </div>
              
              <p className="text-sm">The MacBook Pro 14" offers excellent performance for video editing with its dedicated media engine. The Dell XPS 15 provides great value with a powerful GPU.</p>
              
              <div className="border rounded-lg p-3 bg-muted/50">
                <p className="font-medium text-sm mb-2">TOOL CALL: check_inventory</p>
                <div className="bg-black/5 dark:bg-white/5 rounded p-3 font-mono text-xs overflow-x-auto">
                  <pre className="text-green-600 dark:text-green-400">{`Input:
{
  "product_ids": ["MBP14-M3", "DELL-XPS15-2024"]
}`}</pre>
                </div>
              </div>
              
              <div className="border rounded-lg p-3 bg-muted/50">
                <p className="font-medium text-sm mb-2">TOOL OUTPUT:</p>
                <div className="bg-black/5 dark:bg-white/5 rounded p-3 font-mono text-xs overflow-x-auto">
                  <pre className="text-green-600 dark:text-green-400">{`{
  "MBP14-M3": {
    "available": true,
    "stock": 12,
    "delivery": "2-3 days"
  },
  "DELL-XPS15-2024": {
    "available": true,
    "stock": 8,
    "delivery": "3-5 days"
  }
}`}</pre>
                </div>
              </div>
              
              <p className="text-sm">Both laptops are in stock. The MacBook can be delivered in 2-3 days, while the Dell would take 3-5 days...</p>
              
              <div className="text-xs text-muted-foreground mt-4">
                [Total response: 2,156 tokens]
              </div>
            </div>
          </ScrollArea>
        </div>
      </div>

      {/* Bottom Metadata */}
      <div className="border-t grid grid-cols-2">
        <div className="p-4 border-r bg-muted/20">
          <h4 className="font-medium text-sm mb-2 uppercase tracking-wider text-muted-foreground">MODEL METADATA</h4>
          <div className="space-y-1 text-sm">
            <p>Model: gpt-4-turbo-2024-04-09</p>
            <p>Temperature: 0.7</p>
            <p>Max Tokens: 2048</p>
            <p>Timestamp: 2024-01-19 14:32:18 UTC</p>
          </div>
        </div>
        <div className="p-4 bg-muted/20">
          <h4 className="font-medium text-sm mb-2 uppercase tracking-wider text-muted-foreground">PERFORMANCE METRICS</h4>
          <div className="space-y-1 text-sm">
            <p>Latency: 2.3s</p>
            <p>Tool Calls: 2</p>
            <p>Total Cost: $0.0342</p>
            <p>Cache Hit: No</p>
          </div>
        </div>
      </div>
    </div>
    </>
  );
}