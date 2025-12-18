-- Supabase Schema Initialization Script
-- Generated for Prompt Manager Service
-- This script creates all necessary tables and functions in the 'prompts' schema

-- =====================================================
-- STEP 1: Create Schema and Enable Required Extensions
-- =====================================================

-- Create the prompts schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS prompts;

-- Enable pgvector extension in the public schema (required for vector operations)
CREATE EXTENSION IF NOT EXISTS vector;

-- Set search path to include prompts schema
SET search_path TO prompts, public;

-- =====================================================
-- STEP 2: Create Base Tables (No Dependencies)
-- =====================================================

-- Application configuration table
CREATE TABLE IF NOT EXISTS prompts.app_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT
);

-- Tags for categorizing prompts
CREATE TABLE IF NOT EXISTS prompts.tags (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Principle prompts for reusable content
CREATE TABLE IF NOT EXISTS prompts.principle_prompts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    version VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_latest BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_principle_version UNIQUE (name, version)
);

-- LLM client configurations
CREATE TABLE IF NOT EXISTS prompts.llm_clients (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    default_principles JSONB
);

-- =====================================================
-- STEP 3: Create Main Tables (Depend on Base Tables)
-- =====================================================

-- Main prompts table
CREATE TABLE IF NOT EXISTS prompts.prompts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) UNIQUE NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false,
    sync_hash VARCHAR(255)
);

-- =====================================================
-- STEP 4: Create Version-related Tables (Depend on Main Tables)
-- =====================================================

-- Prompt versions for tracking changes
CREATE TABLE IF NOT EXISTS prompts.prompt_versions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id VARCHAR(36) NOT NULL REFERENCES prompts.prompts(id),
    version VARCHAR(10) NOT NULL,
    version_number INTEGER DEFAULT 1,
    description TEXT NOT NULL,
    description_vector BYTEA,
    is_active BOOLEAN DEFAULT true,
    is_latest BOOLEAN DEFAULT false,
    change_log TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_prompt_version UNIQUE (prompt_id, version)
);

-- Prompt roles for different conversation contexts
CREATE TABLE IF NOT EXISTS prompts.prompt_roles (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id VARCHAR(36) NOT NULL REFERENCES prompts.prompt_versions(id),
    role_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    order_num INTEGER NOT NULL,
    template_variables JSONB
);

-- LLM configuration for each prompt version
CREATE TABLE IF NOT EXISTS prompts.llm_configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id VARCHAR(36) UNIQUE NOT NULL REFERENCES prompts.prompt_versions(id),
    model VARCHAR(100) DEFAULT 'gpt-3.5-turbo',
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 1000,
    top_p FLOAT DEFAULT 1.0,
    top_k INTEGER,
    frequency_penalty FLOAT DEFAULT 0.0,
    presence_penalty FLOAT DEFAULT 0.0,
    stop_sequences JSONB,
    other_params JSONB
);

-- =====================================================
-- STEP 5: Create Relationship Tables (Depend on Multiple Tables)
-- =====================================================

-- Many-to-many relationship between prompt versions and tags
CREATE TABLE IF NOT EXISTS prompts.prompt_tags (
    version_id VARCHAR(36) NOT NULL REFERENCES prompts.prompt_versions(id),
    tag_id VARCHAR(36) NOT NULL REFERENCES prompts.tags(id),
    PRIMARY KEY (version_id, tag_id)
);

-- References to principle prompts
CREATE TABLE IF NOT EXISTS prompts.version_principle_refs (
    version_id VARCHAR(36) NOT NULL REFERENCES prompts.prompt_versions(id),
    principle_id VARCHAR(36) NOT NULL REFERENCES prompts.principle_prompts(id),
    ref_version VARCHAR(10) NOT NULL,
    order_num INTEGER NOT NULL,
    PRIMARY KEY (version_id, principle_id)
);

-- Client mappings for prompt versions
CREATE TABLE IF NOT EXISTS prompts.version_client_mapping (
    version_id VARCHAR(36) NOT NULL REFERENCES prompts.prompt_versions(id),
    client_id VARCHAR(36) NOT NULL REFERENCES prompts.llm_clients(id),
    PRIMARY KEY (version_id, client_id)
);

-- =====================================================
-- STEP 6: Create Vector Table (Depends on prompt_versions)
-- =====================================================

-- Vector storage for semantic search
CREATE TABLE IF NOT EXISTS prompts.vec_prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    version_id VARCHAR(36) NOT NULL REFERENCES prompts.prompt_versions(id) ON DELETE CASCADE,
    description_vector VECTOR(768),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for faster vector queries
CREATE INDEX IF NOT EXISTS idx_vec_prompts_version_id ON prompts.vec_prompts(version_id);

-- =====================================================
-- STEP 7: Create Vector Search Function
-- =====================================================

-- Function for semantic similarity search
CREATE OR REPLACE FUNCTION prompts.match_prompt_versions (
    query_embedding VECTOR(768),
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE (
    id VARCHAR,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.version_id as id,
        1 - (v.description_vector <=> query_embedding) as similarity
    FROM prompts.vec_prompts v
    WHERE 1 - (v.description_vector <=> query_embedding) > match_threshold
    ORDER BY v.description_vector <=> query_embedding
    LIMIT match_count;
END;
$$;

-- =====================================================
-- STEP 8: Create Utility Functions
-- =====================================================

-- Get server time function for health checks
CREATE OR REPLACE FUNCTION prompts.get_server_time()
RETURNS TIMESTAMPTZ
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN now();
END;
$$;

-- =====================================================
-- STEP 9: Create FastAPI-Users Authentication Tables
-- =====================================================

-- User table for FastAPI-Users authentication
CREATE TABLE IF NOT EXISTS prompts.user (
    id UUID PRIMARY KEY,
    email VARCHAR(320) UNIQUE NOT NULL,
    hashed_password VARCHAR(1024) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    is_superuser BOOLEAN DEFAULT false NOT NULL,
    is_verified BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- OAuth account table for social authentication (optional)
CREATE TABLE IF NOT EXISTS prompts.oauth_account (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES prompts.user(id) ON DELETE CASCADE,
    oauth_name VARCHAR(100) NOT NULL,
    access_token VARCHAR(1024) NOT NULL,
    expires_at INTEGER,
    refresh_token VARCHAR(1024),
    account_id VARCHAR(320) NOT NULL,
    account_email VARCHAR(320) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT uq_oauth_account_user_oauth UNIQUE (user_id, oauth_name)
);

-- =====================================================
-- STEP 9: Create Useful Indexes
-- =====================================================

-- Performance indexes for main tables
CREATE INDEX IF NOT EXISTS idx_prompts_name ON prompts.prompts(name);
CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts.prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_id ON prompts.prompt_versions(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_created_at ON prompts.prompt_versions(created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_roles_version_id ON prompts.prompt_roles(version_id);
CREATE INDEX IF NOT EXISTS idx_prompt_tags_version_id ON prompts.prompt_tags(version_id);
CREATE INDEX IF NOT EXISTS idx_prompt_tags_tag_id ON prompts.prompt_tags(tag_id);

-- Indexes for auth tables
CREATE INDEX IF NOT EXISTS idx_user_email ON prompts.user(email);
CREATE INDEX IF NOT EXISTS idx_oauth_account_user_id ON prompts.oauth_account(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_account_account_id ON prompts.oauth_account(account_id);

-- =====================================================
-- STEP 10: Insert Default Configuration
-- =====================================================

-- Insert default app configuration
INSERT INTO prompts.app_config (key, value) VALUES 
    ('vector_dimension', '768'),
    ('default_model', 'gpt-3.5-turbo'),
    ('max_search_results', '10')
ON CONFLICT (key) DO NOTHING;

-- =====================================================
-- STEP 11: Grant Permissions (if needed)
-- =====================================================

-- Grant usage on schema to public (adjust as needed for your security requirements)
GRANT USAGE ON SCHEMA prompts TO public;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA prompts TO public;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA prompts TO public;

-- Specific permissions for auth tables (more restrictive)
REVOKE ALL ON prompts.user FROM public;
REVOKE ALL ON prompts.oauth_account FROM public;
GRANT SELECT, INSERT, UPDATE ON prompts.user TO public;
GRANT SELECT, INSERT, UPDATE, DELETE ON prompts.oauth_account TO public;

-- =====================================================
-- Verification Queries
-- =====================================================

-- Uncomment to verify installation
/*
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'prompts' 
ORDER BY table_name;

SELECT proname 
FROM pg_proc 
WHERE proname = 'match_prompt_versions' 
AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'prompts');

-- Check if vector extension is enabled
SELECT extname 
FROM pg_extension 
WHERE extname = 'vector';

-- Check table count in prompts schema
SELECT COUNT(*) as table_count
FROM information_schema.tables 
WHERE table_schema = 'prompts';
*/

-- =====================================================
-- Usage Notes
-- =====================================================
-- 1. Execute this script in order from top to bottom
-- 2. Ensure pgvector extension is available in your Supabase project
-- 3. All tables are created in the 'prompts' schema
-- 4. Foreign key constraints ensure data integrity
-- 5. Vector similarity search requires 768-dimensional embeddings
-- 6. Created indexes optimize common query patterns
-- 7. Remember to set search path in your application connection: SET search_path TO prompts, public;