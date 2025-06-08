#!/usr/bin/env python3
"""Test script for Shopify GraphQL API implementation."""

import sys
import os
import redis
import json
from pathlib import Path

# Add parent directories to path for imports
agents_dir = Path(__file__).parent.parent
project_root = agents_dir.parent
sys.path.insert(0, str(agents_dir))
sys.path.insert(0, str(project_root))

from app.utils.shopify_util import ShopifyAPI, ShopifyGraphQL
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


def test_rest_api(shop_domain: str, access_token: str):
    """Test REST API functionality."""
    print("\n🔍 Testing REST API...")
    
    try:
        api = ShopifyAPI(shop_domain=shop_domain, access_token=access_token)
        
        # Test customer count
        customer_count = api.get_customer_count()
        print(f"✅ Customer count: {customer_count}")
        
        # Test order counts
        total_orders = api.get_order_count(status="any")
        active_orders = api.get_order_count(status="open")
        
        print(f"✅ Total orders: {total_orders}")
        print(f"✅ Active orders: {active_orders}")
        
        return True
    except Exception as e:
        print(f"❌ REST API test failed: {e}")
        return False


def test_graphql_api(shop_domain: str, access_token: str):
    """Test GraphQL API functionality."""
    print("\n🔍 Testing GraphQL API...")
    
    try:
        graphql = ShopifyGraphQL(shop_domain=shop_domain, access_token=access_token)
        
        # Test basic query
        print("📊 Executing store pulse query...")
        data = graphql.get_store_pulse()
        
        # Display shop info
        shop = data.get("shop", {})
        print(f"\n✅ Shop Name: {shop.get('name', 'N/A')}")
        print(f"✅ Currency: {shop.get('currencyCode', 'N/A')}")
        
        domain = shop.get("primaryDomain", {})
        print(f"✅ Domain: {domain.get('host', 'N/A')}")
        
        # Display recent orders
        orders = data.get("orders", {}).get("edges", [])
        print(f"\n📦 Recent Orders ({len(orders)} found):")
        
        for i, edge in enumerate(orders[:3]):  # Show first 3
            order = edge["node"]
            total = order.get("totalPriceSet", {}).get("shopMoney", {})
            customer = order.get("customer", {})
            
            print(f"\n  Order #{i+1}:")
            print(f"  - Name: {order.get('name', 'N/A')}")
            print(f"  - Total: {total.get('amount', '0')} {total.get('currencyCode', '')}")
            print(f"  - Customer: {customer.get('displayName', 'Guest')}")
            print(f"  - Status: {order.get('displayFinancialStatus', 'N/A')}")
        
        # Display top products
        products = data.get("products", {}).get("edges", [])
        print(f"\n🏆 Top Products by Inventory ({len(products)} found):")
        
        for i, edge in enumerate(products[:3]):  # Show first 3
            product = edge["node"]
            print(f"\n  Product #{i+1}:")
            print(f"  - Title: {product.get('title', 'N/A')}")
            print(f"  - Inventory: {product.get('totalInventory', 0)}")
            
        return True
    except Exception as e:
        print(f"❌ GraphQL API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("🚀 Shopify GraphQL API Test Script")
    print("=" * 50)
    
    # Try to get cratejoy-dev merchant from Redis
    shop_domain = "cratejoy-dev.myshopify.com"
    print(f"\n📌 Looking for merchant: {shop_domain}")
    
    merchant = get_merchant_from_redis(shop_domain)
    
    if not merchant:
        # Fall back to environment variables for testing
        print("\n⚠️  No merchant found in Redis. Trying environment variables...")
        shop_domain = get_env("SHOPIFY_SHOP_DOMAIN")
        access_token = get_env("SHOPIFY_API_TOKEN")
        
        if not shop_domain or not access_token:
            print("❌ No credentials available for testing")
            return
    else:
        access_token = merchant.get("access_token")
        print(f"✅ Found merchant: {merchant.get('shop_name', shop_domain)}")
        print(f"✅ Created at: {merchant.get('created_at', 'Unknown')}")
    
    # Run tests
    rest_success = test_rest_api(shop_domain, access_token)
    graphql_success = test_graphql_api(shop_domain, access_token)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"  REST API: {'✅ PASSED' if rest_success else '❌ FAILED'}")
    print(f"  GraphQL API: {'✅ PASSED' if graphql_success else '❌ FAILED'}")
    
    if rest_success and graphql_success:
        print("\n🎉 All tests passed! Phase 5.1 implementation is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    main()