-- Migration 010: Create merchant_tokens table
-- Links users to merchants with their OAuth tokens
-- This allows us to track which user has access to which merchant

CREATE TABLE IF NOT EXISTS merchant_tokens (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    merchant_id INTEGER NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    shop_domain VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    scopes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, merchant_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_merchant_tokens_user ON merchant_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_merchant_tokens_merchant ON merchant_tokens(merchant_id);
CREATE INDEX IF NOT EXISTS idx_merchant_tokens_created ON merchant_tokens(created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE merchant_tokens IS 'Links users to merchants with their OAuth access tokens';
COMMENT ON COLUMN merchant_tokens.user_id IS 'Reference to users.id';
COMMENT ON COLUMN merchant_tokens.merchant_id IS 'Reference to merchants.id';
COMMENT ON COLUMN merchant_tokens.shop_domain IS 'Full Shopify domain (e.g., example.myshopify.com)';
COMMENT ON COLUMN merchant_tokens.access_token IS 'OAuth access token for this user-merchant combination';
COMMENT ON COLUMN merchant_tokens.scopes IS 'OAuth scopes granted for this token';