"""add last_invite_iat

Revision ID: 2f7d8c1a6b0e
Revises: c9aa126c92e4
Create Date: 2026-04-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f7d8c1a6b0e"
down_revision: Union[str, Sequence[str], None] = "c9aa126c92e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("last_invite_iat", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "last_invite_iat")

