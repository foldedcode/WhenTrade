"""enhance user tables for account management

Revision ID: enhance_user_tables
Revises: 5b2f2bc6cefd
Create Date: 2025-01-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'enhance_user_tables'
down_revision = '5b2f2bc6cefd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 扩展 users 表
    op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('notification_preferences', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False))
    op.add_column('users', sa.Column('last_password_change', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('two_factor_secret', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), server_default='false', nullable=False))
    
    # 创建 user_sessions 表
    op.create_table('user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_sessions_session_token', 'user_sessions', ['session_token'])
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    
    # 创建 login_history 表
    op.create_table('login_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('login_time', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_login_history_user_id', 'login_history', ['user_id'])
    op.create_index('ix_login_history_login_time', 'login_history', ['login_time'])
    
    # 创建 api_keys 表
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])
    
    # 创建 user_tools 表
    op.create_table('user_tools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tool_id', sa.String(100), nullable=False),
        sa.Column('tool_name', sa.String(255), nullable=False),
        sa.Column('tool_type', sa.String(50), nullable=False),
        sa.Column('connection_status', sa.String(50), server_default='disconnected', nullable=False),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_tools_user_id', 'user_tools', ['user_id'])
    op.create_index('ix_user_tools_tool_id', 'user_tools', ['tool_id'])
    
    # 创建 mcp_connections 表
    op.create_table('mcp_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_name', sa.String(255), nullable=False),
        sa.Column('server_url', sa.String(500), nullable=False),
        sa.Column('connection_status', sa.String(50), server_default='disconnected', nullable=False),
        sa.Column('available_tools', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('last_sync', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mcp_connections_user_id', 'mcp_connections', ['user_id'])


def downgrade() -> None:
    # 删除索引和表
    op.drop_index('ix_mcp_connections_user_id', table_name='mcp_connections')
    op.drop_table('mcp_connections')
    
    op.drop_index('ix_user_tools_tool_id', table_name='user_tools')
    op.drop_index('ix_user_tools_user_id', table_name='user_tools')
    op.drop_table('user_tools')
    
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_index('ix_api_keys_user_id', table_name='api_keys')
    op.drop_table('api_keys')
    
    op.drop_index('ix_login_history_login_time', table_name='login_history')
    op.drop_index('ix_login_history_user_id', table_name='login_history')
    op.drop_table('login_history')
    
    op.drop_index('ix_user_sessions_user_id', table_name='user_sessions')
    op.drop_index('ix_user_sessions_session_token', table_name='user_sessions')
    op.drop_table('user_sessions')
    
    # 删除 users 表的列
    op.drop_column('users', 'two_factor_enabled')
    op.drop_column('users', 'two_factor_secret')
    op.drop_column('users', 'last_password_change')
    op.drop_column('users', 'notification_preferences')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'bio')