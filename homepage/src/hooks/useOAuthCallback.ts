import { useEffect, useCallback } from 'react';
import { useLocation } from 'wouter';

interface OAuthCallbackParams {
  oauth: string;
  conversation_id: string;
  is_new: string;
  merchant_id?: string;
  shop?: string;
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
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
      return;
    }
    
    if (params.get('oauth') === 'complete') {
      const callbackData: OAuthCallbackParams = {
        oauth: 'complete',
        conversation_id: params.get('conversation_id') || '',
        is_new: params.get('is_new') || 'true',
        merchant_id: params.get('merchant_id') || undefined,
        shop: params.get('shop') || undefined,
        error: params.get('error') || undefined
      };
      
      if (callbackData.error) {
        onError(callbackData.error);
      } else {
        onSuccess(callbackData);
      }
      
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [onSuccess, onError]);
  
  useEffect(() => {
    handleCallback();
  }, [handleCallback]);
  
  return { handleCallback };
};