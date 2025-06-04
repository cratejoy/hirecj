# Database Schema Documentation

## Overview

This schema is designed for ETL'd support data storage using PostgreSQL's JSONB capabilities. The design prioritizes flexibility and simplicity over rigid relational structures.

## Design Principles

1. **Envelope Pattern**: Tables serve as "envelopes" for JSONB data blobs
2. **Source-Specific Tables**: Separate tables for each data source (Shopify, Freshdesk)
3. **Composite Primary Keys**: Use source system IDs with merchant_id for uniqueness
4. **Flexible Storage**: All business data lives in JSONB `data` columns
5. **ETL-Friendly**: Optimized for bulk data loading and updates

## Tables

### merchants
Primary entity table for businesses using the support system.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Auto-incrementing primary key |
| name | VARCHAR(255) | Unique merchant identifier (e.g., 'amir_elaguizy') |
| is_test | BOOLEAN | Flag for test/demo merchants |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | Last modification time |

### etl_shopify_customers
Shopify customer records with flexible JSONB storage.

| Column | Type | Description |
|--------|------|-------------|
| merchant_id | INTEGER | Foreign key to merchants (part of PK) |
| shopify_customer_id | VARCHAR(255) | Shopify customer ID (part of PK) |
| data | JSONB | All customer data (profile, metrics, orders, etc.) |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | Last modification time |

**Primary Key**: (merchant_id, shopify_customer_id)

### etl_freshdesk_tickets
Freshdesk ticket records with flexible JSONB storage.

| Column | Type | Description |
|--------|------|-------------|
| merchant_id | INTEGER | Foreign key to merchants (part of PK) |
| freshdesk_ticket_id | VARCHAR(255) | Freshdesk ticket ID (part of PK) |
| data | JSONB | All ticket data (conversations, status, etc.) |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | Last modification time |

**Primary Key**: (merchant_id, freshdesk_ticket_id)

### sync_metadata
Tracks ETL sync operations for incremental updates.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Auto-incrementing primary key |
| merchant_id | INTEGER | Foreign key to merchants |
| resource_type | VARCHAR(50) | Type of resource (e.g., 'freshdesk_tickets') |
| last_sync_at | TIMESTAMP WITH TIME ZONE | Last successful sync timestamp |
| last_successful_id | VARCHAR(255) | ID of last synced record |
| sync_status | VARCHAR(20) | Status: 'success', 'failed', 'in_progress' |
| error_message | TEXT | Error details if sync failed |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | Last modification time |

**Unique Constraint**: (merchant_id, resource_type)

### merchant_integrations
Stores API keys and configurations for merchant integrations.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Auto-incrementing primary key |
| merchant_id | INTEGER | Foreign key to merchants |
| type | VARCHAR(50) | Integration type ('freshdesk', 'shopify') |
| api_key | TEXT | Encrypted API key |
| config | JSONB | Integration-specific configuration |
| is_active | BOOLEAN | Whether integration is active |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | Last modification time |

**Unique Constraint**: (merchant_id, type)

## Indexes

### Performance Indexes
- `idx_shopify_customers_merchant_id`: Fast merchant filtering
- `idx_freshdesk_tickets_merchant_id`: Fast merchant filtering
- `idx_shopify_customers_created_at`: Time-based queries
- `idx_freshdesk_tickets_created_at`: Time-based queries
- `idx_sync_metadata_merchant_id`: Sync status lookups
- `idx_sync_metadata_resource_type`: Resource type filtering
- `idx_merchant_integrations_merchant_id`: Integration lookups

### JSONB GIN Indexes
- `idx_shopify_customers_data_gin`: Efficient JSONB queries
- `idx_freshdesk_tickets_data_gin`: Efficient JSONB queries

## Support Analytics

### Functions
- `extract_ticket_status(data JSONB)`: Normalizes ticket status values
- `extract_ticket_priority(data JSONB)`: Normalizes ticket priority values
- `get_support_summary(...)`: Returns aggregated support metrics for a date range
- `get_trending_categories(...)`: Returns top ticket categories/tags
- `compare_support_periods(...)`: Compares metrics between two time periods

### Views
- `current_queue_status`: Real-time view of open/pending tickets

## JSONB Query Examples

```sql
-- Find VIP customers
SELECT * FROM etl_shopify_customers 
WHERE data->'tags' ? 'vip';

-- Find high-priority tickets
SELECT * FROM etl_freshdesk_tickets 
WHERE extract_ticket_priority(data) = 'high';

-- Count tickets by category
SELECT 
    tag,
    COUNT(*) 
FROM etl_freshdesk_tickets,
LATERAL jsonb_array_elements_text(data->'tags') as tag
GROUP BY tag;

-- Find customers by order count
SELECT * FROM etl_shopify_customers 
WHERE (data->>'orders_count')::int > 10;

-- Find tickets with conversations
SELECT * FROM etl_freshdesk_tickets
WHERE data ? 'conversations';
```

## ETL Patterns

### Upsert Pattern
```sql
-- Shopify customer upsert
INSERT INTO etl_shopify_customers (merchant_id, shopify_customer_id, data)
VALUES (1, '12345', '{"email": "john@example.com", "orders_count": 5}')
ON CONFLICT (merchant_id, shopify_customer_id) 
DO UPDATE SET data = EXCLUDED.data, updated_at = NOW();

-- Freshdesk ticket upsert
INSERT INTO etl_freshdesk_tickets (merchant_id, freshdesk_ticket_id, data)
VALUES (1, '67890', '{"subject": "Help needed", "status": "open"}')
ON CONFLICT (merchant_id, freshdesk_ticket_id) 
DO UPDATE SET data = EXCLUDED.data, updated_at = NOW();
```

### Bulk Loading
- Use COPY commands for initial loads
- Use batch upserts for incremental updates
- Transaction batching for consistency
- Two-pass sync for tickets: metadata first, then conversations

## Migration Strategy

1. **Single consolidated migration**: All schema in `001_create_all_tables.sql`
2. **Forward-only migrations**: No automatic rollbacks
3. **Idempotent operations**: Safe to run multiple times
4. **JSONB flexibility**: Schema changes rarely needed

## Future Considerations

- **Partitioning**: By merchant_id or created_at for scale
- **Read replicas**: For analytics workloads
- **Archival**: Move old tickets to cold storage
- **Additional sources**: Easy to add new ETL tables (e.g., `etl_zendesk_tickets`)