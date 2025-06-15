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


def create_shopify_tools() -> List[tool]:
    """Returns a list of all Shopify tools."""
    return [
        get_shopify_store_counts,
        get_shopify_store_overview,
        get_shopify_recent_orders,
        get_shopify_orders_last_week,
    ]
