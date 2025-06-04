"""Shopify OAuth utilities."""

import hmac
import hashlib
import secrets
import base64
import re
from typing import Dict, Optional
from urllib.parse import urlencode

from app.config import settings

class ShopifyAuth:
    """Handle Shopify OAuth operations."""
    
    @staticmethod
    def verify_hmac(params: Dict[str, str]) -> bool:
        """
        Verify HMAC signature from Shopify.
        
        Args:
            params: Query parameters from Shopify (will be modified - hmac removed)
            
        Returns:
            True if HMAC is valid
        """
        # Extract and remove HMAC from params
        provided_hmac = params.pop('hmac', None)
        if not provided_hmac:
            return False
        
        # Sort parameters and create query string
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        
        # Calculate HMAC
        secret = settings.shopify_client_secret.encode('utf-8')
        message = query_string.encode('utf-8')
        calculated_hmac = hmac.new(
            secret, 
            message, 
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(calculated_hmac, provided_hmac)
    
    @staticmethod
    def validate_shop_domain(shop: str) -> bool:
        """
        Validate shop domain format.
        
        Args:
            shop: Shop domain (e.g., "example.myshopify.com")
            
        Returns:
            True if valid Shopify domain
        """
        if not shop:
            return False
        
        # Must end with .myshopify.com
        if not shop.endswith('.myshopify.com'):
            return False
        
        # Extract subdomain
        subdomain = shop.replace('.myshopify.com', '')
        
        # Validate subdomain format (alphanumeric and hyphens)
        # Must start and end with alphanumeric, can contain hyphens in middle
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$'
        return bool(re.match(pattern, subdomain))
    
    @staticmethod
    def generate_state() -> str:
        """Generate secure random state for OAuth."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def build_auth_url(shop: str, state: str, redirect_uri: str) -> str:
        """
        Build Shopify OAuth authorization URL.
        
        Args:
            shop: Shop domain
            state: Random state for CSRF protection
            redirect_uri: OAuth callback URL
            
        Returns:
            Full authorization URL
        """
        params = {
            'client_id': settings.shopify_client_id,
            'scope': settings.shopify_scopes,
            'redirect_uri': redirect_uri,
            'state': state
        }
        
        query_string = urlencode(params)
        return f"https://{shop}/admin/oauth/authorize?{query_string}"

# Singleton instance
shopify_auth = ShopifyAuth()