"""add_lower_email_username_indexes

Revision ID: 8bf4657f46fa
Revises: 28264bb8291a
Create Date: 2026-07-01 14:02:16.686953

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bf4657f46fa'
down_revision: Union[str, Sequence[str], None] = '28264bb8291a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_lower_email ON users (lower(email))")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_lower_username ON users (lower(username))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_lower_email")
    op.execute("DROP INDEX IF EXISTS ix_users_lower_username")
