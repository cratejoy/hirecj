# Universe Schema Documentation

## Overview

A universe represents the complete state of a merchant's business at a specific point in time within a scenario. It contains all the data needed for CJ to answer questions about support tickets, customer issues, business metrics, and operational status.

## Core Principles

1. **Immutable**: Once generated, a universe never changes
2. **Self-contained**: All data needed is within the universe file
3. **Time-aware**: Represents a specific day within a 90-day timeline
4. **Searchable**: Includes indexes for common query patterns

## Schema Structure

### 1. Metadata (Required)

```yaml
metadata:
  universe_id: string  # Unique identifier: "{merchant}_{scenario}_v{version}"
  merchant: string     # Merchant identifier (e.g., "marcus_thompson")
  scenario: string     # Scenario identifier (e.g., "steady_operations")
  generated_at: datetime  # When this universe was generated
  generator_version: string  # Version of generator used
  timeline_days: integer  # Total days in timeline (usually 90)
  current_day: integer   # Current day in the timeline (1-90)
```

### 2. Business Context (Required)

```yaml
business_context:
  current_state:
    mrr: number
    subscriber_count: integer
    churn_rate: number (percentage)
    csat_score: number (1-5)
    support_tickets_per_day: integer
    average_response_time_hours: number

  subscription_tiers:
    - name: string
      price: number
      active_subscribers: integer
```

### 3. Timeline Events (Optional but Recommended)

```yaml
timeline_events:
  - day: integer
    date: date
    event: string
    impact: enum [positive, negative, minor_negative, none]
    details: string (optional)
```

### 4. Customers (Required)

```yaml
customers:
  - customer_id: string
    name: string
    email: string
    customer_type: enum [gift_sender, active_subscriber, hybrid_subscriber, one_time_purchaser, repeat_purchaser]
    sub_type: string  # e.g., "happy_subscriber", "at_risk_subscriber", "corporate_buyer"
    subscription_tier: string (optional for non-subscribers)
    subscription_start_date: date (optional for non-subscribers)
    lifetime_value: number
    orders_count: integer
    last_order_date: date
    status: enum [active, paused, cancelled, never_subscribed]
    satisfaction_score: number (1-5)
    support_tickets_count: integer
    purchase_patterns: object (optional)
      seasonal_buyer: boolean
      bulk_orderer: boolean
      gift_frequency: string
    notes: string (optional)
```

### 5. Support Tickets (Required)

```yaml
support_tickets:
  - ticket_id: string
    created_at: datetime
    customer_id: string (references customers)
    category: enum [shipping, account_management, product_feedback, quality_issues, billing]
    subject: string
    content: string
    sentiment: enum [positive, negative, neutral, frustrated, angry]
    priority: enum [low, normal, high, urgent]
    status: enum [open, in_progress, resolved, closed]
    resolved_at: datetime (if resolved)
    resolution: string (if resolved)
    assigned_to: string (optional)
```

### 6. Product Performance (Optional but Recommended)

```yaml
product_performance:
  top_rated_products:
    - name: string
      sku: string
      rating: number (1-5)
      reviews_count: integer
      inclusion_rate: number (0-1)

  problematic_products:
    - name: string
      sku: string
      rating: number
      issues: [string]
      action_taken: string
```

### 7. Search Indexes (Recommended for Performance)

```yaml
search_indexes:
  by_product:
    "{product_name}": [ticket_ids]

  by_issue_type:
    "{issue_type}": [ticket_ids]

  by_customer_sentiment:
    "{sentiment}": [ticket_ids]
```

## Minimal Required Fields

For a functioning universe, you need at minimum:
- metadata (all fields)
- At least one customer
- At least one ticket
- Basic business metrics

## Size Considerations

- **Small universe**: ~1000 tickets, <5MB file
- **Medium universe**: ~5000 tickets, 10-20MB file
- **Large universe**: ~10000 tickets, 30-50MB file

## Query Patterns

The universe should support these common queries efficiently:
1. "Show me tickets about {product}"
2. "What are today's support metrics?"
3. "Find frustrated customers"
4. "Show shipping delay complaints"
5. "What's the trend for {metric}?"

## Validation Rules

1. All customer_ids in tickets must exist in customers
2. Dates must be within the timeline range
3. Current_day must be between 1 and timeline_days
4. All enum values must be valid
5. Subscription tiers in customers must match business_context

## Example Usage

```python
# Load universe
universe = Universe.load("marcus_thompson_steady_operations_v1.yaml")

# Query tickets
shipping_tickets = universe.search_tickets(category="shipping")
frustrated_customers = universe.get_tickets_by_sentiment("frustrated")

# Get current metrics
metrics = universe.get_current_metrics()
print(f"MRR: ${metrics.mrr}, Tickets today: {metrics.daily_tickets}")
```

## Best Practices

1. **Generate consistently**: Use the same customer pool across days
2. **Maintain continuity**: Reference previous events in tickets
3. **Be realistic**: Ticket volume and types should match the scenario
4. **Include variety**: Mix of positive and negative feedback
5. **Think searchability**: Include product names and key terms in ticket content
