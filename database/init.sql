-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schema for better organization
CREATE SCHEMA IF NOT EXISTS hirecj;

-- Set search path
SET search_path TO hirecj, public;

-- Grant permissions
GRANT ALL ON SCHEMA hirecj TO hirecj;
GRANT CREATE ON DATABASE hirecj_connections TO hirecj;