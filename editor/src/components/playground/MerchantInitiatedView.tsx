import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Send, User, MessageSquare, TrendingUp, CheckCircle, CreditCard, Loader2 } from 'lucide-react';
import { WorkflowConfig } from '@/utils/workflowParser';

interface Persona {
  id: string;
  name: string;
  business: string;
}

interface Scenario {
  id: string;
  name: string;
  description: string;
}

interface MerchantInitiatedViewProps {
  workflow: WorkflowConfig;
  persona?: Persona;
  scenario?: Scenario;
  trustLevel?: number;
  onSendMessage: (message: string) => void | Promise<void>;
  disabled?: boolean;
}

const PRESET_MESSAGES = [
  { value: 'sales', label: '📊 Check sales', message: 'Hey CJ, how are my sales looking this week?' },
  { value: 'shipping', label: '🚚 Shipping issue', message: 'I have a customer asking about shipping delays' },
  { value: 'marketing', label: '💡 Marketing ideas', message: 'What marketing strategies should I try next?' },
  { value: 'promotion', label: '🛍️ Plan promotion', message: 'Can you help me plan a promotion?' },
  { value: 'help', label: '❓ General help', message: 'I need help with...' },
];

const getTrustLevelActions = (trustLevel: number) => {
  const baseActions = [
    { icon: MessageSquare, text: 'Answer questions' },
    { icon: TrendingUp, text: 'Look up metrics' },
    { icon: CheckCircle, text: 'Provide recommendations' },
  ];
  
  if (trustLevel >= 3) {
    baseActions.push({ icon: CreditCard, text: 'Issue credits (up to $100)' });
  }
  
  return baseActions;
};

export const MerchantInitiatedView: React.FC<MerchantInitiatedViewProps> = ({
  workflow: _workflow,
  persona,
  scenario: _scenario,
  trustLevel = 3,
  onSendMessage,
  disabled = false,
}) => {
  const [message, setMessage] = useState('');
  const [selectedPreset, setSelectedPreset] = useState('');
  const [sending, setSending] = useState(false);

  const handlePresetChange = (value: string) => {
    setSelectedPreset(value);
    const preset = PRESET_MESSAGES.find(p => p.value === value);
    if (preset) {
      setMessage(preset.message);
    }
  };

  const handleSend = async () => {
    if (message.trim() && !sending) {
      setSending(true);
      try {
        await onSendMessage(message);
        setMessage('');
        setSelectedPreset('');
      } catch (error) {
        console.error('Failed to send message:', error);
      } finally {
        setSending(false);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !sending) {
      e.preventDefault();
      handleSend();
    }
  };

  const actions = getTrustLevelActions(trustLevel);

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-1">
        {/* Left Panel - Agent Perspective */}
        <div className="flex-1 flex items-center justify-center border-r">
          <div className="text-center space-y-6 max-w-md">
            <p className="text-lg text-muted-foreground">Waiting for merchant...</p>
            
            <div className="relative">
              <div className="h-24 w-24 mx-auto rounded-full bg-primary/10 flex items-center justify-center">
                <span className="text-3xl">👋</span>
              </div>
              <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 bg-background px-3 py-1 rounded-full border">
                <p className="text-sm font-medium">CJ Ready</p>
              </div>
            </div>

            <div className="text-left space-y-3">
              <p className="text-sm font-medium text-center">Trust Level: {trustLevel}</p>
              <div className="space-y-2">
                <p className="text-sm font-medium">Available Actions:</p>
                {actions.map((action, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <action.icon className="h-4 w-4" />
                    <span>{action.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - User Perspective */}
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-6">
            {persona && (
              <Card className="p-6 max-w-sm">
                <div className="flex items-center gap-3 mb-4">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="h-5 w-5 text-primary" />
                  </div>
                  <div className="text-left">
                    <p className="font-medium">{persona.name}</p>
                    <p className="text-sm text-muted-foreground">{persona.business} Founder</p>
                  </div>
                </div>
                
                <div className="text-center space-y-2">
                  <p className="font-medium">Ready to chat with</p>
                  <p className="text-sm text-muted-foreground">your CJ assistant</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
      
      <div className="border-t p-4 space-y-3">
        <Select value={selectedPreset} onValueChange={handlePresetChange}>
          <SelectTrigger>
            <SelectValue placeholder="Choose a preset message or type your own" />
          </SelectTrigger>
          <SelectContent>
            {PRESET_MESSAGES.map(preset => (
              <SelectItem key={preset.value} value={preset.value}>
                {preset.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        
        <div className="flex gap-2">
          <Input 
            placeholder="Type your message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={disabled || sending}
            className="flex-1"
          />
          <Button 
            onClick={handleSend} 
            disabled={!message.trim() || disabled || sending}
            size="icon"
          >
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};