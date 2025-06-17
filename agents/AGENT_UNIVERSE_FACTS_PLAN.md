# Agent Universe Facts Planning Document

## Overview
This document outlines the plan to build a comprehensive data agent that can perform daily support team analytics and provide customer context from Shopify. The agent operates within workflows to provide automated insights and customer lookup capabilities.

## Current State Analysis
- **Existing Infrastructure**: Unified ticket view with comprehensive ticket, conversation, and rating data
- **Available Data**: Full Freshdesk ticket lifecycle, CSAT ratings, conversation history, timestamps
- **Integration Points**: CrewAI tools via database_tools.py, support_daily workflow
- **Completed Components**: Time-series analytics, spike detection, SLA tracking, CSAT analysis

## Stage 1: Foundation Analytics ✅ COMPLETE

### Summary of Completed Work
- **Core Analytics Library**: Implemented `freshdesk_analytics_lib.py` with 7 comprehensive analytics functions
- **Daily Metrics**: `get_daily_snapshot()` - provides new/closed tickets, response times, CSAT scores
- **CSAT Analysis**: `get_csat_detail_log()` - detailed satisfaction ratings with optional conversation history
- **Backlog Monitoring**: `get_open_ticket_distribution()` - age buckets and oldest ticket tracking
- **Performance Metrics**: `get_response_time_metrics()` - statistical analysis with CSAT correlation
- **Volume Trends**: `get_volume_trends()` - spike detection using statistical methods
- **SLA Tracking**: `get_sla_exceptions()` - configurable breach detection and pattern analysis
- **Integration**: All functions exposed as CrewAI tools with proper session management
- **Documentation**: Comprehensive guides created (ANALYTICS_SCENARIOS.md, ANALYTICS_QUICKSTART.md)

**Key Design Principles**:
- All functions require merchant_id as first parameter for data isolation
- Consistent session management pattern (sessions passed down, never created internally)
- Formatted outputs suitable for agent consumption
- Statistical methods for anomaly detection

## Stage 2: Shopify Customer Integration

### Overview
This stage focuses on connecting Freshdesk support tickets to Shopify customer data. The goal is to provide agents with comprehensive customer context using direct API lookups.

### Core Customer Tools

#### 1. **find_shopify_customer_by_email(merchant_id, session, email)**
**Purpose**: Simple customer lookup by email address

**Location**: `agents/app/lib/shopify_customer_lib.py`

**Input**:
```python
{
    "email": "customer@example.com"
}
```

**Output Schema**:
```python
{
    "found": True,
    "customer": {
        "id": 987654321,                     # Shopify customer ID
        "email": "customer@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "created_at": "2023-01-15T10:30:00Z",
        "orders_count": 5,
        "total_spent": "523.45",              # String from API
        "currency": "USD",
        "tags": "vip, repeat_customer",       # Comma-separated string
        "verified_email": True,
        "accepts_marketing": True,
        "phone": "+1234567890",
        "last_order_id": 54321,
        "last_order_name": "#1234",
        "note": "Prefers expedited shipping"
    },
    "message": "Customer found"
}
```

**Error Response**:
```python
{
    "found": False,
    "customer": None,
    "message": "No customer found with email: customer@example.com"
}
```

**Implementation Notes**:
- Direct Shopify Admin API call using REST endpoint
- No caching or database storage
- Returns first match if multiple customers share email (rare)
- Handles API rate limits gracefully

#### 2. **get_customer_order_history(merchant_id, session, customer_id, limit=10)**
**Purpose**: Retrieve recent order history for identified customer

**Location**: `agents/app/lib/shopify_customer_lib.py`

**Input**:
```python
{
    "customer_id": 987654321,
    "limit": 10  # Max orders to return
}
```

**Output Schema**:
```python
{
    "customer_id": 987654321,
    "orders": [
        {
            "id": 54321,
            "name": "#1234",                  # Order number
            "created_at": "2024-01-10T15:00:00Z",
            "financial_status": "paid",
            "fulfillment_status": "fulfilled",
            "total_price": "123.45",
            "currency": "USD",
            "line_items_count": 3,
            "line_items": [                   # Summary only
                {
                    "title": "Premium Widget",
                    "quantity": 2,
                    "price": "49.99"
                }
            ],
            "shipping_address": {
                "address1": "123 Main St",
                "city": "Springfield",
                "province": "IL",
                "country": "US",
                "zip": "62701"
            },
            "note": "Please leave at door"
        }
    ],
    "total_orders": 15,                       # Total lifetime orders
    "orders_returned": 10                     # Number in this response
}
```

**Implementation Notes**:
- Uses Shopify REST API `/customers/{id}/orders.json`
- Returns most recent orders up to limit
- Includes only essential order details
- No product variant or inventory details

### Integration with Existing Tools

1. **Ticket Enhancement**: When agent views a ticket, they can lookup customer by email from ticket
2. **Workflow Integration**: Add customer lookup as optional step in support workflows
3. **Context Building**: Combine customer data with ticket history for complete picture

### Implementation Phases

**Phase 1: Email Lookup** (Week 1)
- Implement `find_shopify_customer_by_email`
- Basic Shopify API integration and authentication
- Error handling and rate limiting
- CrewAI tool wrapper

**Phase 2: Order History** (Week 1-2)
- Implement `get_customer_order_history`
- Format order data for agent consumption
- Add to database_tools.py
- Integration testing

### Success Metrics
- <2 second response time for email lookup
- <3 second response time for order history
- 95%+ accuracy in customer identification
- Zero API rate limit violations

## Implementation Guidelines

### Data Isolation Requirements
- **CRITICAL**: Every function MUST filter by merchant_id as the first operation
- **NEVER** accept merchant names as input - only merchant_id
- **NEVER** perform merchant lookups by name within these functions
- All API calls must include proper merchant context
- No function should ever return data from multiple merchants

### API Integration Best Practices
- Use environment variables for API credentials
- Implement exponential backoff for rate limits
- Log all API errors with context
- Return user-friendly error messages
- Monitor API usage to stay within limits

### Testing Requirements
- Mock Shopify API responses for unit tests
- Test error scenarios (not found, API down, rate limited)
- Verify merchant data isolation
- Integration tests with test Shopify store

## Next Steps
1. Review and approve simplified plan
2. Set up Shopify API credentials
3. Create shopify_customer_lib.py with email lookup
4. Add CrewAI tool wrappers
5. Test with real support tickets