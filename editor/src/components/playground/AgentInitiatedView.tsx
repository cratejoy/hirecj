import React from 'react';
import { Button } from '@/components/ui/button';
import { Play } from 'lucide-react';
import { WorkflowConfig } from '@/utils/workflowParser';

interface AgentInitiatedViewProps {
  workflow: WorkflowConfig;
  preview: string | null;
  onStart: () => void;
  disabled?: boolean;
}

export const AgentInitiatedView: React.FC<AgentInitiatedViewProps> = ({
  workflow,
  preview,
  onStart,
  disabled = false,
}) => {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center space-y-6 max-w-md">
        <div className="space-y-2">
          <h3 className="text-2xl font-semibold">{workflow.name}</h3>
          <p className="text-muted-foreground">{workflow.description}</p>
        </div>
        
        {preview && (
          <div className="bg-muted rounded-lg p-4">
            <p className="text-sm text-muted-foreground mb-2">CJ will start with:</p>
            <p className="italic">{preview}</p>
          </div>
        )}
        
        <Button 
          size="lg" 
          onClick={onStart}
          disabled={disabled}
          className="gap-2"
        >
          <Play className="h-5 w-5" />
          Start Conversation
        </Button>
      </div>
    </div>
  );
};