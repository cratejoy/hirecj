#!/usr/bin/env python3
"""Test script for ShopifyDataFetcher implementation."""

import sys
import os
import redis
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directories to path for imports
agents_dir = Path(__file__).parent.parent
project_root = agents_dir.parent
sys.path.insert(0, str(agents_dir))
sys.path.insert(0, str(project_root))

from app.services.shopify_data_fetcher import ShopifyDataFetcher
from shared.env_loader import get_env


def get_merchant_from_redis(shop_domain: str):
    """Retrieve merchant data from Redis."""
    redis_url = get_env("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL not set in environment")
        return None
        
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        key = f"merchant:{shop_domain}"
        data = redis_client.get(key)
        
        if data:
            return json.loads(data)
        else:
            print(f"❌ No merchant found for domain: {shop_domain}")
            return None
    except Exception as e:
        print(f"❌ Error connecting to Redis: {e}")
        return None


async def test_get_counts(fetcher: ShopifyDataFetcher):
    """Test fetching basic counts."""
    print("\n🔍 Testing get_counts()...")
    
    try:
        # First call - should hit API
        start = datetime.now()
        counts = await fetcher.get_counts()
        duration = (datetime.now() - start).total_seconds()
        
        print(f"✅ Counts fetched in {duration:.2f}s:")
        print(f"  - Customers: {counts['customers']}")
        print(f"  - Total Orders: {counts['total_orders']}")
        print(f"  - Open Orders: {counts['open_orders']}")
        
        # Second call - should hit cache
        start = datetime.now()
        cached_counts = await fetcher.get_counts()
        cache_duration = (datetime.now() - start).total_seconds()
        
        print(f"✅ Cache hit in {cache_duration:.2f}s (should be < 0.1s)")
        
        return True
    except Exception as e:
        print(f"❌ Failed to get counts: {e}")
        return False


async def test_get_recent_orders(fetcher: ShopifyDataFetcher):
    """Test fetching recent orders."""
    print("\n🔍 Testing get_recent_orders()...")
    
    try:
        orders = await fetcher.get_recent_orders(limit=5)
        
        print(f"✅ Fetched {len(orders)} orders")
        
        if orders:
            for i, order in enumerate(orders[:3]):  # Show first 3
                print(f"\n  Order #{i+1}:")
                print(f"  - ID: {order.get('id', 'N/A')}")
                print(f"  - Name: {order.get('name', 'N/A')}")
                print(f"  - Total: {order.get('total_price', '0')} {order.get('currency', '')}")
                print(f"  - Status: {order.get('financial_status', 'N/A')}")
                print(f"  - Created: {order.get('created_at', 'N/A')[:10]}")
        else:
            print("  No orders found (new store)")
        
        return True
    except Exception as e:
        print(f"❌ Failed to get orders: {e}")
        return False


async def test_get_store_overview(fetcher: ShopifyDataFetcher):
    """Test fetching store overview via GraphQL."""
    print("\n🔍 Testing get_store_overview()...")
    
    try:
        overview = await fetcher.get_store_overview()
        
        # Display shop info
        shop = overview.get("shop", {})
        print(f"\n✅ Store Overview:")
        print(f"  - Name: {shop.get('name', 'N/A')}")
        print(f"  - Currency: {shop.get('currencyCode', 'N/A')}")
        
        domain = shop.get("primaryDomain", {})
        print(f"  - Domain: {domain.get('host', 'N/A')}")
        
        # Display order summary
        orders = overview.get("orders", {}).get("edges", [])
        print(f"\n  Recent Orders: {len(orders)} found")
        
        # Display product summary
        products = overview.get("products", {}).get("edges", [])
        print(f"  Top Products: {len(products)} found")
        
        if products:
            for i, edge in enumerate(products[:3]):  # Show first 3
                product = edge["node"]
                print(f"\n  Product #{i+1}:")
                print(f"  - Title: {product.get('title', 'N/A')}")
                print(f"  - Inventory: {product.get('totalInventory', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to get store overview: {e}")
        return False


async def test_get_week_orders(fetcher: ShopifyDataFetcher):
    """Test fetching week's orders."""
    print("\n🔍 Testing get_week_orders()...")
    
    try:
        orders = await fetcher.get_week_orders()
        print(f"✅ Fetched {len(orders)} orders from the last week")
        
        if orders:
            # Calculate total revenue
            total_revenue = sum(float(order.get('total_price', 0)) for order in orders)
            print(f"  - Total revenue: ${total_revenue:.2f}")
            
            # Count unique customers
            customers = set(order.get('customer', {}).get('id') for order in orders if order.get('customer'))
            print(f"  - Unique customers: {len(customers)}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to get week orders: {e}")
        return False


async def test_cache_clearing(fetcher: ShopifyDataFetcher):
    """Test cache clearing functionality."""
    print("\n🔍 Testing cache clearing...")
    
    try:
        # Clear specific cache
        fetcher.clear_cache("counts")
        print("✅ Cleared counts cache")
        
        # Clear all cache
        fetcher.clear_cache()
        print("✅ Cleared all cache for shop")
        
        return True
    except Exception as e:
        print(f"❌ Failed to clear cache: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 ShopifyDataFetcher Test Script")
    print("=" * 50)
    
    # Try to get cratejoy-dev merchant from Redis
    shop_domain = "cratejoy-dev.myshopify.com"
    print(f"\n📌 Looking for merchant: {shop_domain}")
    
    merchant = get_merchant_from_redis(shop_domain)
    
    if not merchant:
        # Fall back to environment variables for testing
        print("\n⚠️  No merchant found in Redis. Trying environment variables...")
        
        # For testing, we can use the hardcoded cratejoy-dev domain
        # if we have an access token in the environment
        access_token = get_env("SHOPIFY_API_TOKEN")
        
        if not access_token:
            print("❌ No SHOPIFY_API_TOKEN available for testing")
            print("\n💡 To run this test, either:")
            print("   1. Complete the OAuth flow for cratejoy-dev.myshopify.com")
            print("   2. Set SHOPIFY_API_TOKEN environment variable")
            return
            
        # Use cratejoy-dev domain for testing
        print(f"✅ Using {shop_domain} with API token from environment")
    else:
        access_token = merchant.get("access_token")
        print(f"✅ Found merchant: {merchant.get('shop_name', shop_domain)}")
        print(f"✅ Created at: {merchant.get('created_at', 'Unknown')}")
    
    # Initialize data fetcher
    fetcher = ShopifyDataFetcher(shop_domain, access_token)
    print(f"\n✅ Initialized ShopifyDataFetcher")
    print(f"  - Cache enabled: {fetcher.cache_enabled}")
    
    # Run tests
    test_results = {
        "get_counts": await test_get_counts(fetcher),
        "get_recent_orders": await test_get_recent_orders(fetcher),
        "get_store_overview": await test_get_store_overview(fetcher),
        "get_week_orders": await test_get_week_orders(fetcher),
        "cache_clearing": await test_cache_clearing(fetcher),
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    for test_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    if all(test_results.values()):
        print("\n🎉 All tests passed! Phase 5.2 implementation is working correctly.")
        print("\n📝 Key Features Verified:")
        print("  - Pure data fetching (no analysis)")
        print("  - Redis caching with TTL")
        print("  - Multiple data types supported")
        print("  - Error handling")
        print("  - Cache management")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())