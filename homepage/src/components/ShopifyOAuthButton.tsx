import React, { useState } from 'react';
import { Button } from '@/components/ui/button';

interface ShopifyOAuthButtonProps {
  conversationId: string;
  text?: string;
  className?: string;
  disabled?: boolean;
}

export const ShopifyOAuthButton: React.FC<ShopifyOAuthButtonProps> = ({
  conversationId,
  text = 'Connect Shopify',
  className = '',
  disabled = false
}) => {
  const [isConnecting, setIsConnecting] = useState(false);

  const handleConnect = () => {
    setIsConnecting(true);

    // Get install URL directly from environment
    const installUrl = import.meta.env.VITE_SHOPIFY_CUSTOM_INSTALL_LINK;
    
    if (!installUrl) {
      console.error('VITE_SHOPIFY_CUSTOM_INSTALL_LINK not configured');
      return;
    }
    
    // Add conversation_id to the install URL so it comes back in redirect
    const separator = installUrl.includes('?') ? '&' : '?';
    const urlWithConversation = `${installUrl}${separator}conversation_id=${conversationId}`;

    // Simply redirect to the install link
    // Shopify will handle everything and redirect back to our /connected endpoint
    window.location.href = urlWithConversation;
  };

  return (
    <Button
      onClick={handleConnect}
      disabled={disabled || isConnecting}
      className={`bg-shopify-green hover:bg-shopify-green-dark text-white ${className}`}
      size="lg"
    >
      {isConnecting ? 'Redirecting to Shopify...' : text}
    </Button>
  );
};