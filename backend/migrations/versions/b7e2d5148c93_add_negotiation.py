"""add negotiation columns and vendor_messages

Revision ID: b7e2d5148c93
Revises: a1c4e9f20b31
Create Date: 2026-08-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b7e2d5148c93"
down_revision: Union[str, Sequence[str], None] = "a1c4e9f20b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ─── vendor_jobs: negotiation state ──────────────────────────────────────
    # `quote_amount` and `quoted_at` already exist and are reused — a parallel
    # price column would immediately raise "which one is authoritative?".
    op.add_column(
        "vendor_jobs", sa.Column("negotiation_thread_id", sa.Text(), nullable=True)
    )
    op.add_column(
        "vendor_jobs",
        sa.Column("negotiation_opened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "vendor_jobs",
        sa.Column("last_vendor_message_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "vendor_jobs",
        sa.Column(
            "followups_sent", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "vendor_jobs",
        sa.Column(
            "counter_rounds", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column("vendor_jobs", sa.Column("availability_text", sa.Text(), nullable=True))
    op.add_column("vendor_jobs", sa.Column("declined_reason", sa.Text(), nullable=True))
    op.add_column(
        "vendor_jobs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ─── vendor_messages ─────────────────────────────────────────────────────
    op.create_table(
        "vendor_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("vendor_job_id", sa.UUID(), nullable=False),
        sa.Column("sender", sa.String(10), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("extracted", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["vendor_job_id"], ["vendor_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # The transcript is always read as "this job's messages, oldest first".
    op.create_index(
        "ix_vendor_messages_job_created",
        "vendor_messages",
        ["vendor_job_id", "created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_vendor_messages_job_created", table_name="vendor_messages")
    op.drop_table("vendor_messages")

    for column in (
        "updated_at",
        "declined_reason",
        "availability_text",
        "counter_rounds",
        "followups_sent",
        "last_vendor_message_at",
        "negotiation_opened_at",
        "negotiation_thread_id",
    ):
        op.drop_column("vendor_jobs", column)
