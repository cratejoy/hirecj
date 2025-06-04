"""Freshdesk API utilities for raw API calls."""

import os
import time
from typing import Dict, Any, Optional, List, Tuple
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()


class FreshdeskAPI:
    """Low-level Freshdesk API client."""
    
    def __init__(self):
        self.api_key = os.getenv("FRESHDESK_API_KEY")
        self.domain = os.getenv("FRESHDESK_DOMAIN")
        
        if not self.api_key or not self.domain:
            raise ValueError("FRESHDESK_API_KEY and FRESHDESK_DOMAIN must be set")
        
        self.base_url = f"https://{self.domain}.freshdesk.com/api/v2"
        self.session = requests.Session()
        self.session.auth = (self.api_key, "X")  # Freshdesk uses API key as username
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Handle rate limiting with exponential backoff."""
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
    
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
        if response.status_code == 429:
            self._handle_rate_limit(response)
            # Retry the request
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data
            )
        
        response.raise_for_status()
        return response
    
    def get_tickets(self, updated_since: Optional[str] = None, page: int = 1,
                   per_page: int = 100, include: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
        """
        Get tickets with pagination.
        
        Args:
            updated_since: ISO format datetime string (e.g., '2024-01-01T00:00:00Z')
            page: Page number (starts at 1)
            per_page: Results per page (max 100)
            include: Comma-separated list of associated objects to include
        
        Returns:
            Tuple of (tickets list, next page URL)
        """
        params = {
            "page": page,
            "per_page": per_page,
            "order_by": "updated_at",  # Sort by updated_at
            "order_type": "desc"       # Most recent first
        }
        
        if updated_since:
            params["updated_since"] = updated_since
        
        if include:
            params["include"] = include
        
        response = self._make_request("GET", "tickets", params=params)
        
        # Parse pagination from Link header
        links = self._parse_link_header(response.headers.get("Link", ""))
        next_url = links.get("next")
        
        
        return response.json(), next_url
    
    def get_ticket(self, ticket_id: int, include: Optional[str] = None) -> Dict[str, Any]:
        """Get a single ticket by ID."""
        params = {}
        if include:
            params["include"] = include
        
        response = self._make_request("GET", f"tickets/{ticket_id}", params=params)
        return response.json()
    
    def get_contacts(self, updated_since: Optional[str] = None, page: int = 1,
                    per_page: int = 100) -> Tuple[List[Dict], Optional[str]]:
        """
        Get contacts with pagination.
        
        Args:
            updated_since: ISO format datetime string
            page: Page number (starts at 1)
            per_page: Results per page (max 100)
        
        Returns:
            Tuple of (contacts list, next page URL)
        """
        params = {
            "page": page,
            "per_page": per_page
        }
        
        if updated_since:
            params["updated_since"] = updated_since
        
        response = self._make_request("GET", "contacts", params=params)
        
        # Parse pagination
        links = self._parse_link_header(response.headers.get("Link", ""))
        next_url = links.get("next")
        
        return response.json(), next_url
    
    def get_contact(self, contact_id: int) -> Dict[str, Any]:
        """Get a single contact by ID."""
        response = self._make_request("GET", f"contacts/{contact_id}")
        return response.json()
    
    def get_conversations(self, ticket_id: int, page: int = 1, 
                         per_page: int = 100) -> Tuple[List[Dict], Optional[str]]:
        """Get conversations (replies) for a ticket."""
        params = {
            "page": page,
            "per_page": per_page
        }
        
        response = self._make_request("GET", f"tickets/{ticket_id}/conversations", params=params)
        
        # Parse pagination
        links = self._parse_link_header(response.headers.get("Link", ""))
        next_url = links.get("next")
        
        return response.json(), next_url
    
    def get_companies(self, page: int = 1, per_page: int = 100) -> Tuple[List[Dict], Optional[str]]:
        """Get companies with pagination."""
        params = {
            "page": page,
            "per_page": per_page
        }
        
        response = self._make_request("GET", "companies", params=params)
        
        # Parse pagination
        links = self._parse_link_header(response.headers.get("Link", ""))
        next_url = links.get("next")
        
        return response.json(), next_url
    
    def get_satisfaction_ratings(self, created_since: Optional[str] = None, 
                               page: int = 1, per_page: int = 100) -> Tuple[List[Dict], Optional[str]]:
        """
        Get satisfaction ratings with pagination.
        
        Args:
            created_since: ISO format datetime string (e.g., '2024-01-01T00:00:00Z')
            page: Page number (starts at 1)
            per_page: Results per page (max 100)
        
        Returns:
            Tuple of (ratings list, next page URL)
        """
        params = {
            "page": page,
            "per_page": per_page
            # Note: Freshdesk satisfaction ratings API doesn't support ordering
        }
        
        if created_since:
            params["created_since"] = created_since
        
        response = self._make_request("GET", "surveys/satisfaction_ratings", params=params)
        
        # Parse pagination
        links = self._parse_link_header(response.headers.get("Link", ""))
        next_url = links.get("next")
        
        return response.json(), next_url
    
    def test_connection(self) -> bool:
        """Test the API connection."""
        try:
            # Try to get first page of tickets
            tickets, _ = self.get_tickets(per_page=1)
            print(f"✅ Freshdesk connection successful. Found tickets.")
            return True
        except Exception as e:
            print(f"❌ Freshdesk connection failed: {e}")
            return False


if __name__ == "__main__":
    # Test the API connection
    api = FreshdeskAPI()
    api.test_connection()