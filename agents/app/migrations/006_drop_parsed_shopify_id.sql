-- Migration to drop parsed_shopify_id column from etl_freshdesk_tickets table
-- This field was never used as the expected custom field doesn't exist in Freshdesk

-- Drop the index first
DROP INDEX IF EXISTS idx_etl_freshdesk_tickets_parsed_shopify_id;

-- Drop the column
ALTER TABLE etl_freshdesk_tickets
DROP COLUMN IF EXISTS parsed_shopify_id;