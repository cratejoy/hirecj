import { useState, useEffect } from 'react';

interface UserSession {
  // State
  merchantId: string | null;
  shopDomain: string | null;
  isConnected: boolean;
  
  // Actions
  setMerchant: (merchantId: string, shopDomain: string) => void;
  clearMerchant: () => void;
}

export function useUserSession(): UserSession {
  // Load initial state from localStorage
  const [merchantId, setMerchantId] = useState<string | null>(() => 
    localStorage.getItem('merchantId') || null
  );
  const [shopDomain, setShopDomain] = useState<string | null>(() => 
    localStorage.getItem('shopDomain') || null
  );

  // Update localStorage when merchantId changes
  useEffect(() => {
    if (merchantId) {
      localStorage.setItem('merchantId', merchantId);
    } else {
      localStorage.removeItem('merchantId');
    }
  }, [merchantId]);

  // Update localStorage when shopDomain changes
  useEffect(() => {
    if (shopDomain) {
      localStorage.setItem('shopDomain', shopDomain);
    } else {
      localStorage.removeItem('shopDomain');
    }
  }, [shopDomain]);

  return {
    // State
    merchantId,
    shopDomain,
    isConnected: !!merchantId,
    
    // Actions
    setMerchant: (id: string, shop: string) => {
      setMerchantId(id);
      setShopDomain(shop);
    },
    clearMerchant: () => {
      setMerchantId(null);
      setShopDomain(null);
    }
  };
}