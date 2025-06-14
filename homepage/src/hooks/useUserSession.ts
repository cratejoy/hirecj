import { useState, useEffect } from 'react';

interface UserSession {
  // State
  shopSubdomain: string | null;
  shopDomain: string | null;
  isConnected: boolean;
  
  // Actions
  setMerchant: (subdomain: string, domain: string) => void;
  clearMerchant: () => void;
}

export function useUserSession(): UserSession {
  // Load initial state from localStorage
  const [shopSubdomain, setShopSubdomain] = useState<string | null>(() => 
    localStorage.getItem('shopSubdomain') || null
  );
  const [shopDomain, setShopDomain] = useState<string | null>(() => 
    localStorage.getItem('shopDomain') || null
  );

  // Update localStorage when shopSubdomain changes
  useEffect(() => {
    if (shopSubdomain) {
      localStorage.setItem('shopSubdomain', shopSubdomain);
    } else {
      localStorage.removeItem('shopSubdomain');
    }
  }, [shopSubdomain]);

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
    shopSubdomain,
    shopDomain,
    isConnected: !!shopSubdomain,
    
    // Actions
    setMerchant: (subdomain: string, domain: string) => {
      setShopSubdomain(subdomain);
      setShopDomain(domain);
    },
    clearMerchant: () => {
      setShopSubdomain(null);
      setShopDomain(null);
    }
  };
}
