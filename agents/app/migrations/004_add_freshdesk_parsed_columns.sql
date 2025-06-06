-- Migration: Add parsed columns to Freshdesk ETL tables
-- Purpose: Add parsed columns for quick access to commonly needed fields
-- Date: 2025-06-06

-- Add parsed columns to etl_freshdesk_tickets
ALTER TABLE etl_freshdesk_tickets
    ADD COLUMN IF NOT EXISTS parsed_created_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS parsed_updated_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS parsed_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS parsed_shopify_id VARCHAR(255);

-- Add parsed columns to etl_freshdesk_conversations
ALTER TABLE etl_freshdesk_conversations
    ADD COLUMN IF NOT EXISTS parsed_created_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS parsed_updated_at TIMESTAMP WITH TIME ZONE;

-- Add parsed columns to etl_freshdesk_ratings
ALTER TABLE etl_freshdesk_ratings
    ADD COLUMN IF NOT EXISTS parsed_rating INTEGER;

-- Create indexes (will be handled by run_migration.py with autocommit)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_freshdesk_tickets_parsed_created_at 
    ON etl_freshdesk_tickets(parsed_created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_freshdesk_tickets_parsed_updated_at 
    ON etl_freshdesk_tickets(parsed_updated_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_freshdesk_tickets_parsed_email 
    ON etl_freshdesk_tickets(parsed_email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_freshdesk_tickets_parsed_shopify_id 
    ON etl_freshdesk_tickets(parsed_shopify_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_freshdesk_conversations_parsed_created_at 
    ON etl_freshdesk_conversations(parsed_created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_freshdesk_conversations_parsed_updated_at 
    ON etl_freshdesk_conversations(parsed_updated_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_freshdesk_ratings_parsed_rating 
    ON etl_freshdesk_ratings(parsed_rating);