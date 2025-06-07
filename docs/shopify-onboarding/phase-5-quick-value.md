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

Phase 5 delivers immediate value after Shopify OAuth by showing merchants quick insights about their store. Instead of complex ETL pipelines, we use a progressive disclosure pattern with targeted API calls.

## Core Architecture: Three-Tier Progressive Loading

### Tier 1: Instant Metrics (< 500ms)
Use existing REST count endpoints for immediate gratification:
- Customer count
- Total orders
- Active orders

### Tier 2: Quick Insights (< 2 seconds)
Single GraphQL query for rich contextual data:
- Recent orders with revenue
- Top products by inventory
- Store configuration

### Tier 3: Deeper Analysis (< 5 seconds)
Targeted REST queries with strict limits:
- Last week's order patterns
- Customer segmentation hints
- Revenue velocity

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
        self.endpoint = f"https://{self.shop_domain}/admin/api/2024-01/graphql.json"
        
        self.session = requests.Session()
        self.session.headers.update({
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
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
            }
          }
          
          orders(first: 10, reverse: true) {
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
                        price
                      }
                    }
                  }
                }
                customer {
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

### Step 3: Update CJ Agent for Progressive Disclosure

**File:** `agents/app/agents/cj_agent.py`

Add this method to the CJAgent class:

```python
async def handle_shopify_insights(self, session: Session) -> AsyncGenerator[str, None]:
    """Progressive disclosure of Shopify insights after OAuth."""
    
    # Get merchant details from session
    merchant_id = session.merchant_id
    shop_domain = session.context.get("shop_domain")
    access_token = await self._get_shopify_token(merchant_id)
    
    if not shop_domain or not access_token:
        yield "I'm having trouble accessing your store data. Let me try again..."
        return
    
    # Initialize insights service
    insights_service = QuickShopifyInsights(merchant_id, shop_domain, access_token)
    
    # Tier 1: Instant gratification (< 500ms)
    tier_1 = await insights_service.tier_1_snapshot()
    
    # Generate and yield first insights
    tier_1_insights = generate_quick_insights(tier_1)
    if tier_1_insights:
        yield tier_1_insights[0]  # Customer count
        await asyncio.sleep(0.5)
    
    # Show we're looking deeper
    yield "Let me take a quick look at your recent activity..."
    await asyncio.sleep(1.0)
    
    # Tier 2: Quick insights (< 2s)
    tier_2 = await insights_service.tier_2_insights()
    
    # Merge data for insights
    all_data = {**tier_1, **tier_2}
    all_insights = generate_quick_insights(all_data)
    
    # Yield insights with natural pacing
    for i, insight in enumerate(all_insights[1:5]):  # Skip first, show next 4
        yield insight
        await asyncio.sleep(0.8)
    
    # Check if we should go deeper
    if tier_2.get("recent_orders") and len(tier_2["recent_orders"]) > 5:
        yield "I'm seeing some interesting patterns in your data..."
        await asyncio.sleep(1.0)
        
        # Tier 3: Deeper analysis (< 5s)
        tier_3 = await insights_service.tier_3_analysis()
        final_data = {**all_data, **tier_3}
        
        # Show 1-2 more insights
        final_insights = generate_quick_insights(final_data)
        for insight in final_insights[5:7]:
            yield insight
            await asyncio.sleep(0.8)
    
    # Natural transition
    await asyncio.sleep(1.0)
    yield "Based on what I'm seeing, I can help you provide even better customer support. Would you like to connect your support system so I can give you personalized insights?"

async def _get_shopify_token(self, merchant_id: str) -> Optional[str]:
    """Get Shopify access token from storage."""
    # Implementation depends on your token storage
    # This is a placeholder
    return None
```

### Step 4: Update OAuth Complete Handler

**File:** `agents/app/services/message_processor.py`

Update the oauth_complete handler:

```python
async def handle_oauth_complete(self, data: Dict[str, Any]) -> None:
    """Handle OAuth completion with progressive insights."""
    
    # Existing OAuth handling...
    
    # After successful OAuth
    if data.get("provider") == "shopify" and data.get("success"):
        # Update session with shop details
        self.session.context["shop_domain"] = data.get("shop_domain")
        self.session.context["is_new_merchant"] = data.get("is_new", True)
        
        # Trigger insights flow
        insights_generator = self.cj_agent.handle_shopify_insights(self.session)
        
        async for insight in insights_generator:
            await self._send_message({
                "type": "message",
                "data": {
                    "conversation_id": self.session.conversation_id,
                    "message": {
                        "role": "assistant",
                        "content": insight,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            })
```

### Step 5: Error Handling and Edge Cases

Add these handlers to the QuickShopifyInsights class:

```python
def handle_new_store(self, tier_1_data: Dict) -> List[str]:
    """Special handling for brand new stores."""
    if tier_1_data.get("total_orders", 0) == 0:
        return [
            "I see you're just getting started - that's exciting!",
            "Your store is all set up and ready for your first customers",
            "Once you start getting orders, I'll be able to provide detailed insights"
        ]
    return []

def handle_api_errors(self, error: Exception) -> List[str]:
    """Graceful error handling."""
    if "rate limit" in str(error).lower():
        return ["Give me just a moment - I'm fetching your store data..."]
    elif "unauthorized" in str(error).lower():
        return ["I need to reconnect to your store. Let me help you with that..."]
    else:
        return ["I'm having a small technical issue accessing your data. Let's continue..."]
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

def test_generate_insights():
    """Test natural language generation."""
    data = {
        "customers": 1234,
        "recent_revenue": 5678.90,
        "order_velocity": 3.2
    }
    
    insights = generate_quick_insights(data)
    
    assert "1,234 customers" in insights[0]
    assert "$5,678.90" in insights[1]
    assert "3.2 orders per day" in insights[2]
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

- [ ] Test with brand new store (0 orders)
- [ ] Test with small store (< 10 orders)
- [ ] Test with medium store (100+ orders)
- [ ] Test with large store (1000+ orders)
- [ ] Test API rate limit handling
- [ ] Test cache behavior (second load < 100ms)
- [ ] Test error scenarios (invalid token, network issues)
- [ ] Test natural pacing of insights delivery
- [ ] Verify smooth transition to Phase 6

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

## Production Considerations

### 1. Monitoring

Add these metrics:
- Time to first insight (p50, p95, p99)
- API call success rate
- Cache hit rate
- Error rate by type

### 2. Feature Flags

```python
FEATURE_FLAGS = {
    "enable_tier_3_analysis": True,
    "enable_graphql_insights": True,
    "max_orders_to_analyze": 50,
}
```

### 3. Graceful Degradation

If any tier fails, continue with available data:
- Tier 1 fails: Use generic welcome message
- Tier 2 fails: Show only count-based insights
- Tier 3 fails: Skip pattern analysis

## Next Steps

After Phase 5 is complete:
1. Gather metrics on insight quality
2. A/B test different insight ordering
3. Add more sophisticated analysis in Tier 3
4. Prepare for Phase 6 (Support System Connection)

## Success Criteria

- [ ] Time to first insight < 500ms (p95)
- [ ] Complete flow < 10 seconds
- [ ] Zero full data syncs during demo
- [ ] Natural conversation flow maintained
- [ ] Smooth handoff to Phase 6