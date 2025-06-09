# Phase 5: Quick Value Demo - Implementation Guide

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Every decision should make the code simpler, not more complex
2. **No Cruft**: Remove all redundant code, validation, and unnecessary complexity
3. **Break It & Fix It Right**: No backwards compatibility shims - make breaking changes and migrate properly
4. **Long-term Elegance**: Choose performant, compiler-enforced solutions that prevent subtle bugs
5. **Backend-Driven**: Let the backend handle complexity, frontend should be a thin client
6. **Single Source of Truth**: One pattern, one way to do things, no alternatives
7. **No Over-Engineering**: Design for current needs only - no hypothetical features
8. **Thoughtful Logging & Instrumentation**: Appropriate visibility into system behavior

## Overview

Phase 5 delivers immediate value after Shopify OAuth by showing merchants quick insights about their store. This is implemented through our workflow-driven architecture using system events and tools, maintaining consistency with our YAML-configured approach.

## Core Architecture: Simplified Data Fetching

### Key Architectural Decisions (Phase 5.2 Implementation)

During implementation, we simplified away the complex three-tier system in favor of direct data methods:

1. **Pure Data Fetching**: ShopifyDataFetcher provides simple methods like `get_counts()`, `get_recent_orders()`, etc.
2. **No Analysis in Service**: All intelligence and progressive disclosure logic moved to the CJ agent
3. **Redis Caching**: Simple caching with TTL for expensive operations
4. **Token Storage**: Access tokens are stored in Redis by the auth service (NOT in PostgreSQL)

### Data Methods Available

- `get_counts()`: Basic metrics (customers, orders)
- `get_recent_orders()`: Recent order data
- `get_store_overview()`: Store info via GraphQL
- `get_week_orders()`: Orders from the past week

## Implementation Architecture

### Key Changes from Original Design

1. **OAuth Completion via System Events**: Instead of hardcoded OAuth handling, we use system events in the shopify_onboarding workflow YAML
2. **Shopify Insights Tool**: Replace CJ agent method with a dedicated tool that CJ can call
3. **Workflow-Driven Progressive Disclosure**: Insights behavior configured in YAML, not code
4. **Consistent Pattern**: Follows our established workflow and tool patterns
5. **Latest Shopify API**: Using GraphQL Admin API version 2025-01 with proper authentication headers

## Implementation Checklist

### Phase Order (Linear Dependencies)

**⚠️ Important**: Each phase depends on the previous one. Complete them in order.

- [x] **Phase 5.1: API Infrastructure** ✅ COMPLETED
  - [x] Extend Shopify API client with GraphQL support (Step 1)
  - [x] Implement authentication and error handling
  - [x] Test with real Shopify store (cratejoy-dev)

- [x] **Phase 5.2: Data Service Layer** ✅ COMPLETED
  - [x] Create ShopifyDataFetcher service (simplified from QuickShopifyInsights)
  - [x] Implement direct data fetching methods (no tier complexity)
  - [x] Add Redis caching with TTL
  - [x] Implement error handling and graceful degradation

- [ ] **Phase 5.3.5: PostgreSQL-Only Token Storage** ⭐ NEW - Clean Architecture
  - [ ] Create store_test_shopify_token.py script
  - [ ] Script stores tokens in PostgreSQL merchant_integrations table
  - [ ] Add PostgreSQL-only MerchantService (no Redis at all)
  - [ ] Test token storage and retrieval works correctly

- [ ] **Phase 5.3: Tool Creation** (Blocked until 5.3.5)
  - [ ] Create shopify_data tool in universe_tools.py (Step 3)
  - [ ] Implement progressive disclosure logic in agent
  - [ ] Use PostgreSQL-only token retrieval from Phase 5.3.5
  - [ ] Return structured JSON for CJ to process

- [ ] **Phase 5.4: Auth Service Migration** (Simplified)
  - [ ] Update auth service to store tokens in PostgreSQL during OAuth
  - [ ] One-time migration script for critical production tokens
  - [ ] Remove ALL Redis token code from auth service
  - [ ] Update all documentation
  - [ ] Note: Existing Redis tokens will require re-authentication

- [ ] **Phase 5.5: Workflow Integration**
  - [ ] Update shopify_onboarding.yaml with system events (Step 4)
  - [ ] Configure OAuth completion handler
  - [ ] Add CJ prompts for progressive disclosure behavior
  - [ ] Define transition to ad_hoc_support

- [ ] **Phase 5.6: Agent Registration**
  - [ ] Register shopify_data tool with CJ agent (Step 5)
  - [ ] Ensure tool is available in CJ's tool registry
  - [ ] Verify context passing works correctly

- [ ] **Phase 5.7: Testing & Validation**
  - [ ] Unit tests for each component
  - [ ] Integration test for OAuth → insights flow
  - [ ] Manual testing with different store types
  - [ ] Performance validation (< 500ms first insight)

## Implementation Steps

### Step 1: Extend Shopify API Client with GraphQL

**File:** `agents/app/utils/shopify_util.py`

Add GraphQL support to existing REST client:

```python
import json
from typing import Dict, Any

class ShopifyGraphQL:
    """Minimal GraphQL client for quick insights."""
    
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain.replace("https://", "").replace("http://", "")
        self.access_token = access_token
        # Using the latest stable API version (2025-01)
        self.endpoint = f"https://{self.shop_domain}/admin/api/2025-01/graphql.json"
        
        self.session = requests.Session()
        self.session.headers.update({
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"  # Required for 2025-01
        })
    
    def execute(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        response = self.session.post(self.endpoint, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if "errors" in result:
            raise Exception(f"GraphQL errors: {result['errors']}")
            
        return result.get("data", {})
    
    def get_store_pulse(self) -> Dict[str, Any]:
        """Get quick store overview in one query."""
        query = """
        query StoreOverview {
          shop {
            name
            currencyCode
            primaryDomain {
              url
              host
            }
          }
          
          orders(first: 10, sortKey: CREATED_AT, reverse: true) {
            edges {
              node {
                id
                name
                createdAt
                displayFinancialStatus
                displayFulfillmentStatus
                totalPriceSet {
                  shopMoney {
                    amount
                    currencyCode
                  }
                }
                lineItems(first: 5) {
                  edges {
                    node {
                      title
                      quantity
                      variant {
                        id
                        price
                      }
                    }
                  }
                }
                customer {
                  id
                  displayName
                  ordersCount
                }
              }
            }
          }
          
          products(first: 5, sortKey: INVENTORY_TOTAL, reverse: true) {
            edges {
              node {
                id
                title
                description
                totalInventory
                priceRangeV2 {
                  minVariantPrice {
                    amount
                    currencyCode
                  }
                  maxVariantPrice {
                    amount
                    currencyCode
                  }
                }
                featuredImage {
                  url
                }
              }
            }
          }
        }
        """
        
        return self.execute(query)
```

### Step 2: Create Quick Insights Service

**File:** `agents/app/services/quick_insights.py`

```python
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import redis
import json
from functools import lru_cache

from app.utils.shopify_util import ShopifyAPI, ShopifyGraphQL
from app.config import get_settings

settings = get_settings()


class QuickShopifyInsights:
    """Progressive data fetching for quick store insights."""
    
    def __init__(self, merchant_id: str, shop_domain: str, access_token: str):
        self.merchant_id = merchant_id
        self.shop_domain = shop_domain
        self.access_token = access_token
        
        # Initialize API clients
        self.rest_api = ShopifyAPI()  # Uses env vars for now
        self.graphql = ShopifyGraphQL(shop_domain, access_token)
        
        # Redis for caching
        self.redis = redis.from_url(settings.redis_url)
        self.cache_ttl = 900  # 15 minutes
    
    def _cache_key(self, tier: str) -> str:
        """Generate cache key for tier data."""
        return f"quick_insights:{self.merchant_id}:{tier}"
    
    def _get_cached(self, tier: str) -> Optional[Dict]:
        """Get cached data if available."""
        key = self._cache_key(tier)
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    def _set_cached(self, tier: str, data: Dict) -> None:
        """Cache data with TTL."""
        key = self._cache_key(tier)
        self.redis.setex(key, self.cache_ttl, json.dumps(data))
    
    async def tier_1_snapshot(self) -> Dict[str, Any]:
        """Instant metrics using count endpoints."""
        # Check cache first
        cached = self._get_cached("tier_1")
        if cached:
            return cached
        
        try:
            # Using REST API 2025-01 count endpoints
            data = {
                "customers": self.rest_api.get_customer_count(),
                "total_orders": self.rest_api.get_order_count(status="any"),
                "active_orders": self.rest_api.get_order_count(status="open"),
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache the result
            self._set_cached("tier_1", data)
            return data
            
        except Exception as e:
            # Return graceful fallback
            return {
                "customers": "some",
                "total_orders": "several",
                "active_orders": 0,
                "error": str(e)
            }
    
    async def tier_2_insights(self) -> Dict[str, Any]:
        """Quick insights via GraphQL."""
        # Check cache
        cached = self._get_cached("tier_2")
        if cached:
            return cached
        
        try:
            # Get store pulse data
            pulse = self.graphql.get_store_pulse()
            
            # Process the data
            insights = {
                "shop_name": pulse["shop"]["name"],
                "currency": pulse["shop"]["currencyCode"],
                "recent_orders": self._process_orders(pulse["orders"]),
                "top_products": self._process_products(pulse["products"]),
                "timestamp": datetime.now().isoformat()
            }
            
            # Calculate derived metrics
            insights["recent_revenue"] = sum(
                float(order["total"]) 
                for order in insights["recent_orders"]
            )
            
            insights["order_velocity"] = self._calculate_velocity(
                insights["recent_orders"]
            )
            
            # Cache result
            self._set_cached("tier_2", insights)
            return insights
            
        except Exception as e:
            return {
                "error": str(e),
                "recent_revenue": 0,
                "order_velocity": 0,
                "recent_orders": [],
                "top_products": []
            }
    
    def _process_orders(self, orders_data: Dict) -> List[Dict]:
        """Extract key order information."""
        orders = []
        for edge in orders_data.get("edges", []):
            node = edge["node"]
            orders.append({
                "id": node["id"],
                "name": node["name"],
                "created_at": node["createdAt"],
                "total": node["totalPriceSet"]["shopMoney"]["amount"],
                "status": node["displayFinancialStatus"],
                "items": [
                    item["node"]["title"] 
                    for item in node["lineItems"]["edges"][:3]
                ],
                "customer_name": node.get("customer", {}).get("displayName", "Guest"),
                "is_repeat": (node.get("customer", {}).get("ordersCount", 0) > 1)
            })
        return orders
    
    def _process_products(self, products_data: Dict) -> List[Dict]:
        """Extract key product information."""
        products = []
        for edge in products_data.get("edges", []):
            node = edge["node"]
            products.append({
                "id": node["id"],
                "title": node["title"],
                "inventory": node["totalInventory"],
                "min_price": node["priceRangeV2"]["minVariantPrice"]["amount"],
                "max_price": node["priceRangeV2"]["maxVariantPrice"]["amount"],
                "image": node.get("featuredImage", {}).get("url")
            })
        return products
    
    def _calculate_velocity(self, orders: List[Dict]) -> float:
        """Calculate orders per day from recent orders."""
        if not orders or len(orders) < 2:
            return 0.0
        
        # Parse dates
        dates = [
            datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
            for order in orders
        ]
        
        # Calculate span
        span = (dates[0] - dates[-1]).days or 1
        
        return round(len(orders) / span, 1)
    
    async def tier_3_analysis(self) -> Dict[str, Any]:
        """Deeper analysis with targeted REST queries."""
        # Check cache
        cached = self._get_cached("tier_3")
        if cached:
            return cached
        
        try:
            # Get last week's orders with strict limit
            # Note: Only last 60 days of orders are accessible by default
            since = (datetime.now() - timedelta(days=7)).isoformat()
            recent_orders, _ = self.rest_api.get_orders(
                updated_at_min=since,
                limit=50
            )
            
            # Analyze patterns
            analysis = {
                "week_order_count": len(recent_orders),
                "customer_segments": self._segment_customers(recent_orders),
                "revenue_pattern": self._identify_pattern(recent_orders),
                "popular_items": self._find_popular_items(recent_orders),
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache result
            self._set_cached("tier_3", analysis)
            return analysis
            
        except Exception as e:
            return {
                "error": str(e),
                "week_order_count": 0,
                "customer_segments": {},
                "revenue_pattern": "unknown"
            }
    
    def _segment_customers(self, orders: List[Dict]) -> Dict[str, int]:
        """Quick customer segmentation."""
        segments = {"new": 0, "returning": 0, "vip": 0}
        
        for order in orders:
            customer = order.get("customer", {})
            if not customer:
                segments["new"] += 1
            else:
                order_count = customer.get("orders_count", 0)
                if order_count == 1:
                    segments["new"] += 1
                elif order_count < 5:
                    segments["returning"] += 1
                else:
                    segments["vip"] += 1
        
        return segments
    
    def _identify_pattern(self, orders: List[Dict]) -> str:
        """Identify basic revenue patterns."""
        if not orders:
            return "no_data"
        
        # Group by day
        daily_revenue = {}
        for order in orders:
            date = order["created_at"][:10]  # YYYY-MM-DD
            revenue = float(order.get("total_price", 0))
            daily_revenue[date] = daily_revenue.get(date, 0) + revenue
        
        # Simple pattern detection
        values = list(daily_revenue.values())
        if len(values) < 3:
            return "insufficient_data"
        
        # Check trend
        first_half = sum(values[:len(values)//2])
        second_half = sum(values[len(values)//2:])
        
        if second_half > first_half * 1.2:
            return "growing"
        elif second_half < first_half * 0.8:
            return "declining"
        else:
            return "stable"
    
    def _find_popular_items(self, orders: List[Dict]) -> List[Dict]:
        """Find most ordered items."""
        item_counts = {}
        
        for order in orders:
            for item in order.get("line_items", []):
                title = item.get("title", "Unknown")
                item_counts[title] = item_counts.get(title, 0) + item.get("quantity", 1)
        
        # Sort by count
        popular = sorted(
            item_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return [{"title": title, "count": count} for title, count in popular]


def generate_quick_insights(data: Dict[str, Any]) -> List[str]:
    """Transform data into conversational insights."""
    insights = []
    
    # Tier 1 insights
    if "customers" in data:
        if isinstance(data["customers"], int):
            insights.append(f"You have {data['customers']:,} customers in your store")
        else:
            insights.append(f"You have {data['customers']} customers in your store")
    
    if data.get("active_orders", 0) > 0:
        insights.append(f"You currently have {data['active_orders']} orders to fulfill")
    
    # Tier 2 insights
    if data.get("recent_revenue"):
        insights.append(f"You've made ${data['recent_revenue']:,.2f} in your last 10 orders")
    
    if data.get("order_velocity"):
        insights.append(f"Your store is averaging {data['order_velocity']} orders per day")
    
    if data.get("top_products"):
        top = data["top_products"][0]
        insights.append(f"'{top['title']}' is your best stocked product with {top['inventory']} units")
    
    # Check for repeat customers
    recent_orders = data.get("recent_orders", [])
    repeat_count = sum(1 for order in recent_orders if order.get("is_repeat"))
    if repeat_count > 0:
        insights.append(f"{repeat_count} of your last 10 orders were from repeat customers")
    
    # Tier 3 insights
    if data.get("revenue_pattern") == "growing":
        insights.append("Your revenue has been trending upward this week")
    elif data.get("revenue_pattern") == "stable":
        insights.append("Your revenue has been steady this week")
    
    segments = data.get("customer_segments", {})
    if segments.get("vip", 0) > 0:
        insights.append(f"You have {segments['vip']} VIP customers who've ordered 5+ times")
    
    # Handle edge cases
    if not insights:
        if data.get("error"):
            insights.append("I'm having trouble accessing your store data right now")
        else:
            insights.append("Your store is all set up and ready to go!")
    
    return insights
```

### Step 2.5: PostgreSQL-Only Token Storage (Phase 5.3.5)

This step implements clean PostgreSQL-only token storage. No Redis fallback - we're making a clean break.

**File:** `agents/scripts/store_test_shopify_token.py`

```python
#!/usr/bin/env python3
"""Store test Shopify tokens in PostgreSQL for development."""

import asyncio
import asyncpg
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directories to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.env_loader import get_env

async def store_test_token(shop_domain: str, access_token: str):
    """Store a test token in PostgreSQL merchant_integrations table."""
    
    db_url = get_env("SUPABASE_CONNECTION_STRING")
    if not db_url:
        print("❌ SUPABASE_CONNECTION_STRING not set")
        return
    
    async with asyncpg.create_pool(db_url) as pool:
        async with pool.acquire() as conn:
            # Create/update merchant
            merchant_name = shop_domain.replace('.myshopify.com', '')
            merchant = await conn.fetchrow(
                "INSERT INTO merchants (name) VALUES ($1) "
                "ON CONFLICT (name) DO UPDATE SET updated_at = NOW() "
                "RETURNING id",
                merchant_name
            )
            
            # Store token in merchant_integrations
            await conn.execute("""
                INSERT INTO merchant_integrations 
                (merchant_id, type, api_key, config, is_active)
                VALUES ($1, 'shopify', $2, $3, true)
                ON CONFLICT (merchant_id, type) 
                DO UPDATE SET 
                    api_key = EXCLUDED.api_key,
                    config = EXCLUDED.config,
                    updated_at = NOW()
            """, merchant['id'], access_token, json.dumps({
                'shop_domain': shop_domain,
                'stored_at': datetime.utcnow().isoformat(),
                'source': 'test_script',
                'scopes': 'read_customers,read_orders,read_products'
            }))
            
            print(f"✅ Stored token for {shop_domain} (merchant_id: {merchant['id']})")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python store_test_shopify_token.py <shop_domain> <access_token>")
        print("Example: python store_test_shopify_token.py cratejoy-dev.myshopify.com shpat_xxxxx")
        sys.exit(1)
    
    shop_domain = sys.argv[1]
    access_token = sys.argv[2]
    
    asyncio.run(store_test_token(shop_domain, access_token))
```

**File:** `agents/app/services/merchant_service.py`

Create a clean PostgreSQL-only service:

```python
"""Service for merchant data access - PostgreSQL only, no Redis."""

from typing import Optional
import asyncpg
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class MerchantService:
    """Service for merchant data access - single source of truth."""
    
    def __init__(self):
        self.pool = None
    
    async def initialize(self):
        """Initialize connection pool at startup."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                settings.supabase_connection_string,
                min_size=1,
                max_size=10
            )
            logger.info("MerchantService: PostgreSQL connection pool initialized")
    
    async def close(self):
        """Close connection pool on shutdown."""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def get_shopify_token(self, shop_domain: str) -> Optional[str]:
        """Get Shopify access token from PostgreSQL only."""
        if not self.pool:
            await self.initialize()
        
        merchant_name = shop_domain.replace('.myshopify.com', '')
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT mi.api_key 
                    FROM merchants m
                    JOIN merchant_integrations mi ON m.id = mi.merchant_id
                    WHERE m.name = $1 
                    AND mi.type = 'shopify' 
                    AND mi.is_active = true
                """, merchant_name)
                
                if result:
                    logger.info(f"Got token from PostgreSQL for {shop_domain}")
                    return result['api_key']
                else:
                    logger.warning(f"No token found for {shop_domain}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get token from PostgreSQL: {e}")
            return None


# Singleton instance
merchant_service = MerchantService()
```

### Step 3: Create Shopify Data Tool

**File:** `agents/app/agents/universe_tools.py`

Add a new tool that CJ can call to get Shopify data:

```python
@tool("shopify_data")
async def get_shopify_data(self, data_type: str = "overview") -> str:
    """
    Get Shopify store data. All analysis and insights are generated by the agent.
    
    Args:
        data_type: Type of data to fetch ("counts", "recent_orders", "overview", "week_orders")
    
    Returns:
        JSON string with raw data for agent to analyze
    """
    # Get merchant details from context
    shop_domain = self.context.get("shop_domain")
    
    if not shop_domain:
        return json.dumps({
            "error": "No Shopify store connected",
            "insights": []
        })
    
    # Get access token from Redis (where auth service stores it)
    access_token = await self._get_merchant_token(shop_domain)
    if not access_token:
        return json.dumps({
            "error": "Unable to access store data",
            "insights": []
        })
    
    # Initialize data fetcher
    data_fetcher = ShopifyDataFetcher(shop_domain, access_token)
    
    try:
        # Fetch the requested data type
        if data_type == "counts":
            data = await data_fetcher.get_counts()
        elif data_type == "recent_orders":
            data = await data_fetcher.get_recent_orders()
        elif data_type == "overview":
            data = await data_fetcher.get_store_overview()
        elif data_type == "week_orders":
            data = await data_fetcher.get_week_orders()
        else:
            return json.dumps({
                "error": f"Unknown data type: {data_type}",
                "available_types": ["counts", "recent_orders", "overview", "week_orders"]
            })
        
        return json.dumps({
            "success": True,
            "data_type": data_type,
            "data": data
        })
        
    except Exception as e:
        logger.error(f"Error fetching Shopify data: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "data_type": data_type
        })

async def _get_merchant_token(self, shop_domain: str) -> Optional[str]:
    """Get Shopify access token from PostgreSQL.
    
    Phase 5.3.5: Clean PostgreSQL-only implementation.
    No Redis fallback - single source of truth.
    """
    from app.services.merchant_service import merchant_service
    
    return await merchant_service.get_shopify_token(shop_domain)
```

### Step 4: Update Workflow YAML for OAuth System Event

**File:** `agents/prompts/workflows/shopify_onboarding.yaml`

Add system event handling for OAuth completion:

```yaml
name: shopify_onboarding
description: Guides merchants through Shopify OAuth connection

# Requirements configuration
requirements:
  - shopify_oauth: true

# Behavior configuration
behavior:
  initiator: "cj"
  initial_action:
    type: "process_message"
    message: "Ready to connect your Shopify store"
    sender: "merchant"
    cleanup_trigger: true
  transitions:
    already_authenticated:
      target_workflow: "ad_hoc_support"
      message: "I see you're already connected! Let me help you with your store."

# System events for OAuth handling
system_events:
  oauth_complete:
    condition: "provider == 'shopify' and success == true"
    actions:
      - type: "update_context"
        data:
          shop_domain: "{{shop_domain}}"
          shopify_connected: true
          merchant_id: "{{merchant_id}}"
      - type: "process_message"
        message: "show_shopify_insights"
        sender: "system"
        metadata:
          command: "progressive_disclosure"
          start_tier: "tier1"

# CJ's prompts with data analysis behavior
prompts:
  cj:
    system: |
      You are CJ, a customer support AI assistant helping a merchant connect their Shopify store.
      
      When you receive a system message with "show_shopify_insights", use the shopify_data tool
      to fetch data and generate insights:
      
      1. First call: get_shopify_data(data_type="counts") - Analyze basic metrics
      2. Pause briefly, then mention you're looking at recent activity
      3. Second call: get_shopify_data(data_type="recent_orders") - Analyze order patterns
      4. If relevant, fetch overview data for more context
      5. Generate insights based on the data patterns you observe
      6. Transition naturally to offering support system connection
      
      You analyze the raw data and create insights. The tool just provides data.
      Make your analysis conversational and helpful, not a raw data dump.
```

### Step 4.5: Complete Token Migration (Phase 5.4)

This completes the architectural improvement started in Phase 5.3.5.

#### What Phase 5.3.5 Does
- Creates PostgreSQL-only token storage in agents service
- Clean implementation with no Redis fallback
- Enables testing with proper architecture from the start

#### What Phase 5.4 Completes
- Updates auth service to store all new tokens in PostgreSQL
- Removes ALL Redis token code from auth service
- One-time migration for critical production tokens (optional)
- Clean break: existing users may need to re-authenticate

**File:** `agents/app/migrations/002_add_shopify_token_storage.sql`

```sql
-- merchant_integrations table already exists with perfect schema
-- Just need to start using it for Shopify tokens
-- No migration needed, table already has:
-- - merchant_id (FK to merchants)
-- - type ('shopify')
-- - api_key (for access token)
-- - config (JSONB for shop_domain, scopes, etc.)
```

**File:** `auth/app/services/merchant_storage.py`

Replace Redis storage with PostgreSQL:

```python
import asyncpg
from app.config import settings

class MerchantStorage:
    """Store merchant data in PostgreSQL instead of Redis."""
    
    def __init__(self):
        self.db_url = settings.database_url
    
    async def store_shopify_token(self, shop_domain: str, access_token: str, scopes: str):
        """Store Shopify OAuth token in merchant_integrations table."""
        
        async with asyncpg.create_pool(self.db_url) as pool:
            async with pool.acquire() as conn:
                # Get or create merchant
                merchant_name = shop_domain.replace('.myshopify.com', '')
                merchant = await conn.fetchrow(
                    "INSERT INTO merchants (name) VALUES ($1) "
                    "ON CONFLICT (name) DO UPDATE SET updated_at = NOW() "
                    "RETURNING id",
                    merchant_name
                )
                
                # Upsert integration
                await conn.execute("""
                    INSERT INTO merchant_integrations 
                    (merchant_id, type, api_key, config, is_active)
                    VALUES ($1, 'shopify', $2, $3, true)
                    ON CONFLICT (merchant_id, type) 
                    DO UPDATE SET 
                        api_key = EXCLUDED.api_key,
                        config = EXCLUDED.config,
                        updated_at = NOW()
                """, merchant['id'], access_token, json.dumps({
                    'shop_domain': shop_domain,
                    'scopes': scopes,
                    'installed_at': datetime.utcnow().isoformat()
                }))
```

**File:** `agents/app/services/merchant_service.py`

Create service for token retrieval:

```python
from typing import Optional
import asyncpg
from app.config import settings

class MerchantService:
    """Service for merchant data access."""
    
    async def get_shopify_token(self, shop_domain: str) -> Optional[str]:
        """Get Shopify access token from merchant_integrations."""
        
        merchant_name = shop_domain.replace('.myshopify.com', '')
        
        async with asyncpg.create_pool(settings.database_url) as pool:
            async with pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT mi.api_key 
                    FROM merchants m
                    JOIN merchant_integrations mi ON m.id = mi.merchant_id
                    WHERE m.name = $1 
                    AND mi.type = 'shopify' 
                    AND mi.is_active = true
                """, merchant_name)
                
                return result['api_key'] if result else None

# Singleton instance
merchant_service = MerchantService()
```

**Migration Script:** `scripts/migrate_redis_tokens_to_postgres.py`

```python
#!/usr/bin/env python3
import asyncio
import redis
import json
import asyncpg
from shared.env_loader import get_env

async def migrate_tokens():
    """One-time migration from Redis to PostgreSQL."""
    
    # Connect to Redis
    redis_client = redis.from_url(get_env("REDIS_URL"), decode_responses=True)
    
    # Connect to PostgreSQL
    pool = await asyncpg.create_pool(get_env("DATABASE_URL"))
    
    # Get all merchant tokens from Redis
    merchant_keys = redis_client.keys("merchant:*")
    migrated = 0
    
    async with pool.acquire() as conn:
        for key in merchant_keys:
            try:
                data = json.loads(redis_client.get(key))
                shop_domain = data['shop_domain']
                access_token = data['access_token']
                
                # Create/get merchant
                merchant_name = shop_domain.replace('.myshopify.com', '')
                merchant = await conn.fetchrow(
                    "INSERT INTO merchants (name) VALUES ($1) "
                    "ON CONFLICT (name) DO UPDATE SET updated_at = NOW() "
                    "RETURNING id",
                    merchant_name
                )
                
                # Store integration
                await conn.execute("""
                    INSERT INTO merchant_integrations 
                    (merchant_id, type, api_key, config, is_active)
                    VALUES ($1, 'shopify', $2, $3, true)
                    ON CONFLICT (merchant_id, type) 
                    DO UPDATE SET 
                        api_key = EXCLUDED.api_key,
                        config = EXCLUDED.config,
                        updated_at = NOW()
                """, merchant['id'], access_token, json.dumps({
                    'shop_domain': shop_domain,
                    'migrated_from_redis': True,
                    'migrated_at': datetime.utcnow().isoformat()
                }))
                
                migrated += 1
                print(f"✅ Migrated {shop_domain}")
                
            except Exception as e:
                print(f"❌ Failed to migrate {key}: {e}")
    
    await pool.close()
    print(f"\n🎉 Migration complete: {migrated}/{len(merchant_keys)} merchants migrated")

if __name__ == "__main__":
    asyncio.run(migrate_tokens())
```

### Step 5: Tool Registration

**File:** `agents/app/agents/cj_agent.py`

Ensure the shopify_data tool is available to CJ:

```python
class CJAgent:
    def __init__(self):
        # Existing initialization...
        
        # Register tools
        self.tools = {
            "search_universe_data": universe_tools.search_universe_data,
            "get_customer_info": universe_tools.get_customer_info,
            "calculate_metrics": universe_tools.calculate_metrics,
            "shopify_data": universe_tools.get_shopify_data,  # Add this
        }
```

### Step 6: Error Handling

The tool returns errors in a structured format. CJ should handle these gracefully:

```python
# CJ's behavior when receiving error responses:
# If error contains "rate limit" -> pause and retry
# If error contains "unauthorized" -> suggest reconnecting
# For other errors -> acknowledge and continue conversation

# The ShopifyDataFetcher already handles:
# - Redis caching to minimize API calls
# - Graceful fallbacks for missing data
# - Proper error messages in responses
```
```

## Testing Guide

### 1. Unit Tests

```python
# tests/test_quick_insights.py
import pytest
from unittest.mock import Mock, patch
from app.services.quick_insights import QuickShopifyInsights, generate_quick_insights

def test_tier_1_snapshot():
    """Test instant metrics retrieval."""
    # Mock REST API
    mock_api = Mock()
    mock_api.get_customer_count.return_value = 100
    mock_api.get_order_count.return_value = 50
    
    insights = QuickShopifyInsights("test_merchant", "test.myshopify.com", "token")
    insights.rest_api = mock_api
    
    result = await insights.tier_1_snapshot()
    
    assert result["customers"] == 100
    assert result["total_orders"] == 50

def test_shopify_data_tool():
    """Test the shopify_data tool."""
    # Mock context
    mock_context = {
        "shop_domain": "test.myshopify.com"
    }
    
    # Test tool execution
    result = await get_shopify_data(mock_context, data_type="counts")
    data = json.loads(result)
    
    assert data["success"] is True
    assert len(data["insights"]) <= 2  # Tier 1 returns max 2 insights
```

### 2. Workflow Integration Tests

```yaml
# tests/shopify_data/oauth_complete_flow.yaml
name: test_shopify_oauth_data_flow
description: Test OAuth completion triggers data fetch

steps:
  - action: simulate_oauth_complete
    data:
      provider: shopify
      success: true
      shop_domain: test.myshopify.com
      merchant_id: test_123
  
  - expect: context_update
    values:
      shopify_connected: true
      shop_domain: test.myshopify.com
  
  - expect: cj_tool_call
    tool: shopify_data
    params:
      data_type: counts
  
  - expect: cj_message
    contains: "customers in your store"
  
  - expect: cj_tool_call
    tool: shopify_data
    params:
      data_type: recent_orders
    min_delay: 1.0
  
  - expect: cj_message
    contains: "recent activity"
```

### 2. Integration Tests

Test the full flow with a test Shopify store:

```python
async def test_full_insights_flow():
    """Test complete progressive disclosure."""
    # Use test store credentials
    insights = QuickShopifyInsights(
        "test_merchant",
        "hirecj-test.myshopify.com", 
        TEST_ACCESS_TOKEN
    )
    
    # Test each tier
    tier_1 = await insights.tier_1_snapshot()
    assert tier_1 is not None
    assert "customers" in tier_1
    
    tier_2 = await insights.tier_2_insights()
    assert "recent_orders" in tier_2
    
    tier_3 = await insights.tier_3_analysis()
    assert "customer_segments" in tier_3
```

### 3. Manual Testing Checklist

- [ ] Test OAuth flow triggers system event
- [ ] Verify context updates with shop domain
- [ ] Test progressive disclosure timing
- [ ] Test with brand new store (0 orders)
- [ ] Test with small store (< 10 orders)
- [ ] Test with medium store (100+ orders)
- [ ] Test with large store (1000+ orders)
- [ ] Test API rate limit handling
- [ ] Test cache behavior (second load < 100ms)
- [ ] Test error scenarios (invalid token, network issues)
- [ ] Verify natural conversation flow
- [ ] Test transition to ad_hoc_support workflow

## Performance Optimization

### 1. Caching Strategy

```python
# Redis cache configuration
CACHE_CONFIG = {
    "tier_1": 900,    # 15 minutes
    "tier_2": 600,    # 10 minutes  
    "tier_3": 300,    # 5 minutes
}
```

### 2. Query Optimization

- GraphQL query requests only needed fields
- REST queries use minimal page sizes
- Parallel execution where possible

### 3. Rate Limit Management

```python
# Implement exponential backoff
async def with_rate_limit_retry(func, max_retries=3):
    for i in range(max_retries):
        try:
            return await func()
        except RateLimitError:
            wait_time = 2 ** i
            await asyncio.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

## Implementation Timeline

### Phase 5.1: Core Infrastructure (2 hours)
1. Implement Shopify GraphQL client
2. Create QuickShopifyInsights service
3. Build shopify_data tool
4. Update workflow YAML

### Phase 5.2: Integration (1 hour)
1. Register tool with CJ agent
2. Test OAuth → insights flow
3. Verify progressive disclosure timing

### Phase 5.3: Polish & Testing (1 hour)
1. Add comprehensive error handling
2. Implement caching strategy
3. Run full test suite
4. Manual testing with real stores

## Production Considerations

### 1. Monitoring

Add these metrics:
- Tool execution time by tier
- API call success rate
- Cache hit rate
- OAuth → first insight latency

### 2. Configuration

```yaml
# In workflow YAML
config:
  insights:
    enable_tier_3: true
    max_orders_analyze: 50
    cache_ttl:
      tier_1: 900
      tier_2: 600
      tier_3: 300
    api_version: "2025-01"  # Latest stable API version
```

### 3. Graceful Degradation

The tool handles failures gracefully:
- Returns partial data if available
- Provides helpful error messages
- Never blocks the conversation flow

## Key Differences from Original Design

1. **No Hardcoded Methods**: Everything is tool and workflow-driven
2. **System Events**: OAuth completion handled via YAML configuration
3. **Consistent Pattern**: Uses same tool pattern as universe data
4. **Backend Authority**: All configuration in workflow YAMLs
5. **Latest API Version**: Using Shopify GraphQL API 2025-01 (latest stable)

## API Version Notes

- Using Shopify API version **2025-01** (latest stable as of January 2025)
- GraphQL endpoint: `/admin/api/2025-01/graphql.json`
- REST endpoints: `/admin/api/2025-01/{resource}.json`
- Required header: `Content-Type: application/json` (breaking change in 2025-01)
- Authentication: `X-Shopify-Access-Token` header

## Success Criteria

### Phase 5.3.5: PostgreSQL-Only Token Storage
- [ ] store_test_shopify_token.py script works correctly
- [ ] Tokens stored in PostgreSQL merchant_integrations table
- [ ] MerchantService uses PostgreSQL exclusively (no Redis)
- [ ] Connection pool properly initialized and reused
- [ ] Clean architecture with single source of truth

### Phase 5.3: Tool Creation
- [ ] CJ uses shopify_data tool (not hardcoded method)
- [ ] Tool returns raw data, not insights
- [ ] Agent generates all analysis and insights
- [ ] Tool works with PostgreSQL-stored test tokens

### Phase 5.4: Auth Service Migration
- [ ] Auth service stores tokens in PostgreSQL merchant_integrations
- [ ] ALL Redis token code removed from auth service
- [ ] ALL Redis token code removed from agents service
- [ ] Zero Redis dependencies for token storage anywhere
- [ ] Single source of truth achieved
- [ ] Accept that users may need to re-authenticate

### Phase 5.5-5.7: Complete Integration
- [ ] OAuth completion triggers system event
- [ ] Progressive disclosure feels natural
- [ ] Time to first data fetch < 500ms (p95)
- [ ] Complete flow < 10 seconds
- [ ] Zero hardcoded workflow logic
- [ ] Smooth transition to ad_hoc_support
- [ ] Proper handling of 60-day order limit

## Architecture Summary: What We Learned

### Token Storage Reality (Current State)
- Shopify access tokens are stored in **Redis** by the auth service
- Tokens are **NOT** in PostgreSQL (no shopify_access_token column exists)
- Key format: `merchant:{shop_domain}`
- TTL: 24 hours
- **Problem**: Bifurcated storage pattern violates Single Source of Truth

### Phase 5.3.5: Clean Break Approach
- PostgreSQL-only token storage - no Redis fallback
- Use store_test_shopify_token.py to add test tokens
- **Important**: Existing Redis tokens won't work - this is intentional
- Clean architecture from the start - no compatibility shims

### Phase 5.4: Complete Auth Service Migration
- Update auth service to store all new tokens in PostgreSQL
- One-time migration for critical production tokens
- Remove ALL Redis token code from auth service
- Existing users may need to re-authenticate (clean break)

### Simplified Implementation (Phase 5.2 Achievement)
- Removed unnecessary tier1/tier2/tier3 complexity
- Created pure data fetching service (ShopifyDataFetcher)
- All intelligence and analysis moved to CJ agent
- Tool just provides raw data, agent generates insights

### Testing Approach (Phase 5.3.5 Onwards)
- Store test tokens in PostgreSQL using provided script
- Tool uses PostgreSQL exclusively - no Redis checks
- Clean, simple testing with single data source
- Production tokens require Phase 5.4 migration

## Next Steps

### Immediate Actions (Phase 5.3.5)
1. Create store_test_shopify_token.py script
2. Implement PostgreSQL-only MerchantService (no Redis)
3. Store test token in PostgreSQL using script
4. Verify token retrieval works from PostgreSQL

### Then Continue (Phase 5.3)
1. Implement shopify_data tool using MerchantService
2. Register tool with CJ agent
3. Test with PostgreSQL-stored tokens
4. Verify data fetching and caching

### Complete Migration (Phase 5.4)
1. Update auth service to use PostgreSQL for all new tokens
2. One-time migration script for critical production tokens
3. Remove ALL Redis token code from auth service
4. Accept that existing users may need to re-authenticate

### Future Work
1. Monitor tool performance metrics
2. Gather feedback on data quality and agent analysis
3. Prepare for Support System Connection phases