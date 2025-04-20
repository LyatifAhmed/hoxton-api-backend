"""Initial tables

Revision ID: 76fc01517b27
Revises: 
Create Date: 2025-04-17 23:42:32.031890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76fc01517b27'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('subscriptions', sa.Column('review_status', sa.String(length=50), nullable=False, server_default='PENDING_REVIEW'))
    # Optional: If you're no longer using these fields, remove them:
    op.drop_column('subscriptions', 'reviewed')
    op.drop_column('subscriptions', 'approved')
    op.drop_column('subscriptions', 'notes')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('subscriptions', sa.Column('reviewed', sa.Boolean(), nullable=True))
    op.add_column('subscriptions', sa.Column('approved', sa.Boolean(), nullable=True))
    op.add_column('subscriptions', sa.Column('notes', sa.Text(), nullable=True))
    op.drop_column('subscriptions', 'review_status')

    # ### end Alembic commands ###
