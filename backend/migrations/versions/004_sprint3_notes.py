"""Create Sprint 3 table: notes.

Revision ID: 004_sprint3_notes
Revises: 003_sprint2_todos_tool_logs
Create Date: 2026-05-28 00:00:00
"""

from alembic import op

revision = "004_sprint3_notes"
down_revision = "003_sprint2_todos_tool_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE notes (
            id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id     UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       VARCHAR(500)    NOT NULL,
            content     TEXT            NOT NULL DEFAULT '',
            tags        JSONB           NOT NULL DEFAULT '[]'::jsonb,
            pinned      BOOLEAN         NOT NULL DEFAULT FALSE,
            source      VARCHAR(20)     NOT NULL DEFAULT 'ui',
            created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            deleted_at  TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX idx_note_user ON notes(user_id) WHERE deleted_at IS NULL")
    op.execute(
        "CREATE INDEX idx_note_user_pinned ON notes(user_id, pinned) WHERE deleted_at IS NULL"
    )
    op.execute("CREATE INDEX idx_note_title_trgm ON notes USING gin (title gin_trgm_ops)")
    op.execute("""
        CREATE TRIGGER trg_note_updated_at BEFORE UPDATE ON notes
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notes")
