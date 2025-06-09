-- Migration to add parsed_status column to etl_freshdesk_tickets table
-- This extracts the status field from JSONB for easier querying

-- Add the parsed_status column
ALTER TABLE etl_freshdesk_tickets
ADD COLUMN parsed_status INTEGER;

-- Create index for efficient status queries
CREATE INDEX idx_etl_freshdesk_tickets_parsed_status 
ON etl_freshdesk_tickets(parsed_status);

-- Backfill existing data
-- Status codes: 2=Open, 3=Pending, 4=Resolved, 5=Closed
UPDATE etl_freshdesk_tickets
SET parsed_status = (data->>'status')::INTEGER
WHERE data->>'status' IS NOT NULL;