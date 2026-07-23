"""add sources json column to messages

Revision ID: f2a1f1d388b2
Revises: 9c18f1c708c0
Create Date: 2026-07-23 00:13:58.882263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a1f1d388b2'
down_revision: Union[str, Sequence[str], None] = '9c18f1c708c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('sources', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'sources')
