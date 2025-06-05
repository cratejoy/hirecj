import React from 'react';
import { Button } from '@/components/ui/button';

interface OAuthButtonProps {
  provider: 'shopify';
  conversationId: string;
  text?: string;
  className?: string;
  disabled?: boolean;
}

export const OAuthButton: React.FC<OAuthButtonProps> = ({
  provider,
  conversationId,
  text = 'Connect Shopify',
  className = '',
  disabled = false
}) => {
  const handleOAuthClick = () => {
    // Get the OAuth URL from environment or use default
    const authBaseUrl = import.meta.env.VITE_AUTH_URL || 'http://localhost:8103';
    
    // Build OAuth URL - use the correct endpoint for Shopify
    const oauthUrl = `${authBaseUrl}/api/v1/shopify/install?conversation_id=${conversationId}`;
    
    // Log OAuth details for debugging
    console.log('🛍️ Shopify OAuth Debug:');
    console.log('  Auth Base URL:', authBaseUrl);
    console.log('  OAuth URL:', oauthUrl);
    console.log('  Expected Redirect URI:', `${authBaseUrl}/api/v1/shopify/callback`);
    
    // Open OAuth flow in new window
    const width = 600;
    const height = 700;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;
    
    window.open(
      oauthUrl,
      'shopify-oauth',
      `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,status=no`
    );
  };

  return (
    <Button
      onClick={handleOAuthClick}
      disabled={disabled}
      className={`bg-shopify-green hover:bg-shopify-green-dark text-white ${className}`}
      size="lg"
    >
      {text}
    </Button>
  );
};