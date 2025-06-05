-- Migration 003: User Identity Schema
-- Phase 4.5: Add user identity and persistence
-- 
-- This migration adds support for user identity tracking,
-- conversation persistence, and fact storage.
-- Uses PostgreSQL JSONB for flexible data storage.

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    shop_domain VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create conversations table for message persistence
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(50) REFERENCES users(id),
    message JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create user_facts table (single JSONB document per user)
CREATE TABLE IF NOT EXISTS user_facts (
    user_id VARCHAR(50) PRIMARY KEY REFERENCES users(id),
    facts JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_shop ON users(shop_domain);
CREATE INDEX IF NOT EXISTS idx_conv_user_created ON conversations(user_id, created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE users IS 'User accounts linked to Shopify shops';
COMMENT ON TABLE conversations IS 'Persistent conversation messages in JSONB format';
COMMENT ON TABLE user_facts IS 'Accumulated facts about users stored as JSONB array';

-- Ensure proper permissions (adjust based on your database setup)
-- For Supabase deployments, uncomment these:
-- GRANT ALL ON users TO postgres, anon, authenticated, service_role;
-- GRANT ALL ON conversations TO postgres, anon, authenticated, service_role;
-- GRANT ALL ON user_facts TO postgres, anon, authenticated, service_role;