"""Create Sprint 5 tables: reminders and push_subscriptions.

Revision ID: 006_sprint5_reminders
Revises: 005_sprint4_memories
Create Date: 2026-06-01 00:00:00
"""

from alembic import op

revision = "006_sprint5_reminders"
down_revision = "005_sprint4_memories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE reminder_status AS ENUM "
        "('pending', 'sending', 'sent', 'failed', 'cancelled')"
    )
    op.execute("""
        CREATE TABLE reminders (
            id          UUID             PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id     UUID             NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       TEXT             NOT NULL,
            description TEXT,
            remind_at   TIMESTAMPTZ      NOT NULL,
            status      reminder_status  NOT NULL DEFAULT 'pending',
            source      TEXT             NOT NULL DEFAULT 'ui',
            created_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
            deleted_at  TIMESTAMPTZ
        )
    """)
    # Partial index for scheduler: only pending, non-deleted rows ordered by remind_at
    op.execute(
        "CREATE INDEX idx_reminders_pending ON reminders (user_id, remind_at) "
        "WHERE status = 'pending' AND deleted_at IS NULL"
    )
    op.execute("""
        CREATE TRIGGER trg_reminder_updated_at BEFORE UPDATE ON reminders
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    op.execute("""
        CREATE TABLE push_subscriptions (
            id         UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id    UUID        NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            endpoint   TEXT        NOT NULL,
            p256dh     TEXT        NOT NULL,
            auth       TEXT        NOT NULL,
            is_active  BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    # Partial index for push delivery: active subscriptions per user
    op.execute(
        "CREATE INDEX idx_push_subscriptions_active ON push_subscriptions (user_id) "
        "WHERE is_active = TRUE"
    )
    op.execute("""
        CREATE TRIGGER trg_push_subscription_updated_at BEFORE UPDATE ON push_subscriptions
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS push_subscriptions")
    op.execute("DROP TABLE IF EXISTS reminders")
    op.execute("DROP TYPE IF EXISTS reminder_status")
