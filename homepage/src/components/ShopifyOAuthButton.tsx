import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';

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
  const [isOpen, setIsOpen] = useState(false);
  const [shopDomain, setShopDomain] = useState('');
  const [error, setError] = useState('');

  const handleConnect = () => {
    // Validate shop domain
    if (!shopDomain.trim()) {
      setError('Please enter your shop domain');
      return;
    }

    // Clean up shop domain (remove protocol, trailing slashes)
    let cleanShop = shopDomain.trim()
      .replace(/^https?:\/\//, '')
      .replace(/\/$/, '');
    
    // Add .myshopify.com if not present
    if (!cleanShop.includes('.')) {
      cleanShop = `${cleanShop}.myshopify.com`;
    }

    // Get the OAuth URL from environment
    const authBaseUrl = import.meta.env.VITE_AUTH_URL || 'http://localhost:8103';
    
    // Build OAuth URL with shop domain
    const oauthUrl = `${authBaseUrl}/api/v1/oauth/shopify/authorize?conversation_id=${conversationId}&redirect_uri=${encodeURIComponent(window.location.origin + '/chat')}&shop=${cleanShop}`;
    
    // Open OAuth flow in new window
    const width = 600;
    const height = 700;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;
    
    const popup = window.open(
      oauthUrl,
      'shopify-oauth',
      `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,status=no`
    );

    // Close dialog
    setIsOpen(false);
    setShopDomain('');
    setError('');

    // Check if popup was blocked
    if (!popup || popup.closed || typeof popup.closed === 'undefined') {
      alert('Please allow pop-ups for this site to connect with Shopify');
    }
  };

  return (
    <>
      <Button
        onClick={() => setIsOpen(true)}
        disabled={disabled}
        className={`bg-shopify-green hover:bg-shopify-green-dark text-white ${className}`}
        size="lg"
      >
        {text}
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Connect Your Shopify Store</DialogTitle>
            <DialogDescription>
              Enter your Shopify store domain to get started. For example: "my-store" or "my-store.myshopify.com"
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Input
                placeholder="your-store"
                value={shopDomain}
                onChange={(e) => {
                  setShopDomain(e.target.value);
                  setError('');
                }}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleConnect();
                  }
                }}
                className={error ? 'border-red-500' : ''}
              />
              {error && (
                <p className="text-sm text-red-500">{error}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Don't include "https://" or ".myshopify.com" - we'll add it for you
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleConnect}
              className="bg-shopify-green hover:bg-shopify-green-dark text-white"
            >
              Connect to Shopify
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};