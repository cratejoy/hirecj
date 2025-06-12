-- Migration 007: Create OAuth tables for shared database models
-- Created: 2025-01-11
-- Purpose: Add tables for OAuth state management (replacing Redis)

-- Create oauth_csrf_state table for Shopify OAuth CSRF protection
CREATE TABLE IF NOT EXISTS oauth_csrf_state (
    state VARCHAR PRIMARY KEY,
    shop VARCHAR NOT NULL,
    conversation_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_oauth_csrf_state_expires_at ON oauth_csrf_state(expires_at);

-- Create oauth_completion_state table for OAuth completion handoff
CREATE TABLE IF NOT EXISTS oauth_completion_state (
    conversation_id VARCHAR PRIMARY KEY,
    data JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create index for unprocessed records
CREATE INDEX IF NOT EXISTS idx_oauth_completion_state_processed ON oauth_completion_state(processed);
-- Create index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_oauth_completion_state_expires_at ON oauth_completion_state(expires_at);