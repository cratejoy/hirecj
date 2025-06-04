import React, { useState, useEffect } from 'react';
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
  const [shopDomain, setShopDomain] = useState('');
  const [showShopInput, setShowShopInput] = useState(false);

  // Clear any stored shop domain on mount
  useEffect(() => {
    localStorage.removeItem('shopify_shop_domain');
  }, []);

  const handleConnect = () => {
    // Always show input for shop domain
    setShowShopInput(true);
  };

  const initiateOAuth = (shop: string) => {
    setIsConnecting(true);
    
    // Validate shop domain format
    if (!shop.endsWith('.myshopify.com')) {
      shop = `${shop}.myshopify.com`;
    }
    
    // Store conversation ID for later (OAuth doesn't preserve it)
    sessionStorage.setItem('shopify_oauth_conversation_id', conversationId);
    
    // Redirect to auth service install endpoint
    const authUrl = import.meta.env.VITE_AUTH_URL || 'https://amir-auth.hirecj.ai';
    const installUrl = `${authUrl}/api/v1/shopify/install?shop=${encodeURIComponent(shop)}`;
    
    // Redirect to start OAuth flow
    window.location.href = installUrl;
  };

  const handleShopSubmit = () => {
    if (shopDomain) {
      initiateOAuth(shopDomain);
    }
  };

  if (showShopInput) {
    return (
      <div className="space-y-2">
        <div className="text-sm text-gray-600">
          Enter your Shopify store domain:
        </div>
        <input
          type="text"
          placeholder="yourstore or yourstore.myshopify.com"
          value={shopDomain}
          onChange={(e) => setShopDomain(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-shopify-green text-gray-900 bg-white placeholder-gray-500"
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              handleShopSubmit();
            }
          }}
          autoFocus
        />
        <div className="flex gap-2">
          <Button
            onClick={handleShopSubmit}
            disabled={!shopDomain || isConnecting}
            className={`bg-shopify-green hover:bg-shopify-green-dark text-white ${className}`}
          >
            {isConnecting ? 'Redirecting...' : 'Connect'}
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setShowShopInput(false);
              setShopDomain('');
            }}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

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