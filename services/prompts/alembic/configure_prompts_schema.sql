-- Configure prompts schema for Supabase REST API access

-- Grant schema usage
GRANT USAGE ON SCHEMA prompts TO anon, authenticated, service_role;

-- Grant specific permissions on tables
-- anon: read-only on prompts (public view)
GRANT SELECT ON prompts.prompts TO anon;

-- authenticated: read-only on prompts, read-write on prompt_versions (for management)
GRANT SELECT ON prompts.prompts TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON prompts.prompt_versions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON prompts.prompts TO authenticated; -- Allow management of prompts
GRANT ALL ON prompts.tags TO authenticated;
GRANT ALL ON prompts.prompt_tags TO authenticated;
GRANT ALL ON prompts.principle_prompts TO authenticated;
GRANT ALL ON prompts.principles TO authenticated;

-- service_role: full access
GRANT ALL ON ALL TABLES IN SCHEMA prompts TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA prompts TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA prompts TO service_role;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA prompts GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA prompts GRANT SELECT ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA prompts GRANT ALL ON TABLES TO authenticated;

-- Create a simple function to test RPC calls
CREATE OR REPLACE FUNCTION prompts.get_server_time()
RETURNS TIMESTAMP WITH TIME ZONE
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN NOW();
END;
$$;

-- Grant execute permission on the function
GRANT EXECUTE ON FUNCTION prompts.get_server_time() TO anon, authenticated, service_role;

-- Also create the function in public schema for compatibility
CREATE OR REPLACE FUNCTION public.get_server_time()
RETURNS TIMESTAMP WITH TIME ZONE
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN NOW();
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_server_time() TO anon, authenticated, service_role;