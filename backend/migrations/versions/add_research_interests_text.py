"""Add research_interests_text column to users table

Revision ID: add_research_interests_text
Revises: 
Create Date: 2023-07-25

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_research_interests_text'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('research_interests_text', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('users', 'research_interests_text') 