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

    // Redirect to auth service install endpoint, passing the conversation_id
    const authUrl = import.meta.env.VITE_AUTH_URL || 'https://amir-auth.hirecj.ai';
    const params = new URLSearchParams({
      shop: shop,
      conversation_id: conversationId,
    });
    const installUrl = `${authUrl}/api/v1/shopify/install?${params.toString()}`;

    // Log OAuth details for debugging
    console.log('🛍️ Shopify OAuth Debug (ShopifyOAuthButton):');
    console.log('  Auth URL:', authUrl);
    console.log('  Install URL:', installUrl);
    console.log('  Expected Redirect URI:', `${authUrl}/api/v1/shopify/callback`);
    console.log('  Shop Domain:', shop);

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
      <div className="space-y-3 p-4 bg-gray-800 rounded-lg border border-gray-700">
        <div className="text-sm text-gray-300 font-medium">
          Enter your Shopify store domain:
        </div>
        <input
          type="text"
          placeholder="yourstore or yourstore.myshopify.com"
          value={shopDomain}
          onChange={(e) => setShopDomain(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleShopSubmit();
            }
          }}
          className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-shopify-green focus:border-transparent text-white placeholder-gray-500 transition-all"
          autoFocus
        />
        <div className="flex gap-2">
          <Button
            type="button"
            onClick={handleShopSubmit}
            disabled={!shopDomain || isConnecting}
            className="flex-1 bg-shopify-green hover:bg-shopify-green-dark"
          >
            {isConnecting ? 'Redirecting...' : 'Connect'}
          </Button>
          <Button
            type="button"
            variant="secondary"
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
