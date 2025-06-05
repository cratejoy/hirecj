"""Shopify API utilities for raw API calls."""

import os
import time
import json
from typing import Dict, Any, Optional, List, Tuple
import requests
from urllib.parse import urlparse, parse_qs

# Use centralized config - no direct load_dotenv!
from shared.env_loader import get_env


class ShopifyAPI:
    """Low-level Shopify API client using REST API."""
    
    def __init__(self):
        self.api_token = get_env("SHOPIFY_API_TOKEN")
        self.shop_domain = get_env("SHOPIFY_SHOP_DOMAIN")
        
        if not self.api_token or not self.shop_domain:
            raise ValueError("SHOPIFY_API_TOKEN and SHOPIFY_SHOP_DOMAIN must be set")
        
        # Ensure shop domain doesn't include protocol
        self.shop_domain = self.shop_domain.replace("https://", "").replace("http://", "")
        
        self.base_url = f"https://{self.shop_domain}/admin/api/2024-01"
        self.session = requests.Session()
        self.session.headers.update({
            "X-Shopify-Access-Token": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Handle Shopify rate limiting."""
        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", 2.0))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
        
        # Also check the rate limit headers
        rate_limit = response.headers.get("X-Shopify-Shop-Api-Call-Limit")
        if rate_limit:
            current, limit = map(int, rate_limit.split("/"))
            if current >= limit - 5:  # Getting close to limit
                print(f"Approaching rate limit ({current}/{limit}). Slowing down...")
                time.sleep(0.5)
    
    def _parse_link_header(self, link_header: str) -> Dict[str, str]:
        """Parse Link header for pagination."""
        links = {}
        if not link_header:
            return links
        
        for link in link_header.split(","):
            parts = link.strip().split(";")
            if len(parts) == 2:
                url = parts[0].strip("<>")
                rel = parts[1].split("=")[1].strip('"')
                links[rel] = url
        
        return links
    
    def _extract_page_info(self, url: str) -> Optional[str]:
        """Extract page_info parameter from URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get("page_info", [None])[0]
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     json_data: Optional[Dict] = None) -> requests.Response:
        """Make an API request with error handling."""
        url = f"{self.base_url}/{endpoint}"
        
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            json=json_data
        )
        
        # Handle rate limiting
        self._handle_rate_limit(response)
        
        if response.status_code == 429:
            # Retry the request
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data
            )
        
        response.raise_for_status()
        return response
    
    def get_customers(self, updated_at_min: Optional[str] = None, 
                     page_info: Optional[str] = None, limit: int = 250) -> Tuple[List[Dict], Optional[str]]:
        """
        Get customers with cursor-based pagination.
        
        Args:
            updated_at_min: ISO format datetime string (e.g., '2024-01-01T00:00:00Z')
            page_info: Pagination cursor from previous request
            limit: Results per page (max 250)
        
        Returns:
            Tuple of (customers list, next page_info)
        """
        params = {
            "limit": limit
        }
        
        if updated_at_min and not page_info:  # Can't use filters with page_info
            params["updated_at_min"] = updated_at_min
        
        if page_info:
            params["page_info"] = page_info
        
        response = self._make_request("GET", "customers.json", params=params)
        
        # Parse pagination from Link header
        links = self._parse_link_header(response.headers.get("Link", ""))
        next_url = links.get("next")
        next_page_info = self._extract_page_info(next_url) if next_url else None
        
        data = response.json()
        return data.get("customers", []), next_page_info
    
    def get_customer(self, customer_id: int) -> Dict[str, Any]:
        """Get a single customer by ID."""
        response = self._make_request("GET", f"customers/{customer_id}.json")
        return response.json().get("customer", {})
    
    def get_orders(self, updated_at_min: Optional[str] = None, status: str = "any",
                  page_info: Optional[str] = None, limit: int = 250) -> Tuple[List[Dict], Optional[str]]:
        """
        Get orders with cursor-based pagination.
        
        Args:
            updated_at_min: ISO format datetime string
            status: Order status filter ('open', 'closed', 'cancelled', 'any')
            page_info: Pagination cursor
            limit: Results per page (max 250)
        
        Returns:
            Tuple of (orders list, next page_info)
        """
        params = {
            "limit": limit,
            "status": status
        }
        
        if updated_at_min and not page_info:
            params["updated_at_min"] = updated_at_min
        
        if page_info:
            params["page_info"] = page_info
        
        response = self._make_request("GET", "orders.json", params=params)
        
        # Parse pagination
        links = self._parse_link_header(response.headers.get("Link", ""))
        next_url = links.get("next")
        next_page_info = self._extract_page_info(next_url) if next_url else None
        
        data = response.json()
        return data.get("orders", []), next_page_info
    
    def get_order(self, order_id: int) -> Dict[str, Any]:
        """Get a single order by ID."""
        response = self._make_request("GET", f"orders/{order_id}.json")
        return response.json().get("order", {})
    
    def get_products(self, updated_at_min: Optional[str] = None,
                    page_info: Optional[str] = None, limit: int = 250) -> Tuple[List[Dict], Optional[str]]:
        """Get products with pagination."""
        params = {
            "limit": limit
        }
        
        if updated_at_min and not page_info:
            params["updated_at_min"] = updated_at_min
        
        if page_info:
            params["page_info"] = page_info
        
        response = self._make_request("GET", "products.json", params=params)
        
        # Parse pagination
        links = self._parse_link_header(response.headers.get("Link", ""))
        next_url = links.get("next")
        next_page_info = self._extract_page_info(next_url) if next_url else None
        
        data = response.json()
        return data.get("products", []), next_page_info
    
    def get_customer_count(self) -> int:
        """Get total customer count."""
        response = self._make_request("GET", "customers/count.json")
        return response.json().get("count", 0)
    
    def get_order_count(self, status: str = "any") -> int:
        """Get total order count."""
        params = {"status": status}
        response = self._make_request("GET", "orders/count.json", params=params)
        return response.json().get("count", 0)
    
    def test_connection(self) -> bool:
        """Test the API connection."""
        try:
            # Try to get customer count
            count = self.get_customer_count()
            print(f"✅ Shopify connection successful. Found {count} customers.")
            return True
        except Exception as e:
            print(f"❌ Shopify connection failed: {e}")
            return False


if __name__ == "__main__":
    # Test the API connection
    api = ShopifyAPI()
    api.test_connection()