import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Send } from 'lucide-react';
import { WorkflowConfig } from '@/utils/workflowParser';

interface MerchantInitiatedViewProps {
  workflow: WorkflowConfig;
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

const PRESET_MESSAGES = [
  { value: 'sales', label: 'Check sales', message: 'Hey CJ, how are my sales looking this week?' },
  { value: 'shipping', label: 'Shipping issue', message: 'I have a customer asking about shipping delays' },
  { value: 'marketing', label: 'Marketing ideas', message: 'What marketing strategies should I try next?' },
  { value: 'help', label: 'General help', message: 'Can you help me with something?' },
];

export const MerchantInitiatedView: React.FC<MerchantInitiatedViewProps> = ({
  workflow,
  onSendMessage,
  disabled = false,
}) => {
  const [message, setMessage] = useState('');
  const [selectedPreset, setSelectedPreset] = useState('');

  const handlePresetChange = (value: string) => {
    setSelectedPreset(value);
    const preset = PRESET_MESSAGES.find(p => p.value === value);
    if (preset) {
      setMessage(preset.message);
    }
  };

  const handleSend = () => {
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
      setSelectedPreset('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4 max-w-md">
          <div className="space-y-2">
            <h3 className="text-2xl font-semibold">{workflow.name}</h3>
            <p className="text-muted-foreground">{workflow.description}</p>
          </div>
          
          <div className="bg-muted rounded-lg p-4">
            <p className="text-sm font-medium">You start the conversation</p>
            <p className="text-sm text-muted-foreground mt-1">
              CJ is waiting for your message
            </p>
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
            disabled={disabled}
            className="flex-1"
          />
          <Button 
            onClick={handleSend} 
            disabled={!message.trim() || disabled}
            size="icon"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};