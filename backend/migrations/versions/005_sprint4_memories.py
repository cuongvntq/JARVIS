"""Create Sprint 4 table: memories.

Revision ID: 005_sprint4_memories
Revises: 004_sprint3_notes
Create Date: 2026-05-31 00:00:00
"""

from alembic import op

revision = "005_sprint4_memories"
down_revision = "004_sprint3_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE memory_type AS ENUM ('fact','preference','rule','relation','goal','other')")
    op.execute("""
        CREATE TABLE memories (
            id           UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id      UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            memory_type  memory_type   NOT NULL DEFAULT 'fact',
            content      TEXT          NOT NULL,
            embedding    vector(1536),
            importance   INTEGER       NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
            is_active    BOOLEAN       NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            deleted_at   TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX idx_memories_user_active ON memories (user_id) "
        "WHERE is_active = TRUE AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_memories_type ON memories (user_id, memory_type) "
        "WHERE is_active = TRUE AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_memories_hnsw ON memories USING hnsw (embedding vector_cosine_ops) "
        "WHERE embedding IS NOT NULL AND deleted_at IS NULL AND is_active = TRUE"
    )
    op.execute("""
        CREATE TRIGGER trg_memory_updated_at BEFORE UPDATE ON memories
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memories")
    op.execute("DROP TYPE IF EXISTS memory_type")
