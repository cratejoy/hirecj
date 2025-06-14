"""Shopify OAuth utilities."""

import hmac
import hashlib
import secrets
import base64
import re
import logging
from typing import Dict, Optional
from urllib.parse import urlencode

from app.config import settings

logger = logging.getLogger(__name__)

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
        
        # Sort parameters and join without additional percent-encoding
        # Per Shopify docs, keys must be sorted alphabetically.
        sorted_params = sorted(params.items())
        
        # NOTE: The values must NOT be URL-encoded again. They are used as-is from the query string.
        # This is a common mistake. The `&` and `=` characters are part of the message to be signed.
        query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        
        # Calculate HMAC
        secret = settings.shopify_client_secret.encode('utf-8')
        message = query_string.encode('utf-8')
        calculated_hmac = hmac.new(
            secret, 
            message, 
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        is_valid = hmac.compare_digest(calculated_hmac, provided_hmac)
        
        # Add extensive logging for debugging HMAC issues, especially on failure
        if settings.debug:
            if not is_valid:
                logger.error("[HMAC_VALIDATION] FAILED")
            else:
                logger.info("[HMAC_VALIDATION] SUCCESS")
            
            logger.info("[HMAC_VALIDATION] Debug Details:")
            logger.info(f"  - Client Secret Used: '{settings.shopify_client_secret}'")
            logger.info(f"  - Query String for HMAC: '{query_string}'")
            logger.info(f"  - Provided HMAC:   '{provided_hmac}'")
            logger.info(f"  - Calculated HMAC: '{calculated_hmac}'")
            
        return is_valid
    
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
        
        # Log the exact parameters being used
        logger.info(f"[SHOPIFY_AUTH] Building auth URL with:")
        logger.info(f"  shop: {shop}")
        logger.info(f"  client_id: {settings.shopify_client_id}")
        logger.info(f"  redirect_uri: {redirect_uri}")
        logger.info(f"  scopes: {settings.shopify_scopes}")
        
        # Debug: Check for any special characters
        logger.info(f"[SHOPIFY_AUTH] Redirect URI analysis:")
        logger.info(f"  Length: {len(redirect_uri)}")
        logger.info(f"  Starts with: {redirect_uri[:50]}")
        logger.info(f"  Ends with: {redirect_uri[-50:]}")
        logger.info(f"  Contains spaces: {' ' in redirect_uri}")
        logger.info(f"  URL encoded: {urlencode({'redirect_uri': redirect_uri})}")
        
        query_string = urlencode(params)
        auth_url = f"https://{shop}/admin/oauth/authorize?{query_string}"
        
        logger.info(f"[SHOPIFY_AUTH] Full auth URL: {auth_url}")
        
        # Extract just the redirect_uri param from the final URL for verification
        import urllib.parse
        parsed = urllib.parse.urlparse(auth_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        final_redirect_uri = query_params.get('redirect_uri', [''])[0]
        logger.info(f"[SHOPIFY_AUTH] Final redirect_uri in URL: '{final_redirect_uri}'")
        
        return auth_url

# Singleton instance
shopify_auth = ShopifyAuth()
