"""Create Sprint 2 tables: todos, tool_execution_logs, llm_call_logs + ENUM types.

Revision ID: 003_sprint2_todos_tool_logs
Revises: 002_create_core_tables
Create Date: 2026-05-28 00:00:00
"""

from alembic import op

revision = "003_sprint2_todos_tool_logs"
down_revision = "002_create_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ENUM types
    op.execute("CREATE TYPE todo_status   AS ENUM ('pending', 'in_progress', 'completed', 'cancelled')")
    op.execute("CREATE TYPE todo_priority AS ENUM ('low', 'medium', 'high', 'urgent')")
    op.execute("CREATE TYPE tool_status   AS ENUM ('success', 'failed', 'timeout')")

    # todos
    op.execute("""
        CREATE TABLE todos (
            id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title           VARCHAR(500)    NOT NULL,
            description     TEXT,
            status          todo_status     NOT NULL DEFAULT 'pending',
            priority        todo_priority   NOT NULL DEFAULT 'medium',
            due_at          TIMESTAMPTZ,
            completed_at    TIMESTAMPTZ,
            tags            TEXT[]          NOT NULL DEFAULT '{}',
            source          VARCHAR(20)     NOT NULL DEFAULT 'ui',
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            deleted_at      TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX idx_todo_user_status ON todos(user_id, status) WHERE deleted_at IS NULL"
    )
    op.execute("""
        CREATE INDEX idx_todo_user_due
            ON todos(user_id, due_at)
            WHERE deleted_at IS NULL AND status != 'completed'
    """)
    op.execute("CREATE INDEX idx_todo_title_trgm ON todos USING gin (title gin_trgm_ops)")
    op.execute("""
        CREATE TRIGGER trg_todo_updated_at BEFORE UPDATE ON todos
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    # tool_execution_logs
    op.execute("""
        CREATE TABLE tool_execution_logs (
            id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message_id      UUID            REFERENCES messages(id) ON DELETE SET NULL,
            tool_name       VARCHAR(64)     NOT NULL,
            input           JSONB           NOT NULL,
            output          JSONB,
            status          tool_status     NOT NULL,
            error_message   TEXT,
            duration_ms     INTEGER         NOT NULL,
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX idx_tool_log_user_time ON tool_execution_logs(user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_tool_log_tool_status ON tool_execution_logs(tool_name, status, created_at DESC)"
    )

    # llm_call_logs
    op.execute("""
        CREATE TABLE llm_call_logs (
            id               UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id          UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message_id       UUID          REFERENCES messages(id) ON DELETE SET NULL,
            intent           VARCHAR(32)   NOT NULL,
            classify_source  VARCHAR(16)   NOT NULL,
            model_used       VARCHAR(64)   NOT NULL,
            tokens_in        INTEGER       NOT NULL,
            tokens_out       INTEGER       NOT NULL,
            cost_usd         NUMERIC(10,6) NOT NULL,
            duration_ms      INTEGER       NOT NULL,
            success          BOOLEAN       NOT NULL,
            error_code       VARCHAR(64),
            created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX idx_llm_log_user_created ON llm_call_logs(user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_llm_log_model ON llm_call_logs(model_used, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_call_logs")
    op.execute("DROP TABLE IF EXISTS tool_execution_logs")
    op.execute("DROP TABLE IF EXISTS todos")
    op.execute("DROP TYPE IF EXISTS tool_status")
    op.execute("DROP TYPE IF EXISTS todo_priority")
    op.execute("DROP TYPE IF EXISTS todo_status")
