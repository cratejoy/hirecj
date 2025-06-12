import { useEffect, useCallback } from 'react';
import { useLocation } from 'wouter';

interface OAuthCallbackParams {
  oauth: string;
  conversation_id: string;
  is_new: string;
  merchant_id?: string;
  shop?: string;
  user_id?: string;
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
      
      // Remove only oauth / error params, keep others (e.g. workflow)
      params.delete('oauth');
      params.delete('error');
      const remaining = params.toString();
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
