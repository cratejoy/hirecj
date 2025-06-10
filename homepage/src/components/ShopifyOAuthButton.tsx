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
      <form
        className="space-y-3 p-4 bg-gray-800 rounded-lg border border-gray-700"
        onSubmit={(e) => {
          e.preventDefault();
          handleShopSubmit();
        }}
      >
        <div className="text-sm text-gray-300 font-medium">
          Enter your Shopify store domain:
        </div>
        <input
          type="text"
          placeholder="yourstore or yourstore.myshopify.com"
          value={shopDomain}
          onChange={(e) => setShopDomain(e.target.value)}
          className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-shopify-green focus:border-transparent text-white placeholder-gray-500 transition-all"
          autoFocus
        />
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={!shopDomain || isConnecting}
            className="flex-1 bg-shopify-green hover:bg-shopify-green-dark disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 px-4 rounded-lg transition-colors"
          >
            {isConnecting ? 'Redirecting...' : 'Connect'}
          </button>
          <button
            type="button"
            onClick={() => {
              setShowShopInput(false);
              setShopDomain('');
            }}
            className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-300 font-medium rounded-lg transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
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
