"""Shopify OAuth provider for merchant authentication."""

import logging
from typing import Dict, Any
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.providers.base import LoginProvider, OAuthToken

logger = logging.getLogger(__name__)


class ShopifyProvider(LoginProvider):
    """
    Shopify OAuth provider for merchant login.
    
    Shopify uses a slightly different OAuth flow where the shop domain
    is part of the OAuth URLs.
    """
    
    def __init__(self):
        # Note: Shopify URLs are dynamic based on shop domain
        super().__init__(
            name="shopify",
            client_id=settings.shopify_client_id or "",
            client_secret=settings.shopify_client_secret or "",
            authorize_url="https://{shop}.myshopify.com/admin/oauth/authorize",
            token_url="https://{shop}.myshopify.com/admin/oauth/access_token",
            scopes=settings.shopify_scopes.split(",")
        )
    
    async def get_authorization_url(self, redirect_uri: str, state: str, **kwargs) -> str:
        """
        Generate Shopify OAuth authorization URL.
        
        Args:
            redirect_uri: The callback URL
            state: Security state parameter
            shop: The Shopify shop domain (e.g., 'mystore' or 'mystore.myshopify.com')
            
        Returns:
            The authorization URL
        """
        shop = kwargs.get("shop")
        if not shop:
            raise ValueError("Shop domain is required for Shopify OAuth")
        
        # Clean shop domain
        shop = shop.replace("https://", "").replace("http://", "")
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        
        params = {
            "client_id": self.client_id,
            "scope": self.get_scopes_string(),
            "redirect_uri": redirect_uri,
            "state": state
        }
        
        auth_url = self.authorize_url.format(shop=shop.replace(".myshopify.com", ""))
        return f"{auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str, **kwargs) -> OAuthToken:
        """
        Exchange authorization code for Shopify access token.
        
        Args:
            code: The authorization code
            redirect_uri: The callback URL
            shop: The Shopify shop domain
            
        Returns:
            OAuthToken with permanent access token
        """
        shop = kwargs.get("shop")
        if not shop:
            raise ValueError("Shop domain is required for token exchange")
        
        # Clean shop domain
        shop = shop.replace("https://", "").replace("http://", "")
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        
        token_url = self.token_url.format(shop=shop.replace(".myshopify.com", ""))
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, json=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Shopify returns a permanent access token
            return OAuthToken(
                access_token=token_data["access_token"],
                scope=token_data.get("scope", ""),
                extra_data={
                    "shop": shop,
                    "associated_user_scope": token_data.get("associated_user_scope"),
                    "associated_user": token_data.get("associated_user")
                }
            )
    
    async def refresh_access_token(self, refresh_token: str) -> OAuthToken:
        """
        Shopify access tokens don't expire, so refresh is not needed.
        
        Raises:
            NotImplementedError: Shopify tokens don't need refresh
        """
        raise NotImplementedError("Shopify access tokens are permanent and don't need refresh")
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a Shopify access token.
        
        Note: This requires knowing the shop domain.
        """
        # TODO: Implement token revocation
        # This would require storing the shop domain with the token
        logger.warning("Shopify token revocation not yet implemented")
        return False
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get shop information using the access token.
        
        Args:
            access_token: Valid Shopify access token
            
        Returns:
            Shop information including owner details
        """
        # Extract shop domain from token's extra data
        # In production, this would come from our token storage
        shop = "demo-shop"  # TODO: Get from token storage
        
        shop_url = f"https://{shop}.myshopify.com/admin/api/2024-01/shop.json"
        
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(shop_url, headers=headers)
            response.raise_for_status()
            
            shop_data = response.json()["shop"]
            
            # Return standardized user info
            return {
                "id": str(shop_data["id"]),
                "email": shop_data["email"],
                "name": shop_data["shop_owner"],
                "shop_name": shop_data["name"],
                "shop_domain": shop_data["domain"],
                "timezone": shop_data["timezone"],
                "currency": shop_data["currency"],
                "country": shop_data["country_name"],
                "plan_name": shop_data.get("plan_name"),
                "raw_data": shop_data
            }