"""init core models and vector structures

Revision ID: 0001
Revises: 
Create Date: 2025-12-05
"""

from alembic import op
import sqlalchemy as sa
import os


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Core tables by autogenerate are handled elsewhere; focus on vector and extensions
    conn = op.get_bind()
    dialect = conn.dialect.name
    dim = int(os.getenv("VECTOR_DIMENSION", "768"))

    # Create core SQLModel tables if not exist
    # This migration assumes models are applied via application or later autogen revisions

    if dialect == 'postgresql':
        # Enable pgvector extension
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # Create vec_prompts table to match init_supabase_schema.sql exactly
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS vec_prompts (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                version_id VARCHAR(36) NOT NULL REFERENCES prompt_versions(id) ON DELETE CASCADE,
                description_vector VECTOR({dim}),
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """.format(dim=dim)
        )
        
        # Create index for faster vector queries (matching SQL file)
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_vec_prompts_version_id 
            ON vec_prompts(version_id)
            """
        )
        
        # Optional HNSW index (if available)
        try:
            op.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_vec_prompts_embedding 
                ON vec_prompts USING hnsw (description_vector vector_cosine_ops)
                """
            )
        except Exception:
            pass
            
        # Create RPC function for similarity search (matching SQL file)
        op.execute(
            """
            CREATE OR REPLACE FUNCTION match_prompt_versions (
                query_embedding VECTOR({dim}),
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
                FROM vec_prompts v
                WHERE 1 - (v.description_vector <=> query_embedding) > match_threshold
                ORDER BY v.description_vector <=> query_embedding
                LIMIT match_count;
            END;
            $$;
            """.format(dim=dim)
        )
    elif dialect == 'sqlite':
        # Create fallback table for envs without sqlite-vec
        op.execute("""
            CREATE TABLE IF NOT EXISTS vec_prompts (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                version_id TEXT NOT NULL REFERENCES prompt_versions(id),
                description_vector BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_vec_prompts_version_id ON vec_prompts(version_id)")


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == 'postgresql':
        op.execute("DROP FUNCTION IF EXISTS match_prompt_versions")
        op.execute("DROP TABLE IF EXISTS vec_prompts")
        # Do not drop extension automatically
    elif dialect == 'sqlite':
        op.execute("DROP TABLE IF EXISTS vec_prompts")
