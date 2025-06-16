"""
Specialized tools for fetching data from the Shopify API.
These tools are designed to be atomic and return raw JSON data for the agent to analyze.
"""

from crewai.tools import tool
from typing import Optional, List
import json

from app.services.shopify_data_fetcher import ShopifyDataFetcher
from app.services.merchant_service import merchant_service
from shared.logging_config import get_logger
from app.lib.shopify_customer_lib import (
    find_shopify_customer_by_email,
    search_customers_fuzzy,
    get_customer_order_history
)

logger = get_logger(__name__)


def _get_data_fetcher(shop_domain: str) -> Optional[ShopifyDataFetcher]:
    """Helper to get an authenticated ShopifyDataFetcher."""
    # Ensure shop_domain has .myshopify.com if it's just a subdomain
    if '.' not in shop_domain:
        shop_domain = f"{shop_domain}.myshopify.com"
    
    # This is a synchronous call to the merchant service
    access_token = merchant_service.get_shopify_token(shop_domain)
    if not access_token:
        raise RuntimeError(f"Shopify token not found or DB error for {shop_domain}")
    return ShopifyDataFetcher(shop_domain, access_token)


@tool("get_shopify_store_counts")
def get_shopify_store_counts(shop_domain: str) -> str:
    """
    Get basic store counts (customers, orders).
    This tool should be used to get a high-level snapshot of store activity.
    The input must be the shop domain (e.g., 'example.myshopify.com').
    """
    logger.info(f"[TOOL_CALL] get_shopify_store_counts called with shop_domain={shop_domain}")
    fetcher = _get_data_fetcher(shop_domain)
    if not fetcher:
        raise RuntimeError(f"Shopify token not found or DB error for {shop_domain}")
    try:
        data = fetcher.get_counts()
        result = json.dumps(data)
        logger.info(f"[TOOL_CALL] get_shopify_store_counts returned: {result}")
        return result
    except Exception as e:
        logger.error(f"Error fetching Shopify store counts for {shop_domain}: {e}")
        result = json.dumps({"error": str(e)})
        logger.info(f"[TOOL_CALL] get_shopify_store_counts returned error: {result}")
        return result


@tool("get_shopify_store_overview")
def get_shopify_store_overview(shop_domain: str) -> str:
    """
    Get a high-level overview of the store including recent orders and top products.
    This tool uses a single efficient GraphQL query.
    The input must be the shop domain (e.g., 'example.myshopify.com').
    """
    logger.info(f"[TOOL_CALL] get_shopify_store_overview called with shop_domain={shop_domain}")
    fetcher = _get_data_fetcher(shop_domain)
    if not fetcher:
        raise RuntimeError(f"Shopify token not found or DB error for {shop_domain}")
    try:
        data = fetcher.get_store_overview()
        result = json.dumps(data, default=str)  # Use default=str for datetime objects
        logger.info(f"[TOOL_CALL] get_shopify_store_overview returned: {result[:500]}{'...' if len(result) > 500 else ''}")
        return result
    except Exception as e:
        logger.error(f"Error fetching Shopify store overview for {shop_domain}: {e}")
        result = json.dumps({"error": str(e)})
        logger.info(f"[TOOL_CALL] get_shopify_store_overview returned error: {result}")
        return result


@tool("get_shopify_recent_orders")
def get_shopify_recent_orders(shop_domain: str, limit: int = 10) -> str:
    """
    Get the most recent orders from the store.
    The input must be the shop domain and an optional limit (default 10).
    """
    logger.info(f"[TOOL_CALL] get_shopify_recent_orders called with shop_domain={shop_domain}, limit={limit}")
    fetcher = _get_data_fetcher(shop_domain)
    if not fetcher:
        raise RuntimeError(f"Shopify token not found or DB error for {shop_domain}")
    try:
        data = fetcher.get_recent_orders(limit=limit)
        result = json.dumps(data, default=str)
        logger.info(f"[TOOL_CALL] get_shopify_recent_orders returned: {result[:500]}{'...' if len(result) > 500 else ''}")
        return result
    except Exception as e:
        logger.error(f"Error fetching recent Shopify orders for {shop_domain}: {e}")
        result = json.dumps({"error": str(e)})
        logger.info(f"[TOOL_CALL] get_shopify_recent_orders returned error: {result}")
        return result


@tool("get_shopify_orders_last_week")
def get_shopify_orders_last_week(shop_domain: str) -> str:
    """
    Get all orders updated in the last 7 days.
    Useful for weekly summaries and trend analysis.
    The input must be the shop domain (e.g., 'example.myshopify.com').
    """
    logger.info(f"[TOOL_CALL] get_shopify_orders_last_week called with shop_domain={shop_domain}")
    fetcher = _get_data_fetcher(shop_domain)
    if not fetcher:
        raise RuntimeError(f"Shopify token not found or DB error for {shop_domain}")
    try:
        data = fetcher.get_orders_last_week()
        result = json.dumps(data, default=str)
        logger.info(f"[TOOL_CALL] get_shopify_orders_last_week returned: {result[:500]}{'...' if len(result) > 500 else ''}")
        return result
    except Exception as e:
        logger.error(f"Error fetching last week's Shopify orders for {shop_domain}: {e}")
        result = json.dumps({"error": str(e)})
        logger.info(f"[TOOL_CALL] get_shopify_orders_last_week returned error: {result}")
        return result


@tool("lookup_shopify_customer_by_email")
def lookup_shopify_customer_by_email(email: str) -> str:
    """
    Look up a Shopify customer by their email address.
    
    This tool searches for customers using their email with intelligent fallback:
    - First tries exact email match  
    - Falls back to partial email search if no exact match
    
    Args:
        email: Customer email address to search for
        
    Returns:
        JSON formatted customer data or not found message
    """
    logger.info(f"[TOOL_CALL] lookup_shopify_customer_by_email called with email={email}")
    
    try:
        result = find_shopify_customer_by_email(email=email)
        
        result_json = json.dumps(result, indent=2, default=str)
        logger.info(f"[TOOL_CALL] lookup_shopify_customer_by_email returned: found={result.get('found')}")
        return result_json
        
    except Exception as e:
        logger.error(f"Error looking up customer by email: {e}")
        result = json.dumps({"error": str(e), "found": False})
        return result


@tool("search_shopify_customers")
def search_shopify_customers(search_term: str, search_fields: Optional[str] = None) -> str:
    """
    Search for Shopify customers using fuzzy matching across multiple fields.
    
    Args:
        search_term: Term to search for (name, phone, email part, etc.)
        search_fields: Comma-separated fields to search in. Options: email,first_name,last_name,phone
                      Default: searches all fields
        
    Returns:
        JSON formatted list of matching customers
    """
    logger.info(f"[TOOL_CALL] search_shopify_customers called with term={search_term}, fields={search_fields}")
    
    try:
        # Parse search fields if provided
        fields_list = None
        if search_fields:
            fields_list = [f.strip() for f in search_fields.split(',')]
        
        result = search_customers_fuzzy(
            search_term=search_term,
            search_fields=fields_list
        )
        
        result_json = json.dumps(result, indent=2, default=str)
        logger.info(f"[TOOL_CALL] search_shopify_customers returned: count={result.get('total_count')}")
        return result_json
        
    except Exception as e:
        logger.error(f"Error searching customers: {e}")
        result = json.dumps({"error": str(e), "found": False, "customers": []})
        return result


@tool("get_shopify_customer_orders")  
def get_shopify_customer_orders(customer_id: str, limit: Optional[int] = 10) -> str:
    """
    Get order history for a specific Shopify customer.
    
    Args:
        customer_id: Shopify customer ID (numeric or GID format)
        limit: Maximum number of orders to return (default: 10, max: 50)
        
    Returns:
        JSON formatted order history with customer details
    """
    logger.info(f"[TOOL_CALL] get_shopify_customer_orders called with customer_id={customer_id}, limit={limit}")
    
    try:
        result = get_customer_order_history(
            customer_id=customer_id,
            limit=limit or 10
        )
        
        result_json = json.dumps(result, indent=2, default=str)
        logger.info(f"[TOOL_CALL] get_shopify_customer_orders returned: orders={result.get('orders_returned')}")
        return result_json
        
    except Exception as e:
        logger.error(f"Error fetching customer orders: {e}")
        result = json.dumps({"error": str(e), "orders": [], "orders_returned": 0})
        return result


def create_shopify_tools() -> List[tool]:
    """Returns a list of all Shopify tools."""
    return [
        get_shopify_store_counts,
        get_shopify_store_overview,
        get_shopify_recent_orders,
        get_shopify_orders_last_week,
        lookup_shopify_customer_by_email,
        search_shopify_customers,
        get_shopify_customer_orders,
    ]
