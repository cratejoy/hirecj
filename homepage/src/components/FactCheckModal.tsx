import React from 'react';
import { Shield, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Badge } from './ui/badge';

interface FactCheckResult {
  claim: string;
  verdict: 'verified' | 'incorrect' | 'unverifiable';
  explanation: string;
  confidence?: number;
}

interface FactCheckModalProps {
  isOpen: boolean;
  onClose: () => void;
  results: FactCheckResult[] | null;
  isLoading: boolean;
  error?: string | null;
}

export function FactCheckModal({ 
  isOpen, 
  onClose, 
  results, 
  isLoading, 
  error 
}: FactCheckModalProps) {
  const getVerdictIcon = (verdict: string) => {
    switch (verdict) {
      case 'verified':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'incorrect':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'unverifiable':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      default:
        return <Shield className="w-5 h-5 text-gray-500" />;
    }
  };

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case 'verified':
        return <Badge className="bg-green-500/20 text-green-400 border-green-500/50">Verified</Badge>;
      case 'incorrect':
        return <Badge className="bg-red-500/20 text-red-400 border-red-500/50">Incorrect</Badge>;
      case 'unverifiable':
        return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/50">Unverifiable</Badge>;
      default:
        return <Badge>Unknown</Badge>;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-blue-500" />
            <span>Fact Check Results</span>
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-cratejoy-teal border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-gray-400">Verifying facts...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {results && results.length === 0 && (
            <div className="text-center py-8">
              <Shield className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <p className="text-gray-400">No specific claims found to verify in this message.</p>
            </div>
          )}

          {results && results.length > 0 && (
            <div className="space-y-4">
              {results.map((result, index) => (
                <div 
                  key={index} 
                  className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1">
                      {getVerdictIcon(result.verdict)}
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-200 mb-1">
                          {result.claim}
                        </p>
                      </div>
                    </div>
                    {getVerdictBadge(result.verdict)}
                  </div>
                  
                  <div className="pl-8">
                    <p className="text-sm text-gray-400">
                      {result.explanation}
                    </p>
                    {result.confidence && (
                      <div className="mt-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">Confidence:</span>
                          <div className="flex-1 bg-gray-700 rounded-full h-2 max-w-[100px]">
                            <div 
                              className="bg-cratejoy-teal h-2 rounded-full transition-all"
                              style={{ width: `${result.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-400">
                            {Math.round(result.confidence * 100)}%
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              <div className="bg-gray-800/30 rounded-lg p-3 border border-gray-700/50">
                <p className="text-xs text-gray-500 text-center">
                  Fact-checking is based on CJ's knowledge and available data. 
                  Always verify critical information independently.
                </p>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}