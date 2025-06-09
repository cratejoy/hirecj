-- Migration: Create complete ETL database schema
-- Description: Creates all tables, functions, views, and indexes for the ETL system
-- This is a consolidated, idempotent migration that creates the final schema

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
    etl_created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    etl_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    PRIMARY KEY (merchant_id, shopify_customer_id)
);

-- Create Freshdesk tickets ETL table (core ticket data only)
CREATE TABLE IF NOT EXISTS etl_freshdesk_tickets (
    freshdesk_ticket_id VARCHAR(255) NOT NULL,
    merchant_id INTEGER NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    data JSONB NOT NULL DEFAULT '{}',   -- Core ticket data only (no conversations/ratings)
    etl_created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    etl_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    PRIMARY KEY (merchant_id, freshdesk_ticket_id)
);

-- Handle etl_freshdesk_conversations table
-- First check if it exists with the old schema (with merchant_id)
DO $$
BEGIN
    -- If table exists and has merchant_id column, we need to migrate it
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'etl_freshdesk_conversations' 
        AND column_name = 'merchant_id'
    ) THEN
        -- Drop dependent objects
        DROP VIEW IF EXISTS ticket_analytics CASCADE;
        DROP MATERIALIZED VIEW IF EXISTS daily_ticket_metrics CASCADE;
        
        -- Drop constraints
        ALTER TABLE etl_freshdesk_conversations 
            DROP CONSTRAINT IF EXISTS etl_freshdesk_conversations_merchant_id_freshdesk_ticket_id_fkey,
            DROP CONSTRAINT IF EXISTS etl_freshdesk_conversations_pkey,
            DROP CONSTRAINT IF EXISTS etl_freshdesk_conversations_ticket_fkey;
        
        -- Drop indexes
        DROP INDEX IF EXISTS idx_freshdesk_conversations_merchant;
        DROP INDEX IF EXISTS idx_freshdesk_conversations_ticket_id;
        
        -- Drop the merchant_id column
        ALTER TABLE etl_freshdesk_conversations DROP COLUMN IF EXISTS merchant_id;
        
        -- Add new primary key
        ALTER TABLE etl_freshdesk_conversations ADD PRIMARY KEY (freshdesk_ticket_id);
    END IF;
END $$;

-- Create or ensure etl_freshdesk_conversations table has correct schema
CREATE TABLE IF NOT EXISTS etl_freshdesk_conversations (
    freshdesk_ticket_id VARCHAR(255) NOT NULL PRIMARY KEY,
    data JSONB NOT NULL DEFAULT '{}',   -- Array of conversation entries
    etl_created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    etl_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- Handle etl_freshdesk_ratings table
-- First check if it exists with the old schema (with merchant_id)
DO $$
BEGIN
    -- If table exists and has merchant_id column, we need to migrate it
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'etl_freshdesk_ratings' 
        AND column_name = 'merchant_id'
    ) THEN
        -- Drop constraints
        ALTER TABLE etl_freshdesk_ratings 
            DROP CONSTRAINT IF EXISTS etl_freshdesk_ratings_merchant_id_freshdesk_ticket_id_fkey,
            DROP CONSTRAINT IF EXISTS etl_freshdesk_ratings_pkey,
            DROP CONSTRAINT IF EXISTS etl_freshdesk_ratings_ticket_fkey;
        
        -- Drop indexes
        DROP INDEX IF EXISTS idx_freshdesk_ratings_merchant;
        DROP INDEX IF EXISTS idx_freshdesk_ratings_ticket_id;
        
        -- Drop the merchant_id column
        ALTER TABLE etl_freshdesk_ratings DROP COLUMN IF EXISTS merchant_id;
        
        -- Add new primary key
        ALTER TABLE etl_freshdesk_ratings ADD PRIMARY KEY (freshdesk_ticket_id);
    END IF;
END $$;

-- Create or ensure etl_freshdesk_ratings table has correct schema
CREATE TABLE IF NOT EXISTS etl_freshdesk_ratings (
    freshdesk_ticket_id VARCHAR(255) NOT NULL PRIMARY KEY,
    data JSONB NOT NULL DEFAULT '{}',   -- Satisfaction rating data
    etl_created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    etl_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
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


-- Add unique constraint on ticket ID (Freshdesk IDs are globally unique)
-- Use DO block to handle case where constraint already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'etl_freshdesk_tickets_ticket_id_unique'
    ) THEN
        ALTER TABLE etl_freshdesk_tickets 
            ADD CONSTRAINT etl_freshdesk_tickets_ticket_id_unique 
            UNIQUE (freshdesk_ticket_id);
    END IF;
END $$;

-- Add foreign key constraints (idempotent)
DO $$
BEGIN
    -- Add foreign key for conversations
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'etl_freshdesk_conversations_ticket_fkey'
    ) THEN
        ALTER TABLE etl_freshdesk_conversations 
            ADD CONSTRAINT etl_freshdesk_conversations_ticket_fkey 
            FOREIGN KEY (freshdesk_ticket_id) 
            REFERENCES etl_freshdesk_tickets(freshdesk_ticket_id) 
            ON DELETE CASCADE;
    END IF;
    
    -- Add foreign key for ratings
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'etl_freshdesk_ratings_ticket_fkey'
    ) THEN
        ALTER TABLE etl_freshdesk_ratings 
            ADD CONSTRAINT etl_freshdesk_ratings_ticket_fkey 
            FOREIGN KEY (freshdesk_ticket_id) 
            REFERENCES etl_freshdesk_tickets(freshdesk_ticket_id) 
            ON DELETE CASCADE;
    END IF;
END $$;

-- Create indexes (all idempotent with IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_shopify_customers_merchant ON etl_shopify_customers(merchant_id);
CREATE INDEX IF NOT EXISTS idx_shopify_customers_data_email ON etl_shopify_customers((data->>'email'));
CREATE INDEX IF NOT EXISTS idx_freshdesk_tickets_merchant ON etl_freshdesk_tickets(merchant_id);
CREATE INDEX IF NOT EXISTS idx_freshdesk_tickets_created ON etl_freshdesk_tickets((data->>'created_at'));
CREATE INDEX IF NOT EXISTS idx_etl_freshdesk_tickets_etl_created_at ON etl_freshdesk_tickets(etl_created_at);
CREATE INDEX IF NOT EXISTS idx_freshdesk_tickets_status ON etl_freshdesk_tickets((data->>'status'));
CREATE INDEX IF NOT EXISTS idx_freshdesk_tickets_shopify_customer_id ON etl_freshdesk_tickets((data->>'cf_shopify_customer_id')) WHERE data->>'cf_shopify_customer_id' IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_freshdesk_conversations_ticket_id ON etl_freshdesk_conversations(freshdesk_ticket_id);
CREATE INDEX IF NOT EXISTS idx_freshdesk_ratings_ticket_id ON etl_freshdesk_ratings(freshdesk_ticket_id);
CREATE INDEX IF NOT EXISTS idx_freshdesk_ratings_rating ON etl_freshdesk_ratings((data->>'rating')) WHERE data->>'rating' IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sync_metadata_merchant_resource ON sync_metadata(merchant_id, resource_type);

-- Create updated_at trigger function for regular tables
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create etl_updated_at trigger function for ETL tables
CREATE OR REPLACE FUNCTION update_etl_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.etl_updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at (using IF NOT EXISTS pattern)
DO $$
BEGIN
    -- Merchants table
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_merchants_updated_at'
    ) THEN
        CREATE TRIGGER update_merchants_updated_at 
            BEFORE UPDATE ON merchants
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- Shopify customers table (ETL)
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_etl_shopify_customers_etl_updated_at'
    ) THEN
        CREATE TRIGGER update_etl_shopify_customers_etl_updated_at 
            BEFORE UPDATE ON etl_shopify_customers
            FOR EACH ROW EXECUTE FUNCTION update_etl_updated_at_column();
    END IF;
    
    -- Freshdesk tickets table (ETL)
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_etl_freshdesk_tickets_etl_updated_at'
    ) THEN
        CREATE TRIGGER update_etl_freshdesk_tickets_etl_updated_at 
            BEFORE UPDATE ON etl_freshdesk_tickets
            FOR EACH ROW EXECUTE FUNCTION update_etl_updated_at_column();
    END IF;
    
    -- Freshdesk conversations table (ETL)
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_etl_freshdesk_conversations_etl_updated_at'
    ) THEN
        CREATE TRIGGER update_etl_freshdesk_conversations_etl_updated_at 
            BEFORE UPDATE ON etl_freshdesk_conversations
            FOR EACH ROW EXECUTE FUNCTION update_etl_updated_at_column();
    END IF;
    
    -- Freshdesk ratings table (ETL)
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_etl_freshdesk_ratings_etl_updated_at'
    ) THEN
        CREATE TRIGGER update_etl_freshdesk_ratings_etl_updated_at 
            BEFORE UPDATE ON etl_freshdesk_ratings
            FOR EACH ROW EXECUTE FUNCTION update_etl_updated_at_column();
    END IF;
    
    -- Sync metadata table
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_sync_metadata_updated_at'
    ) THEN
        CREATE TRIGGER update_sync_metadata_updated_at 
            BEFORE UPDATE ON sync_metadata
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- Merchant integrations table
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_merchant_integrations_updated_at'
    ) THEN
        CREATE TRIGGER update_merchant_integrations_updated_at 
            BEFORE UPDATE ON merchant_integrations
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
END $$;

-- Create view for ticket analytics (joining all three tables)
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

-- Create materialized view for daily metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_ticket_metrics AS
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
COMMENT ON TABLE etl_freshdesk_tickets IS 'ETL table for core Freshdesk ticket data (excluding conversations and ratings)';
COMMENT ON TABLE etl_freshdesk_conversations IS 'ETL table for Freshdesk ticket conversations stored as JSONB array';
COMMENT ON TABLE etl_freshdesk_ratings IS 'ETL table for Freshdesk satisfaction ratings (one per ticket max)';
COMMENT ON TABLE sync_metadata IS 'Tracks ETL sync operations and status for each resource type';
COMMENT ON TABLE merchant_integrations IS 'Stores API credentials and configuration for merchant integrations';

COMMIT;

-- Note: This migration is fully idempotent and can be run multiple times safely.
-- It will handle both fresh installations and upgrades from the old schema
-- where conversations and ratings tables had merchant_id columns.