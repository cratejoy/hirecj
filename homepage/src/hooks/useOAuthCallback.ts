import { useEffect, useCallback } from 'react';
import { useLocation } from 'wouter';

interface OAuthCallbackParams {
  oauth: 'complete';
  error?: string;
}

export const useOAuthCallback = (
  onSuccess: (params: OAuthCallbackParams) => void,
  onError: (error: string) => void
) => {
  const [location] = useLocation();
  
  const handleCallback = useCallback(() => {
    const params = new URLSearchParams(window.location.search);
    
    // Handle error parameter even without oauth=complete
    const error = params.get('error');
    if (error) {
      console.error('[OAuth] Error in URL:', error);
      onError(error);
      params.delete('error');
      const rest = params.toString();
      window.history.replaceState({}, '', rest ? `${window.location.pathname}?${rest}` : window.location.pathname);
      return;
    }
    
    if (params.get('oauth') === 'complete') {
      const callbackData: OAuthCallbackParams = { oauth: 'complete' };
      
      if (params.get('error')) {
        callbackData.error = params.get('error') || undefined;
      }

      if (callbackData.error) {
        onError(callbackData.error);
      } else {
        onSuccess(callbackData);
      }

      // Remove only oauth / error params, keep others (e.g. workflow)
      const remaining = (() => {
        params.delete('oauth');
        params.delete('error');
        return params.toString();
      })();
      window.history.replaceState(
        {},
        '',
        remaining ? `${window.location.pathname}?${remaining}` : window.location.pathname
      );
    }
  }, [onSuccess, onError]);
  
  useEffect(() => {
    handleCallback();
  }, [handleCallback]);
  
  return { handleCallback };
};
