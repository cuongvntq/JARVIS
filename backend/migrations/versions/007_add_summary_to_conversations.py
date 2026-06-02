"""Add summary column to conversations table.

Revision ID: 007_add_summary_to_conversations
Revises: 006_sprint5_reminders
Create Date: 2026-06-02 00:00:00
"""

from alembic import op

revision = "007_add_summary_to_conversations"
down_revision = "006_sprint5_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS summary TEXT DEFAULT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS summary")
