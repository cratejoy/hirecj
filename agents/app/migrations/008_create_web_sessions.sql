-- Migration: Create web_sessions table for HTTP session management
-- This implements the two-layer session pattern where HTTP cookies
-- handle user identity and WebSocket handles conversation state

CREATE TABLE IF NOT EXISTS web_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data JSONB DEFAULT '{}',
    
    -- Add foreign key constraint to users table
    CONSTRAINT fk_web_sessions_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE
);

-- Index for looking up sessions by user
CREATE INDEX IF NOT EXISTS idx_web_sessions_user_id 
    ON web_sessions(user_id);

-- Index for finding expired sessions (used by cleanup job)
-- Note: We can't use CURRENT_TIMESTAMP in a partial index predicate
-- because it's not immutable. The cleanup job will use expires_at < NOW()
CREATE INDEX IF NOT EXISTS idx_web_sessions_expires_at 
    ON web_sessions(expires_at);

-- Comments for documentation
COMMENT ON TABLE web_sessions IS 'HTTP session storage for cookie-based authentication';
COMMENT ON COLUMN web_sessions.session_id IS 'Unique session identifier stored in HTTP-only cookie';
COMMENT ON COLUMN web_sessions.user_id IS 'Reference to authenticated user';
COMMENT ON COLUMN web_sessions.expires_at IS 'Session expiration time (24 hours from creation)';
COMMENT ON COLUMN web_sessions.last_accessed_at IS 'Updated on each request to track activity';
COMMENT ON COLUMN web_sessions.data IS 'Optional session data storage';