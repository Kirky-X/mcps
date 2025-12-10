"""create SQLModel tables to match current definitions

Revision ID: 0002
Revises: 0001
Create Date: 2025-12-05
"""

from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'prompts',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('sync_hash', sa.String(), nullable=True),
        sa.UniqueConstraint('name', name='uq_prompts_name'),
    )

    op.create_table(
        'prompt_versions',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('prompt_id', sa.String(), sa.ForeignKey('prompts.id', ondelete=None), nullable=False),
        sa.Column('version', sa.String(length=10), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('description_vector', sa.LargeBinary(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_latest', sa.Boolean(), nullable=False),
        sa.Column('change_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('prompt_id', 'version', name='uq_prompt_version'),
    )

    op.create_table(
        'prompt_roles',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('version_id', sa.String(), sa.ForeignKey('prompt_versions.id', ondelete=None), nullable=False),
        sa.Column('role_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('template_variables', sa.JSON(), nullable=True),
    )

    op.create_table(
        'llm_configs',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('version_id', sa.String(), sa.ForeignKey('prompt_versions.id', ondelete=None), nullable=False, unique=True),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=False),
        sa.Column('top_p', sa.Float(), nullable=False),
        sa.Column('top_k', sa.Integer(), nullable=True),
        sa.Column('frequency_penalty', sa.Float(), nullable=False),
        sa.Column('presence_penalty', sa.Float(), nullable=False),
        sa.Column('stop_sequences', sa.JSON(), nullable=True),
        sa.Column('other_params', sa.JSON(), nullable=True),
    )

    op.create_table(
        'tags',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('name', name='uq_tags_name'),
    )

    op.create_table(
        'prompt_tags',
        sa.Column('version_id', sa.String(), sa.ForeignKey('prompt_versions.id', ondelete=None), primary_key=True, nullable=False),
        sa.Column('tag_id', sa.String(), sa.ForeignKey('tags.id', ondelete=None), primary_key=True, nullable=False),
    )

    op.create_table(
        'principle_prompts',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('version', sa.String(length=10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_latest', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('name', 'version', name='uq_principle_version'),
    )

    op.create_table(
        'version_principle_refs',
        sa.Column('version_id', sa.String(), sa.ForeignKey('prompt_versions.id', ondelete=None), primary_key=True, nullable=False),
        sa.Column('principle_id', sa.String(), sa.ForeignKey('principle_prompts.id', ondelete=None), primary_key=True, nullable=False),
        sa.Column('ref_version', sa.String(length=10), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
    )

    op.create_table(
        'llm_clients',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('default_principles', sa.JSON(), nullable=True),
        sa.UniqueConstraint('name', name='uq_llm_clients_name'),
    )

    op.create_table(
        'version_client_mapping',
        sa.Column('version_id', sa.String(), sa.ForeignKey('prompt_versions.id', ondelete=None), primary_key=True, nullable=False),
        sa.Column('client_id', sa.String(), sa.ForeignKey('llm_clients.id', ondelete=None), primary_key=True, nullable=False),
    )

    op.create_table(
        'app_config',
        sa.Column('key', sa.String(length=100), primary_key=True, nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('version_client_mapping')
    op.drop_table('llm_clients')
    op.drop_table('version_principle_refs')
    op.drop_table('principle_prompts')
    op.drop_table('prompt_tags')
    op.drop_table('tags')
    op.drop_table('llm_configs')
    op.drop_table('prompt_roles')
    op.drop_table('prompt_versions')
    op.drop_table('app_config')
    op.drop_table('prompts')
