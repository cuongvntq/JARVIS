"""Init: enable Postgres extensions.

Revision ID: 001_init_extensions
Revises:
Create Date: 2026-05-18 10:00:00
"""

from alembic import op

revision: str = "001_init_extensions"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable extensions needed for JARVIS."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # Trigger function for auto-updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS set_updated_at() CASCADE")
    # Note: KHÔNG drop extension trong downgrade vì có thể bảng khác đang dùng
