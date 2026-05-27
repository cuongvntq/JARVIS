"""Create core tables: users, conversations, messages, auth_sessions.

Revision ID: 002_create_core_tables
Revises: 001_init_extensions
Create Date: 2026-05-26 00:00:00
"""

from alembic import op

revision = "002_create_core_tables"
down_revision = "001_init_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ENUM for message role
    op.execute("CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system', 'tool')")

    # users
    op.execute("""
        CREATE TABLE users (
            id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
            email           VARCHAR(255)    NOT NULL UNIQUE,
            password_hash   VARCHAR(255),
            google_sub      VARCHAR(255)    UNIQUE,
            name            VARCHAR(100)    NOT NULL,
            avatar_url      TEXT,
            timezone        VARCHAR(64)     NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
            locale          VARCHAR(10)     NOT NULL DEFAULT 'vi-VN',
            assistant_name  VARCHAR(50)     NOT NULL DEFAULT 'JARVIS',
            is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
            last_login_at   TIMESTAMPTZ,
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_auth CHECK (password_hash IS NOT NULL OR google_sub IS NOT NULL)
        )
    """)
    op.execute("CREATE INDEX idx_users_email ON users(email) WHERE is_active = TRUE")
    op.execute("""
        CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    # conversations
    op.execute("""
        CREATE TABLE conversations (
            id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title           VARCHAR(255)    NOT NULL DEFAULT 'Cuộc hội thoại mới',
            last_message_at TIMESTAMPTZ,
            message_count   INTEGER         NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            deleted_at      TIMESTAMPTZ
        )
    """)
    op.execute("""
        CREATE INDEX idx_conv_user_active
            ON conversations(user_id, last_message_at DESC)
            WHERE deleted_at IS NULL
    """)
    op.execute("""
        CREATE TRIGGER trg_conv_updated_at BEFORE UPDATE ON conversations
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    # messages
    op.execute("""
        CREATE TABLE messages (
            id                UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
            conversation_id   UUID            NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            user_id           UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role              message_role    NOT NULL,
            content           TEXT            NOT NULL,
            metadata          JSONB           NOT NULL DEFAULT '{}'::jsonb,
            tokens_in         INTEGER         NOT NULL DEFAULT 0,
            tokens_out        INTEGER         NOT NULL DEFAULT 0,
            created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_msg_conv_created ON messages(conversation_id, created_at)")
    op.execute("CREATE INDEX idx_msg_user_created ON messages(user_id, created_at DESC)")

    # auth_sessions
    op.execute("""
        CREATE TABLE auth_sessions (
            id                  UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id             UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            refresh_token_hash  VARCHAR(255)    NOT NULL UNIQUE,
            user_agent          TEXT,
            ip_address          VARCHAR(45),
            expires_at          TIMESTAMPTZ     NOT NULL,
            revoked_at          TIMESTAMPTZ,
            created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            last_used_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX idx_session_user_active ON auth_sessions(user_id) WHERE revoked_at IS NULL"
    )
    op.execute("CREATE INDEX idx_session_token ON auth_sessions(refresh_token_hash)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth_sessions")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS conversations")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TYPE IF EXISTS message_role")
