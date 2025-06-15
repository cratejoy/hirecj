import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { usePlaygroundChat } from '@/hooks/usePlaygroundChat';
import { Badge } from '@/components/ui/badge';

export function TestsView() {
  const {
    messages,
    thinking,
    isConnected,
    conversationStarted,
    startConversation,
    sendMessage,
    resetConversation
  } = usePlaygroundChat();

  const [messageInput, setMessageInput] = useState('');

  const handleStartConversation = () => {
    startConversation({
      workflow: 'ad_hoc_support',
      personaId: 'test_shop',
      scenarioId: 'default',
      trustLevel: 3
    });
  };

  const handleSendMessage = () => {
    if (messageInput.trim()) {
      sendMessage(messageInput);
      setMessageInput('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex h-full flex-col p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">WebSocket Tests</h1>
        <p className="text-muted-foreground mt-2">Test the playground WebSocket functionality</p>
      </div>

      <div className="grid grid-cols-3 gap-6 flex-1">
        {/* Controls */}
        <Card>
          <CardHeader>
            <CardTitle>Connection Status</CardTitle>
            <CardDescription>WebSocket connection state</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <div className={`h-3 w-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
            
            <div className="flex items-center gap-2">
              <Badge variant={conversationStarted ? "default" : "secondary"}>
                {conversationStarted ? 'Conversation Active' : 'No Conversation'}
              </Badge>
            </div>

            <div className="space-y-2 pt-4">
              <Button 
                onClick={handleStartConversation} 
                disabled={!isConnected}
                className="w-full"
              >
                Start Conversation
              </Button>
              
              <Button 
                onClick={() => resetConversation('user_clear')} 
                variant="outline"
                disabled={!isConnected}
                className="w-full"
              >
                Reset (User Clear)
              </Button>
              
              <Button 
                onClick={() => resetConversation('workflow_change', 'order_support')} 
                variant="outline"
                disabled={!isConnected}
                className="w-full"
              >
                Reset (Workflow Change)
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Message Input */}
        <Card>
          <CardHeader>
            <CardTitle>Send Message</CardTitle>
            <CardDescription>Send a message to the agent</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type a message..."
              disabled={!isConnected || !conversationStarted}
            />
            <Button 
              onClick={handleSendMessage}
              disabled={!isConnected || !conversationStarted || !messageInput.trim()}
              className="w-full"
            >
              Send Message
            </Button>
            
            {thinking && (
              <div className="mt-4 p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                <p className="text-sm font-medium">Thinking...</p>
                <p className="text-xs text-muted-foreground">{thinking.data.status}</p>
                {thinking.data.currentTool && (
                  <p className="text-xs text-muted-foreground">Tool: {thinking.data.currentTool}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Messages */}
        <Card>
          <CardHeader>
            <CardTitle>Messages</CardTitle>
            <CardDescription>Conversation history</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px] pr-4">
              <div className="space-y-3">
                {messages.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No messages yet</p>
                ) : (
                  messages.map((msg, index) => (
                    <div key={index} className="p-3 rounded-lg bg-muted">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="text-xs">
                          CJ
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          #{index} • {new Date(msg.data.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{msg.data.content}</p>
                      {msg.data.ui_elements && (
                        <details className="mt-2">
                          <summary className="text-xs text-muted-foreground cursor-pointer">
                            UI Elements
                          </summary>
                          <pre className="text-xs mt-1 p-2 bg-background rounded">
                            {JSON.stringify(msg.data.ui_elements, null, 2)}
                          </pre>
                        </details>
                      )}
                      {msg.data.factCheckStatus && (
                        <Badge variant="secondary" className="mt-2 text-xs">
                          Fact Check: {msg.data.factCheckStatus}
                        </Badge>
                      )}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}