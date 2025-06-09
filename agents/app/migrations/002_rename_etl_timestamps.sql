-- Migration: Rename ETL table timestamps and remove parsed columns
-- Description: Renames created_at/updated_at to etl_created_at/etl_updated_at and removes parsed_* columns

BEGIN;

-- Step 1: Rename timestamp columns in ETL tables
ALTER TABLE etl_shopify_customers 
    RENAME COLUMN created_at TO etl_created_at;
ALTER TABLE etl_shopify_customers 
    RENAME COLUMN updated_at TO etl_updated_at;

ALTER TABLE etl_freshdesk_tickets 
    RENAME COLUMN created_at TO etl_created_at;
ALTER TABLE etl_freshdesk_tickets 
    RENAME COLUMN updated_at TO etl_updated_at;

ALTER TABLE etl_freshdesk_conversations 
    RENAME COLUMN created_at TO etl_created_at;
ALTER TABLE etl_freshdesk_conversations 
    RENAME COLUMN updated_at TO etl_updated_at;

ALTER TABLE etl_freshdesk_ratings 
    RENAME COLUMN created_at TO etl_created_at;
ALTER TABLE etl_freshdesk_ratings 
    RENAME COLUMN updated_at TO etl_updated_at;

-- Step 2: Drop parsed columns from etl_freshdesk_tickets
ALTER TABLE etl_freshdesk_tickets 
    DROP COLUMN IF EXISTS parsed_created_at,
    DROP COLUMN IF EXISTS parsed_updated_at,
    DROP COLUMN IF EXISTS parsed_email,
    DROP COLUMN IF EXISTS parsed_status;

-- Step 3: Drop parsed columns from etl_freshdesk_conversations
ALTER TABLE etl_freshdesk_conversations 
    DROP COLUMN IF EXISTS parsed_created_at,
    DROP COLUMN IF EXISTS parsed_updated_at;

-- Step 4: Drop parsed columns from etl_freshdesk_ratings
ALTER TABLE etl_freshdesk_ratings 
    DROP COLUMN IF EXISTS parsed_rating;

-- Step 5: Drop old triggers
DROP TRIGGER IF EXISTS update_etl_shopify_customers_updated_at ON etl_shopify_customers;
DROP TRIGGER IF EXISTS update_etl_freshdesk_tickets_updated_at ON etl_freshdesk_tickets;
DROP TRIGGER IF EXISTS update_etl_freshdesk_conversations_updated_at ON etl_freshdesk_conversations;
DROP TRIGGER IF EXISTS update_etl_freshdesk_ratings_updated_at ON etl_freshdesk_ratings;

-- Step 6: Create new trigger function for ETL tables
CREATE OR REPLACE FUNCTION update_etl_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.etl_updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Step 7: Create new triggers with correct names
CREATE TRIGGER update_etl_shopify_customers_etl_updated_at 
    BEFORE UPDATE ON etl_shopify_customers
    FOR EACH ROW EXECUTE FUNCTION update_etl_updated_at_column();

CREATE TRIGGER update_etl_freshdesk_tickets_etl_updated_at 
    BEFORE UPDATE ON etl_freshdesk_tickets
    FOR EACH ROW EXECUTE FUNCTION update_etl_updated_at_column();

CREATE TRIGGER update_etl_freshdesk_conversations_etl_updated_at 
    BEFORE UPDATE ON etl_freshdesk_conversations
    FOR EACH ROW EXECUTE FUNCTION update_etl_updated_at_column();

CREATE TRIGGER update_etl_freshdesk_ratings_etl_updated_at 
    BEFORE UPDATE ON etl_freshdesk_ratings
    FOR EACH ROW EXECUTE FUNCTION update_etl_updated_at_column();

-- Step 8: Drop indexes that reference parsed columns
DROP INDEX IF EXISTS idx_etl_freshdesk_tickets_parsed_status;
DROP INDEX IF EXISTS idx_etl_freshdesk_tickets_created_at;

-- Step 9: Create new index on etl_created_at
CREATE INDEX IF NOT EXISTS idx_etl_freshdesk_tickets_etl_created_at ON etl_freshdesk_tickets(etl_created_at);

-- Step 10: Update the ticket_analytics view
CREATE OR REPLACE VIEW ticket_analytics AS
SELECT 
    m.name as merchant_name,
    t.freshdesk_ticket_id,
    t.data->>'subject' as subject,
    t.data->>'status' as status,
    t.data->>'priority' as priority,
    t.data->>'type' as ticket_type,
    t.data->>'cf_shopify_customer_id' as shopify_customer_id,
    (t.data->>'created_at')::timestamp as created_at,
    (t.data->>'updated_at')::timestamp as updated_at,
    (t.data->>'resolved_at')::timestamp as resolved_at,
    r.data->>'rating' as satisfaction_rating,
    c.data as conversations,
    t.etl_created_at as etl_created_at,
    t.etl_updated_at as etl_updated_at
FROM etl_freshdesk_tickets t
JOIN merchants m ON m.id = t.merchant_id
LEFT JOIN etl_freshdesk_conversations c ON c.freshdesk_ticket_id = t.freshdesk_ticket_id
LEFT JOIN etl_freshdesk_ratings r ON r.freshdesk_ticket_id = t.freshdesk_ticket_id;

-- Step 11: Drop and recreate the materialized view (can't alter columns)
DROP MATERIALIZED VIEW IF EXISTS daily_ticket_metrics;

CREATE MATERIALIZED VIEW daily_ticket_metrics AS
SELECT 
    t.merchant_id,
    DATE(((t.data->>'created_at')::timestamp)) as date,
    COUNT(*) as total_tickets,
    COUNT(*) FILTER (WHERE t.data->>'status' IN ('2', '3', '4', '5')) as open_tickets,
    COUNT(*) FILTER (WHERE t.data->>'status' = '5') as resolved_tickets,
    AVG(CASE 
        WHEN t.data->>'status' = '5' AND t.data->>'resolved_at' IS NOT NULL 
        THEN EXTRACT(EPOCH FROM ((t.data->>'resolved_at')::timestamp - (t.data->>'created_at')::timestamp)) / 3600
        ELSE NULL 
    END) as avg_resolution_hours,
    COUNT(DISTINCT t.data->>'cf_shopify_customer_id') FILTER (WHERE t.data->>'cf_shopify_customer_id' IS NOT NULL) as unique_customers,
    COUNT(DISTINCT r.freshdesk_ticket_id) as rated_tickets,
    AVG((r.data->>'rating')::numeric) as avg_satisfaction
FROM etl_freshdesk_tickets t
LEFT JOIN etl_freshdesk_ratings r ON r.freshdesk_ticket_id = t.freshdesk_ticket_id
GROUP BY t.merchant_id, date;

-- Recreate index on materialized view
CREATE INDEX idx_daily_metrics_merchant_date ON daily_ticket_metrics(merchant_id, date);

COMMIT;

-- Note: This migration renames timestamp columns in ETL tables to make it clear
-- they track when data was inserted into our database, not when events occurred upstream.