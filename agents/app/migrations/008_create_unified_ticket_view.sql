-- Migration: Create Freshdesk Unified Ticket View
-- Purpose: Single view combining data from tickets, conversations, and ratings tables
-- Date: 2025-06-08

BEGIN;

-- Drop the view if it exists (for idempotency)
DROP VIEW IF EXISTS v_freshdesk_unified_tickets CASCADE;

-- Create the unified ticket view
CREATE VIEW v_freshdesk_unified_tickets AS
WITH conversation_summary AS (
    -- Pre-aggregate conversation data for better performance
    SELECT 
        c.freshdesk_ticket_id,
        jsonb_array_length(c.data) as conversation_count,
        MAX((conv->>'created_at')::timestamp) as last_conversation_at,
        bool_or((conv->>'incoming')::boolean = false) as has_agent_response
    FROM etl_freshdesk_conversations c,
    LATERAL jsonb_array_elements(c.data) as conv
    GROUP BY c.freshdesk_ticket_id
),
rating_info AS (
    -- Pre-aggregate rating data
    SELECT 
        r.freshdesk_ticket_id,
        true as has_rating,
        (r.data->'ratings'->>'default_question')::integer as rating_score,
        r.data->>'feedback' as rating_feedback,
        (r.data->>'created_at')::timestamp as rating_created_at
    FROM etl_freshdesk_ratings r
)
SELECT 
    -- Core Ticket Identifiers
    t.merchant_id,
    t.freshdesk_ticket_id,
    NULLIF(regexp_replace(t.freshdesk_ticket_id, '[^0-9]', '', 'g'), '')::bigint as ticket_id_numeric,
    
    -- Basic Ticket Info
    t.data->>'subject' as subject,
    t.data->>'description' as description,
    -- description_text does not exist in Freshdesk API, removed
    t.data->>'type' as type,
    (t.data->'_raw_data'->>'source')::integer as source,
    (t.data->'_raw_data'->>'spam')::boolean as spam,
    
    -- Status & Priority
    (t.data->>'status')::integer as status,
    (t.data->>'priority')::integer as priority,
    (t.data->>'is_escalated')::boolean as is_escalated,
    (COALESCE(t.data->>'fr_escalated', t.data->'_raw_data'->>'fr_escalated'))::boolean as fr_escalated,
    (COALESCE(t.data->>'nr_escalated', t.data->'_raw_data'->>'nr_escalated'))::boolean as nr_escalated,
    
    -- People
    (t.data->>'requester_id')::bigint as requester_id,
    t.data->'requester'->>'name' as requester_name,
    t.data->'requester'->>'email' as requester_email,
    (t.data->'_raw_data'->>'responder_id')::bigint as responder_id,
    (t.data->'_raw_data'->>'company_id')::bigint as company_id,
    (t.data->'_raw_data'->>'group_id')::bigint as group_id,
    
    -- Timestamps
    (t.data->>'created_at')::timestamp with time zone as created_at,
    (t.data->>'updated_at')::timestamp with time zone as updated_at,
    (t.data->>'due_by')::timestamp with time zone as due_by,
    (t.data->>'fr_due_by')::timestamp with time zone as fr_due_by,
    (t.data->>'nr_due_by')::timestamp with time zone as nr_due_by,
    
    -- Stats (from data->'stats')
    (t.data->'stats'->>'first_responded_at')::timestamp with time zone as first_responded_at,
    (t.data->'stats'->>'agent_responded_at')::timestamp with time zone as agent_responded_at,
    (t.data->'stats'->>'requester_responded_at')::timestamp with time zone as requester_responded_at,
    (t.data->'stats'->>'closed_at')::timestamp with time zone as closed_at,
    (t.data->'stats'->>'resolved_at')::timestamp with time zone as resolved_at,
    (t.data->'stats'->>'reopened_at')::timestamp with time zone as reopened_at,
    (t.data->'stats'->>'pending_since')::timestamp with time zone as pending_since,
    (t.data->'stats'->>'status_updated_at')::timestamp with time zone as status_updated_at,
    
    -- Tags & Custom Fields
    t.data->'tags' as tags,
    t.data->'custom_fields' as custom_fields,
    
    -- Conversation Summary
    COALESCE(cs.conversation_count, 0) as conversation_count,
    cs.last_conversation_at,
    COALESCE(cs.has_agent_response, false) as has_agent_response,
    
    -- Rating Info
    COALESCE(ri.has_rating, false) as has_rating,
    ri.rating_score,
    ri.rating_feedback,
    ri.rating_created_at
    
FROM etl_freshdesk_tickets t
LEFT JOIN conversation_summary cs ON cs.freshdesk_ticket_id = t.freshdesk_ticket_id
LEFT JOIN rating_info ri ON ri.freshdesk_ticket_id = t.freshdesk_ticket_id;

-- Create helpful indexes on the base tables to support this view
CREATE INDEX IF NOT EXISTS idx_freshdesk_conversations_ticket_id 
    ON etl_freshdesk_conversations(freshdesk_ticket_id);

CREATE INDEX IF NOT EXISTS idx_freshdesk_ratings_ticket_id 
    ON etl_freshdesk_ratings(freshdesk_ticket_id);

-- Add comments for documentation
COMMENT ON VIEW v_freshdesk_unified_tickets IS 'Unified view of Freshdesk tickets combining data from tickets, conversations, and ratings tables. Maps directly to Freshdesk API v2 fields without any fallbacks or computed fields.';

COMMIT;

-- Rollback instructions:
-- DROP VIEW IF EXISTS v_freshdesk_unified_tickets CASCADE;