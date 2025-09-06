"""Remove user foreign key constraint from analysis_tasks

Revision ID: remove_user_fk
Revises: 
Create Date: 2025-01-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_user_fk'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop the foreign key constraint if it exists
    try:
        op.drop_constraint('analysis_tasks_user_id_fkey', 'analysis_tasks', type_='foreignkey')
    except:
        pass  # Constraint might not exist
    
    # Drop the foreign key constraint on ai_usage table if it exists
    try:
        op.drop_constraint('ai_usage_user_id_fkey', 'ai_usage', type_='foreignkey')
    except:
        pass


def downgrade():
    # We don't want to recreate the foreign keys
    pass