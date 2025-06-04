-- Migration: Create complete ETL database schema with support analytics and daily summaries
-- Description: Creates all tables, functions, views, and indexes for the ETL system including daily ticket summaries
-- Combined from 001_create_all_tables.sql and 002_create_daily_ticket_summaries.sql

-- UP Migration
BEGIN;

-- Create merchants table
CREATE TABLE IF NOT EXISTS merchants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    is_test BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- Create Shopify customers ETL table
CREATE TABLE IF NOT EXISTS etl_shopify_customers (
    shopify_customer_id VARCHAR(255) NOT NULL,
    merchant_id INTEGER NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    data JSONB NOT NULL DEFAULT '{}',   -- Flexible data storage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    PRIMARY KEY (merchant_id, shopify_customer_id)
);

-- Create Freshdesk tickets ETL table
CREATE TABLE IF NOT EXISTS etl_freshdesk_tickets (
    freshdesk_ticket_id VARCHAR(255) NOT NULL,
    merchant_id INTEGER NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    data JSONB NOT NULL DEFAULT '{}',   -- Flexible ticket data storage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    PRIMARY KEY (merchant_id, freshdesk_ticket_id)
);

-- Create sync_metadata table for tracking ETL operations
CREATE TABLE IF NOT EXISTS sync_metadata (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL,  -- 'freshdesk_tickets', 'shopify_customers', etc.
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    last_successful_id VARCHAR(255) DEFAULT NULL,
    sync_status VARCHAR(20) DEFAULT NULL,  -- 'success', 'failed', 'in_progress'
    error_message TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    UNIQUE(merchant_id, resource_type)
);

-- Create merchant_integrations table for storing API keys and configurations
CREATE TABLE IF NOT EXISTS merchant_integrations (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,  -- 'freshdesk', 'shopify', etc.
    api_key TEXT,  -- Encrypted in production
    config JSONB DEFAULT '{}',  -- Platform-specific configuration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    UNIQUE(merchant_id, platform)
);

-- Create daily_ticket_summaries table
CREATE TABLE IF NOT EXISTS daily_ticket_summaries (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    message TEXT NOT NULL,
    context JSONB NOT NULL, -- Store all metrics for potential reuse
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_merchant_date UNIQUE(merchant_id, date)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_shopify_customers_merchant ON etl_shopify_customers(merchant_id);
CREATE INDEX IF NOT EXISTS idx_shopify_customers_data_email ON etl_shopify_customers((data->>'email'));
CREATE INDEX IF NOT EXISTS idx_freshdesk_tickets_merchant ON etl_freshdesk_tickets(merchant_id);
CREATE INDEX IF NOT EXISTS idx_freshdesk_tickets_created ON etl_freshdesk_tickets((data->>'created_at'));
CREATE INDEX IF NOT EXISTS idx_freshdesk_tickets_status ON etl_freshdesk_tickets((data->>'status'));
CREATE INDEX IF NOT EXISTS idx_freshdesk_tickets_shopify_customer_id ON etl_freshdesk_tickets((data->>'cf_shopify_customer_id')) WHERE data->>'cf_shopify_customer_id' IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sync_metadata_merchant_resource ON sync_metadata(merchant_id, resource_type);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_merchant_date ON daily_ticket_summaries(merchant_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_ticket_summaries(date);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_merchants_updated_at BEFORE UPDATE ON merchants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_etl_shopify_customers_updated_at BEFORE UPDATE ON etl_shopify_customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_etl_freshdesk_tickets_updated_at BEFORE UPDATE ON etl_freshdesk_tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sync_metadata_updated_at BEFORE UPDATE ON sync_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_merchant_integrations_updated_at BEFORE UPDATE ON merchant_integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_ticket_summaries_updated_at BEFORE UPDATE ON daily_ticket_summaries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for ticket analysis
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
    t.data->'satisfaction_rating'->>'rating' as satisfaction_rating,
    t.created_at as etl_created_at,
    t.updated_at as etl_updated_at
FROM etl_freshdesk_tickets t
JOIN merchants m ON m.id = t.merchant_id;

-- Create materialized view for daily metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_ticket_metrics AS
SELECT 
    merchant_id,
    DATE(((data->>'created_at')::timestamp)) as date,
    COUNT(*) as total_tickets,
    COUNT(*) FILTER (WHERE data->>'status' IN ('2', '3', '4', '5')) as open_tickets,
    COUNT(*) FILTER (WHERE data->>'status' = '5') as resolved_tickets,
    AVG(CASE 
        WHEN data->>'status' = '5' AND data->>'resolved_at' IS NOT NULL 
        THEN EXTRACT(EPOCH FROM ((data->>'resolved_at')::timestamp - (data->>'created_at')::timestamp)) / 3600
        ELSE NULL 
    END) as avg_resolution_hours,
    COUNT(DISTINCT data->>'cf_shopify_customer_id') FILTER (WHERE data->>'cf_shopify_customer_id' IS NOT NULL) as unique_customers,
    COUNT(*) FILTER (WHERE data->'satisfaction_rating'->>'rating' IS NOT NULL) as rated_tickets,
    AVG((data->'satisfaction_rating'->>'rating')::numeric) FILTER (WHERE data->'satisfaction_rating'->>'rating' IS NOT NULL) as avg_satisfaction
FROM etl_freshdesk_tickets
GROUP BY merchant_id, date;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_daily_metrics_merchant_date ON daily_ticket_metrics(merchant_id, date);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_daily_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_ticket_metrics;
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON TABLE merchants IS 'Merchant accounts in the system';
COMMENT ON TABLE etl_shopify_customers IS 'ETL table for Shopify customer data with flexible JSONB storage';
COMMENT ON TABLE etl_freshdesk_tickets IS 'ETL table for Freshdesk ticket data with flexible JSONB storage';
COMMENT ON TABLE sync_metadata IS 'Tracks ETL sync operations and status for each resource type';
COMMENT ON TABLE merchant_integrations IS 'Stores API credentials and configuration for merchant integrations';
COMMENT ON TABLE daily_ticket_summaries IS 'Stores daily support summaries for each merchant';
COMMENT ON COLUMN daily_ticket_summaries.context IS 'JSONB storage of all metrics used to generate the summary';
COMMENT ON COLUMN daily_ticket_summaries.message IS 'The formatted summary message displayed to users';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user;

COMMIT;

-- DOWN Migration (if needed)
-- BEGIN;
-- DROP VIEW IF EXISTS ticket_analytics CASCADE;
-- DROP MATERIALIZED VIEW IF EXISTS daily_ticket_metrics CASCADE;
-- DROP FUNCTION IF EXISTS refresh_daily_metrics() CASCADE;
-- DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
-- DROP TABLE IF EXISTS daily_ticket_summaries CASCADE;
-- DROP TABLE IF EXISTS merchant_integrations CASCADE;
-- DROP TABLE IF EXISTS sync_metadata CASCADE;
-- DROP TABLE IF EXISTS etl_freshdesk_tickets CASCADE;
-- DROP TABLE IF EXISTS etl_shopify_customers CASCADE;
-- DROP TABLE IF EXISTS merchants CASCADE;
-- COMMIT;