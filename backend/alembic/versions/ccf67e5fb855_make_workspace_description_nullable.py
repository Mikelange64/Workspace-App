"""make workspace description nullable

Revision ID: ccf67e5fb855
Revises: 8bf4657f46fa
Create Date: 2026-07-02 17:49:25.561907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccf67e5fb855'
down_revision: Union[str, Sequence[str], None] = '8bf4657f46fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('workspaces', 'description',
               existing_type=sa.TEXT(),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('workspaces', 'description',
               existing_type=sa.TEXT(),
               nullable=False)
