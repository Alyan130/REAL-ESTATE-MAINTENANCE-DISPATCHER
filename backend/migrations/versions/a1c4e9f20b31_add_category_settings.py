"""add category_settings

Revision ID: a1c4e9f20b31
Revises: 2f7d8c1a6b0e
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1c4e9f20b31"
down_revision: Union[str, Sequence[str], None] = "2f7d8c1a6b0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "category_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("pm_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("target_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "is_vendor_selectable", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["pm_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pm_id", "name", name="uq_category_settings_pm_name"),
        sa.CheckConstraint(
            "max_price IS NULL OR target_price IS NULL OR max_price >= target_price",
            name="ck_category_settings_price_order",
        ),
        sa.CheckConstraint(
            "target_price IS NULL OR target_price >= 0",
            name="ck_category_settings_target_non_negative",
        ),
        sa.CheckConstraint(
            "max_price IS NULL OR max_price >= 0",
            name="ck_category_settings_max_non_negative",
        ),
    )

    # Backfill every existing PM with the seed vocabulary. Raw SQL rather than an
    # import of app.core.categories — a migration must keep working after the
    # application code it was written against has moved on.
    #
    # Prices are left NULL deliberately: NULL max_price means "never
    # auto-approve", so no quote is ever approved without the PM having set a
    # ceiling themselves.
    op.execute(
        """
        INSERT INTO category_settings
            (id, pm_id, name, label, is_vendor_selectable, is_active,
             sort_order, created_at, updated_at)
        SELECT gen_random_uuid(), u.id, c.name, c.label, c.selectable, true,
               c.ord, now(), now()
          FROM users u
         CROSS JOIN (VALUES
             ('plumbing',   'Plumbing',   true,  0),
             ('electrical', 'Electrical', true,  1),
             ('hvac',       'HVAC',       true,  2),
             ('structural', 'Structural', true,  3),
             ('appliance',  'Appliance',  true,  4),
             ('pest',       'Pest',       true,  5),
             ('cleaning',   'Cleaning',   true,  6),
             ('other',      'Other',      false, 7)
         ) AS c(name, label, selectable, ord)
         WHERE u.role = 'pm'
        ON CONFLICT (pm_id, name) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("category_settings")
