import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';

interface ShopifyOAuthButtonProps {
  text?: string;
  className?: string;
  disabled?: boolean;
}

export const ShopifyOAuthButton: React.FC<ShopifyOAuthButtonProps> = ({
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

  const initiateOAuth = async (shop: string) => {
    // Normalize shop domain
    if (!shop.endsWith(".myshopify.com")) {
      shop = `${shop}.myshopify.com`;
    }

    setIsConnecting(true);

    const authUrlBase =
      import.meta.env.VITE_AUTH_URL || "https://amir-auth.hirecj.ai";

    // ONE direct navigation – no pre-flight, no CORS
    const redirect = `${authUrlBase}/api/v1/shopify/install?shop=${encodeURIComponent(
      shop
    )}`;

    window.location.assign(redirect);
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
      {isConnecting ? (
        <>
          <svg
            className="animate-spin h-4 w-4 mr-2"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"
            />
          </svg>
          Connecting…
        </>
      ) : (
        text
      )}
    </Button>
  );
};
