import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Play, User, TrendingUp, Shield, Loader2 } from 'lucide-react';
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

interface AgentInitiatedViewProps {
  workflow: WorkflowConfig;
  preview: string | null;
  persona?: Persona;
  scenario?: Scenario;
  trustLevel?: number;
  onStart: () => void | Promise<void>;
  disabled?: boolean;
}

export const AgentInitiatedView: React.FC<AgentInitiatedViewProps> = ({
  workflow: _workflow,
  preview,
  persona,
  scenario,
  trustLevel = 3,
  onStart,
  disabled = false,
}) => {
  const [starting, setStarting] = useState(false);

  const handleStart = async () => {
    if (!starting) {
      setStarting(true);
      try {
        await onStart();
      } catch (error) {
        console.error('Failed to start conversation:', error);
      } finally {
        setStarting(false);
      }
    }
  };

  return (
    <div className="flex h-full">
      {/* Left Panel - Agent Perspective */}
      <div className="flex-1 flex items-center justify-center border-r">
        <div className="text-center space-y-8 max-w-md">
          <Button 
            size="lg" 
            onClick={handleStart}
            disabled={disabled || starting}
            className="h-20 w-20 rounded-full"
          >
            {starting ? (
              <Loader2 className="h-8 w-8 animate-spin" />
            ) : (
              <Play className="h-8 w-8" />
            )}
          </Button>
          
          <div className="space-y-2">
            <p className="text-lg font-medium">Click to start CJ outreach</p>
            
            {scenario && (
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Scenario: {scenario.name}</p>
                <p className="flex items-center justify-center gap-1">
                  <Shield className="h-3 w-3" />
                  Trust Level: {trustLevel}
                </p>
              </div>
            )}
          </div>

          {preview && (
            <div className="bg-muted rounded-lg p-4 text-left">
              <p className="text-sm text-muted-foreground mb-2">CJ will start with:</p>
              <p className="text-sm italic">{preview}</p>
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - User Perspective */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-6">
          <p className="text-lg text-muted-foreground">Waiting for CJ to begin...</p>
          
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
              
              {scenario && (
                <div className="text-left space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Current Scenario:</span>
                  </div>
                  <p className="font-medium">{scenario.name}</p>
                </div>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};