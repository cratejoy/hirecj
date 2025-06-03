import React from 'react';
import { Button } from '@/components/ui/button';

interface OAuthButtonProps {
  provider: 'shopify';
  text?: string;
  className?: string;
  disabled?: boolean;
}

export const OAuthButton: React.FC<OAuthButtonProps> = ({
  provider,
  text = 'Connect Shopify',
  className = '',
  disabled = false
}) => {
  return (
    <Button
      disabled={disabled}
      className={`bg-shopify-green hover:bg-shopify-green-dark text-white ${className}`}
      size="lg"
    >
      {text}
    </Button>
  );
};