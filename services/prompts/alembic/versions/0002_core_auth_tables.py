"""core models and authentication tables

Revision ID: 0002_core_auth
Revises: 0001
Create Date: 2025-12-18
"""

from alembic import op
import sqlalchemy as sa
import os

revision = '0002_core_auth'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Create core model tables (from original 0002)
    op.create_table(
        'prompts',
        sa.Column('id', sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()") if dialect == 'postgresql' else None),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()") if dialect == 'postgresql' else sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("now()") if dialect == 'postgresql' else sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('sync_hash', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_prompts_name'),
    )
    op.create_index('idx_prompts_name', 'prompts', ['name'])
    op.create_index('idx_prompts_created_at', 'prompts', ['created_at'])

    op.create_table(
        'prompt_versions',
        sa.Column('id', sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()") if dialect == 'postgresql' else None),
        sa.Column('prompt_id', sa.String(length=36), sa.ForeignKey('prompts.id'), nullable=False),
        sa.Column('version', sa.String(length=10), nullable=False),
        sa.Column('version_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('description_vector', sa.LargeBinary() if dialect == 'postgresql' else sa.BLOB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_latest', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('change_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()") if dialect == 'postgresql' else sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prompt_id', 'version', name='uq_prompt_version'),
    )
    op.create_index('idx_prompt_versions_prompt_id', 'prompt_versions', ['prompt_id'])
    op.create_index('idx_prompt_versions_created_at', 'prompt_versions', ['created_at'])

    op.create_table(
        'prompt_roles',
        sa.Column('id', sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()") if dialect == 'postgresql' else None),
        sa.Column('version_id', sa.String(length=36), sa.ForeignKey('prompt_versions.id'), nullable=False),
        sa.Column('role_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('order_num', sa.Integer(), nullable=False),
        sa.Column('template_variables', sa.JSON() if dialect == 'postgresql' else sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_prompt_roles_version_id', 'prompt_roles', ['version_id'])

    op.create_table(
        'llm_configs',
        sa.Column('id', sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()") if dialect == 'postgresql' else None),
        sa.Column('version_id', sa.String(length=36), sa.ForeignKey('prompt_versions.id'), nullable=False, unique=True),
        sa.Column('model', sa.String(length=100), server_default='gpt-3.5-turbo', nullable=False),
        sa.Column('temperature', sa.Float(), server_default='0.7', nullable=False),
        sa.Column('max_tokens', sa.Integer(), server_default='1000', nullable=False),
        sa.Column('top_p', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('top_k', sa.Integer(), nullable=True),
        sa.Column('frequency_penalty', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('presence_penalty', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('stop_sequences', sa.JSON() if dialect == 'postgresql' else sa.Text(), nullable=True),
        sa.Column('other_params', sa.JSON() if dialect == 'postgresql' else sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'tags',
        sa.Column('id', sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()") if dialect == 'postgresql' else None),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()") if dialect == 'postgresql' else sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_tags_name'),
    )

    op.create_table(
        'prompt_tags',
        sa.Column('version_id', sa.String(length=36), sa.ForeignKey('prompt_versions.id'), primary_key=True, nullable=False),
        sa.Column('tag_id', sa.String(length=36), sa.ForeignKey('tags.id'), primary_key=True, nullable=False),
    )
    op.create_index('idx_prompt_tags_version_id', 'prompt_tags', ['version_id'])
    op.create_index('idx_prompt_tags_tag_id', 'prompt_tags', ['tag_id'])

    op.create_table(
        'principle_prompts',
        sa.Column('id', sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()") if dialect == 'postgresql' else None),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('version', sa.String(length=10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_latest', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()") if dialect == 'postgresql' else sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_principle_version'),
    )

    op.create_table(
        'version_principle_refs',
        sa.Column('version_id', sa.String(length=36), sa.ForeignKey('prompt_versions.id'), primary_key=True, nullable=False),
        sa.Column('principle_id', sa.String(length=36), sa.ForeignKey('principle_prompts.id'), primary_key=True, nullable=False),
        sa.Column('ref_version', sa.String(length=10), nullable=False),
        sa.Column('order_num', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('version_id', 'principle_id'),
    )

    op.create_table(
        'llm_clients',
        sa.Column('id', sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()") if dialect == 'postgresql' else None),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('default_principles', sa.JSON() if dialect == 'postgresql' else sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_llm_clients_name'),
    )

    op.create_table(
        'version_client_mapping',
        sa.Column('version_id', sa.String(length=36), sa.ForeignKey('prompt_versions.id'), primary_key=True, nullable=False),
        sa.Column('client_id', sa.String(length=36), sa.ForeignKey('llm_clients.id'), primary_key=True, nullable=False),
        sa.PrimaryKeyConstraint('version_id', 'client_id'),
    )

    op.create_table(
        'app_config',
        sa.Column('key', sa.String(length=100), primary_key=True, nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
    )

    # Insert default app configuration
    op.execute(
        """
        INSERT INTO app_config (key, value) VALUES 
            ('vector_dimension', '768'),
            ('default_model', 'gpt-3.5-turbo'),
            ('max_search_results', '10')
        ON CONFLICT (key) DO NOTHING
        """
    )

    # Create authentication tables (from original 0003)
    op.create_table(
        'user',
        sa.Column('id', sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()") if dialect == 'postgresql' else None),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()") if dialect == 'postgresql' else sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("now()") if dialect == 'postgresql' else sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_user_email'),
    )
    op.create_index('idx_user_email', 'user', ['email'])

    op.create_table(
        'oauth_account',
        sa.Column('id', sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()") if dialect == 'postgresql' else None),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_account_id', sa.String(length=255), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.Integer(), nullable=True),
        sa.Column('scope', sa.String(length=500), nullable=True),
        sa.Column('token_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()") if dialect == 'postgresql' else sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("now()") if dialect == 'postgresql' else sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_account_id', name='uq_oauth_provider_account'),
    )
    op.create_index('idx_oauth_account_user_id', 'oauth_account', ['user_id'])
    op.create_index('idx_oauth_account_provider', 'oauth_account', ['provider'])


def downgrade() -> None:
    # Drop authentication tables first (reverse order of original 0003)
    op.drop_index('idx_oauth_account_provider', table_name='oauth_account')
    op.drop_index('idx_oauth_account_user_id', table_name='oauth_account')
    op.drop_table('oauth_account')
    op.drop_index('idx_user_email', table_name='user')
    op.drop_table('user')

    # Drop core model tables (reverse order of original 0002)
    op.drop_table('version_client_mapping')
    op.drop_table('llm_clients')
    op.drop_table('version_principle_refs')
    op.drop_table('principle_prompts')
    op.drop_index('idx_prompt_tags_tag_id', table_name='prompt_tags')
    op.drop_index('idx_prompt_tags_version_id', table_name='prompt_tags')
    op.drop_table('prompt_tags')
    op.drop_table('tags')
    op.drop_table('llm_configs')
    op.drop_index('idx_prompt_roles_version_id', table_name='prompt_roles')
    op.drop_table('prompt_roles')
    op.drop_index('idx_prompt_versions_created_at', table_name='prompt_versions')
    op.drop_index('idx_prompt_versions_prompt_id', table_name='prompt_versions')
    op.drop_table('prompt_versions')
    op.drop_index('idx_prompts_created_at', table_name='prompts')
    op.drop_index('idx_prompts_name', table_name='prompts')
    op.drop_table('prompts')
    op.drop_table('app_config')