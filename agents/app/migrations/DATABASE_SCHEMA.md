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
| etl_created_at | TIMESTAMP WITH TIME ZONE | ETL record creation time |
| etl_updated_at | TIMESTAMP WITH TIME ZONE | ETL last modification time |

**Primary Key**: (merchant_id, shopify_customer_id)

### etl_freshdesk_tickets
Core Freshdesk ticket data (excluding conversations and ratings).

| Column | Type | Description |
|--------|------|-------------|
| merchant_id | INTEGER | Foreign key to merchants (part of PK) |
| freshdesk_ticket_id | VARCHAR(255) | Freshdesk ticket ID (part of PK) |
| data | JSONB | Core ticket data only |
| etl_created_at | TIMESTAMP WITH TIME ZONE | ETL record creation time |
| etl_updated_at | TIMESTAMP WITH TIME ZONE | ETL last modification time |

**Primary Key**: (merchant_id, freshdesk_ticket_id)

### etl_freshdesk_conversations
Ticket conversation history stored separately for performance.

| Column | Type | Description |
|--------|------|-------------|
| freshdesk_ticket_id | VARCHAR(255) | Foreign key to tickets (PK) |
| data | JSONB | Array of conversation entries |
| etl_created_at | TIMESTAMP WITH TIME ZONE | ETL record creation time |
| etl_updated_at | TIMESTAMP WITH TIME ZONE | ETL last modification time |

**Primary Key**: freshdesk_ticket_id

### etl_freshdesk_ratings
Customer satisfaction ratings (one per ticket maximum).

| Column | Type | Description |
|--------|------|-------------|
| freshdesk_ticket_id | VARCHAR(255) | Foreign key to tickets (PK) |
| data | JSONB | Rating data including score and feedback |
| etl_created_at | TIMESTAMP WITH TIME ZONE | ETL record creation time |
| etl_updated_at | TIMESTAMP WITH TIME ZONE | ETL last modification time |

**Primary Key**: freshdesk_ticket_id

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
- `idx_etl_shopify_customers_merchant_id`: Fast merchant filtering
- `idx_etl_shopify_customers_shopify_customer_id`: Customer ID lookups
- `idx_etl_freshdesk_tickets_merchant_id`: Fast merchant filtering  
- `idx_etl_freshdesk_tickets_freshdesk_ticket_id`: Ticket ID lookups
- `idx_etl_freshdesk_tickets_etl_created_at`: Time-based queries
- `idx_freshdesk_conversations_ticket_id`: Join optimization
- `idx_freshdesk_ratings_ticket_id`: Join optimization
- `idx_sync_metadata_merchant_id`: Sync status lookups
- `idx_sync_metadata_resource_type`: Resource type filtering
- `idx_merchant_integrations_merchant_id`: Integration lookups

### JSONB GIN Indexes
- `idx_etl_shopify_customers_data_gin`: Efficient JSONB queries
- `idx_etl_freshdesk_tickets_data_gin`: Efficient JSONB queries

### Specialized Indexes
- `idx_freshdesk_ratings_rating`: Filtered index on rating scores for CSAT queries

## Support Analytics

### Functions
- `extract_ticket_status(data JSONB)`: Normalizes ticket status values
- `extract_ticket_priority(data JSONB)`: Normalizes ticket priority values
- `get_support_summary(...)`: Returns aggregated support metrics for a date range
- `get_trending_categories(...)`: Returns top ticket categories/tags
- `compare_support_periods(...)`: Compares metrics between two time periods

### Views

#### current_queue_status
Real-time view of open/pending tickets (deprecated - use v_freshdesk_unified_tickets instead).

#### v_freshdesk_unified_tickets
Comprehensive view combining ticket, conversation, and rating data into a single queryable interface.

| Column | Type | Description |
|--------|------|-------------|
| merchant_id | INTEGER | Foreign key to merchants |
| freshdesk_ticket_id | VARCHAR(255) | Freshdesk ticket ID |
| ticket_id_numeric | BIGINT | Numeric ticket ID extracted from string |
| subject | TEXT | Ticket subject |
| description | TEXT | HTML ticket description (usually NULL - actual content in conversations) |
| type | VARCHAR | Ticket type |
| source | INTEGER | Source (1=Email, 2=Portal, 9=Chat, etc.) |
| spam | BOOLEAN | Spam flag |
| status | INTEGER | Status code (2=Open, 3=Pending, 4=Resolved, 5=Closed) |
| priority | INTEGER | Priority (1=Low, 2=Medium, 3=High, 4=Urgent) |
| is_escalated | BOOLEAN | General escalation flag |
| fr_escalated | BOOLEAN | First response escalation |
| nr_escalated | BOOLEAN | Next response escalation |
| requester_id | BIGINT | Freshdesk contact ID |
| requester_name | VARCHAR | Contact name |
| requester_email | VARCHAR | Contact email |
| responder_id | BIGINT | Assigned agent ID |
| company_id | BIGINT | Company ID |
| group_id | BIGINT | Support group ID |
| created_at | TIMESTAMP | Ticket creation time |
| updated_at | TIMESTAMP | Last update time |
| due_by | TIMESTAMP | Resolution due date |
| fr_due_by | TIMESTAMP | First response due |
| nr_due_by | TIMESTAMP | Next response due |
| first_responded_at | TIMESTAMP | First response time |
| agent_responded_at | TIMESTAMP | Last agent response |
| requester_responded_at | TIMESTAMP | Last customer response |
| closed_at | TIMESTAMP | Closure time |
| resolved_at | TIMESTAMP | Resolution time |
| reopened_at | TIMESTAMP | Reopen time if applicable |
| pending_since | TIMESTAMP | When entered pending state |
| status_updated_at | TIMESTAMP | Last status change |
| tags | JSONB | Array of tags |
| custom_fields | JSONB | All custom field values |
| conversation_count | INTEGER | Number of conversations |
| last_conversation_at | TIMESTAMP | Most recent conversation |
| has_agent_response | BOOLEAN | Whether agent has responded |
| has_rating | BOOLEAN | Whether customer rated |
| rating_score | INTEGER | Rating value (103=Happy, -103=Unhappy) |
| rating_feedback | TEXT | Customer feedback text |
| rating_created_at | TIMESTAMP | When rating was given |

This view is the primary interface for all ticket queries and should be used instead of joining the ETL tables directly.

## JSONB Query Examples

### Using the Unified View (Recommended)
```sql
-- Find high-priority unresolved tickets
SELECT * FROM v_freshdesk_unified_tickets
WHERE priority >= 3 AND status IN (2, 3);

-- Get tickets with poor ratings
SELECT freshdesk_ticket_id, subject, rating_score, rating_feedback
FROM v_freshdesk_unified_tickets
WHERE has_rating = true AND rating_score < 0;

-- Find tickets missing first response
SELECT * FROM v_freshdesk_unified_tickets
WHERE status = 2 AND first_responded_at IS NULL
ORDER BY created_at;

-- Analyze response times by priority
SELECT 
    priority,
    COUNT(*) as ticket_count,
    AVG(EXTRACT(EPOCH FROM (first_responded_at - created_at))/3600) as avg_response_hours
FROM v_freshdesk_unified_tickets
WHERE first_responded_at IS NOT NULL
GROUP BY priority;
```

### Direct Table Queries (Legacy)
```sql
-- Find VIP customers
SELECT * FROM etl_shopify_customers 
WHERE data->'tags' ? 'vip';

-- Find high-priority tickets
SELECT * FROM etl_freshdesk_tickets 
WHERE (data->>'priority')::int >= 3;

-- Count tickets by tag
SELECT 
    tag,
    COUNT(*) 
FROM etl_freshdesk_tickets,
LATERAL jsonb_array_elements_text(data->'tags') as tag
GROUP BY tag;

-- Find customers by order count
SELECT * FROM etl_shopify_customers 
WHERE (data->>'orders_count')::int > 10;
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