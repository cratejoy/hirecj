import { useState, useCallback, useRef } from 'react';
import { logger } from '@/lib/logger';

const factCheckLogger = logger.child('fact-check');

interface FactCheckResult {
  messageIndex: number;
  results: any[];
  timestamp: string;
}

export function useFactCheck() {
  const [activeChecks, setActiveChecks] = useState<Set<number>>(new Set());
  const cache = useRef<Map<number, FactCheckResult>>(new Map());
  
  const checkFact = useCallback((messageIndex: number, sendFactCheck: (index: number) => void) => {
    // Return cached results if available
    const cached = cache.current.get(messageIndex);
    if (cached) {
      factCheckLogger.info('Returning cached fact check results', { messageIndex });
      return cached.results;
    }
    
    // Start new fact check
    factCheckLogger.info('Starting fact check', { messageIndex });
    setActiveChecks(prev => new Set(prev).add(messageIndex));
    sendFactCheck(messageIndex);
    
    return null;
  }, []);
  
  const handleFactCheckResult = useCallback((messageIndex: number, results: any[]) => {
    factCheckLogger.info('Received fact check results', { messageIndex, resultCount: results.length });
    
    // Cache the results
    cache.current.set(messageIndex, {
      messageIndex,
      results,
      timestamp: new Date().toISOString()
    });
    
    // Remove from active checks
    setActiveChecks(prev => {
      const next = new Set(prev);
      next.delete(messageIndex);
      return next;
    });
    
    return results;
  }, []);
  
  const isChecking = useCallback((messageIndex: number) => {
    return activeChecks.has(messageIndex);
  }, [activeChecks]);
  
  const getCachedResults = useCallback((messageIndex: number) => {
    return cache.current.get(messageIndex)?.results || null;
  }, []);
  
  const clearCache = useCallback(() => {
    cache.current.clear();
    setActiveChecks(new Set());
    factCheckLogger.info('Fact check cache cleared');
  }, []);
  
  return { 
    activeChecks,
    checkFact, 
    handleFactCheckResult, 
    isChecking,
    getCachedResults,
    clearCache
  };
}