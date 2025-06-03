"""Initial multi-tenant schema

Revision ID: 001
Revises: 
Create Date: 2025-01-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create schema
    op.execute("CREATE SCHEMA IF NOT EXISTS hirecj")
    
    # Create accounts table
    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        schema='hirecj'
    )
    op.create_index(op.f('ix_hirecj_accounts_slug'), 'accounts', ['slug'], schema='hirecj')
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('account_id', postgresql.UUID(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['hirecj.accounts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', 'email', name='uq_account_email'),
        schema='hirecj'
    )
    op.create_index(op.f('ix_hirecj_users_account_id'), 'users', ['account_id'], schema='hirecj')
    
    # Create credentials table
    op.create_table(
        'credentials',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('account_id', postgresql.UUID(), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('auth_type', sa.String(50), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['hirecj.accounts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='hirecj'
    )
    op.create_index('idx_account_provider_cred', 'credentials', ['account_id', 'provider'], schema='hirecj')
    
    # Create connections table
    op.create_table(
        'connections',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('account_id', postgresql.UUID(), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('credential_id', postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['hirecj.accounts.id'], ),
        sa.ForeignKeyConstraint(['credential_id'], ['hirecj.credentials.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='hirecj'
    )
    op.create_index('idx_account_provider', 'connections', ['account_id', 'provider'], schema='hirecj')
    op.create_index(op.f('ix_hirecj_connections_account_id'), 'connections', ['account_id'], schema='hirecj')


def downgrade() -> None:
    op.drop_index(op.f('ix_hirecj_connections_account_id'), table_name='connections', schema='hirecj')
    op.drop_index('idx_account_provider', table_name='connections', schema='hirecj')
    op.drop_table('connections', schema='hirecj')
    op.drop_index('idx_account_provider_cred', table_name='credentials', schema='hirecj')
    op.drop_table('credentials', schema='hirecj')
    op.drop_index(op.f('ix_hirecj_users_account_id'), table_name='users', schema='hirecj')
    op.drop_table('users', schema='hirecj')
    op.drop_index(op.f('ix_hirecj_accounts_slug'), table_name='accounts', schema='hirecj')
    op.drop_table('accounts', schema='hirecj')
    op.execute("DROP SCHEMA IF EXISTS hirecj CASCADE")