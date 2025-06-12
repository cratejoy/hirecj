-- Migration 009: Drop legacy oauth_completion_state table
-- Created: 2025-01-11
-- Purpose: Remove the old OAuth handoff mechanism now that we use 
--          direct server-to-server calls (Phase 6.4)

-- Drop the table and its indexes
DROP TABLE IF EXISTS oauth_completion_state CASCADE;

-- Note: This table was used for the "dead drop" pattern where the auth
-- service would write OAuth completion data and the agents service would
-- poll for it. This has been replaced by direct API calls between services.