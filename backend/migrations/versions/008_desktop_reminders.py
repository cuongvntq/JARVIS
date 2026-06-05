"""Desktop migration: add reminder_status.due, drop push_subscriptions, add due poll index."""

import sqlalchemy as sa
from alembic import op

revision = "008_desktop_reminders"
down_revision = "007_add_summary_to_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Note: ALTER TYPE ADD VALUE cannot be used in a partial index in the same transaction.
    # Solution: run ADD VALUE first via raw DDL (works in Postgres 12+ within a transaction
    # as long as we don't reference the new value in constraints/indexes in the same tx).
    # The index below does NOT filter on status='due' to avoid this restriction.
    op.execute("ALTER TYPE reminder_status ADD VALUE IF NOT EXISTS 'due'")

    # Drop push_subscriptions table (replaced by in-app polling)
    op.drop_table("push_subscriptions")

    # Index for GET /due poll — index on (user_id, status) for fast lookup of due reminders
    # Partial on deleted_at IS NULL only (avoids referencing the new enum value in same tx)
    op.create_index(
        "idx_reminders_user_status",
        "reminders",
        ["user_id", "status", "remind_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_reminders_user_status", table_name="reminders")
    # Note: push_subscriptions table not recreated — this migration is one-way
    # Note: Postgres does not support DROP ENUM VALUE — 'due' remains in type
