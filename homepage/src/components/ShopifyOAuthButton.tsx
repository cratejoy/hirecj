import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { SHOPIFY_INSTALL_POLL_INTERVAL, SHOPIFY_INSTALL_TIMEOUT } from '@/constants/shopify';

interface ShopifyOAuthButtonProps {
  conversationId: string;
  text?: string;
  className?: string;
  disabled?: boolean;
  onSuccess?: (data: any) => void;
}

export const ShopifyOAuthButton: React.FC<ShopifyOAuthButtonProps> = ({
  conversationId,
  text = 'Connect Shopify',
  className = '',
  disabled = false,
  onSuccess
}) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState('');
  const pollIntervalRef = useRef<NodeJS.Timeout>();

  const handleConnect = async () => {
    setIsConnecting(true);
    setError('');

    try {
      // Get the auth service URL from environment
      const authBaseUrl = import.meta.env.VITE_AUTH_URL || 'http://localhost:8103';
      
      // 1. Get custom install link from backend
      const response = await fetch(`${authBaseUrl}/api/v1/shopify/install`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ conversation_id: conversationId }),
      });

      if (!response.ok) {
        throw new Error('Failed to get install link');
      }

      const { install_url, session_id } = await response.json();

      // 2. Open custom install link in popup
      const width = 600;
      const height = 700;
      const left = window.screen.width / 2 - width / 2;
      const top = window.screen.height / 2 - height / 2;
      
      const popup = window.open(
        install_url,
        'shopify-install',
        `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,status=no`
      );

      // Check if popup was blocked
      if (!popup || popup.closed || typeof popup.closed === 'undefined') {
        throw new Error('Please allow pop-ups for this site to connect with Shopify');
      }

      // 3. Poll for installation status
      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusResponse = await fetch(
            `${authBaseUrl}/api/v1/shopify/status/${session_id}`
          );
          
          if (!statusResponse.ok) {
            console.error('Failed to check installation status');
            return;
          }

          const status = await statusResponse.json();

          if (status.installed) {
            // Installation complete!
            clearInterval(pollIntervalRef.current);
            popup?.close();
            
            // Get the session token from Shopify (this would come from App Bridge in production)
            // For now, we'll simulate it
            const sessionToken = 'mock-session-token'; // TODO: Get real session token
            
            // Validate the session token with backend
            const verifyResponse = await fetch(`${authBaseUrl}/api/v1/shopify/verify`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                session_token: sessionToken,
                session_id: session_id,
              }),
            });

            if (!verifyResponse.ok) {
              throw new Error('Failed to verify installation');
            }

            const verifyData = await verifyResponse.json();
            
            setIsConnecting(false);
            
            // Call success callback if provided
            if (onSuccess) {
              onSuccess({
                oauth: 'complete',
                conversation_id: conversationId,
                is_new: verifyData.is_new,
                merchant_id: verifyData.merchant_id,
                shop: verifyData.shop_domain,
              });
            }
            
            // Redirect to complete OAuth flow (similar to old callback)
            const redirectParams = new URLSearchParams({
              oauth: 'complete',
              conversation_id: conversationId,
              is_new: String(verifyData.is_new),
              merchant_id: verifyData.merchant_id,
              shop: verifyData.shop_domain,
            });
            
            window.location.href = `/chat?${redirectParams.toString()}`;
          } else if (status.error) {
            // Installation failed or expired
            clearInterval(pollIntervalRef.current);
            popup?.close();
            throw new Error(status.error);
          }
        } catch (pollError) {
          console.error('Polling error:', pollError);
        }
      }, SHOPIFY_INSTALL_POLL_INTERVAL);

      // Stop polling after timeout
      setTimeout(() => {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          popup?.close();
          setIsConnecting(false);
          setError('Installation timed out. Please try again.');
        }
      }, SHOPIFY_INSTALL_TIMEOUT);

    } catch (err) {
      console.error('Connection error:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect to Shopify');
      setIsConnecting(false);
      
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    }
  };

  // Clean up on unmount
  React.useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  return (
    <>
      <Button
        onClick={handleConnect}
        disabled={disabled || isConnecting}
        className={`bg-shopify-green hover:bg-shopify-green-dark text-white ${className}`}
        size="lg"
      >
        {isConnecting ? 'Connecting...' : text}
      </Button>
      
      {error && (
        <p className="mt-2 text-sm text-red-500">{error}</p>
      )}
    </>
  );
};