import React from 'react';
import { Shield, ShieldCheck, Loader } from 'lucide-react';
import { Button } from './ui/button';

interface FactCheckButtonProps {
  messageIndex: number;
  isAvailable: boolean;
  isChecking: boolean;
  hasResults: boolean;
  onClick: () => void;
}

export function FactCheckButton({ 
  messageIndex, 
  isAvailable, 
  isChecking, 
  hasResults, 
  onClick 
}: FactCheckButtonProps) {
  if (!isAvailable) return null;

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onClick}
      disabled={isChecking}
      className={`
        flex items-center gap-1 text-xs h-auto py-1 px-2
        ${hasResults 
          ? 'text-blue-400 hover:text-blue-300' 
          : 'text-gray-400 hover:text-gray-300'
        }
      `}
    >
      {isChecking ? (
        <>
          <Loader className="w-3 h-3 animate-spin" />
          <span>Checking...</span>
        </>
      ) : (
        <>
          {hasResults ? (
            <ShieldCheck className="w-3 h-3" />
          ) : (
            <Shield className="w-3 h-3" />
          )}
          <span>{hasResults ? 'View Facts' : 'Fact Check'}</span>
        </>
      )}
    </Button>
  );
}