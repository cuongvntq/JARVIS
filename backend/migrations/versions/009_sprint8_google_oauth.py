"""Sprint 8: create google_oauth_accounts (Calendar OAuth metadata, no tokens)."""

import sqlalchemy as sa
from alembic import op

revision = "009_sprint8_google_oauth"
down_revision = "008_desktop_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_oauth_accounts",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("google_email", sa.String(255), nullable=False),
        sa.Column("scopes", sa.String(), nullable=False),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # unique=True on user_id already creates a unique index for fast lookup by user.


def downgrade() -> None:
    op.drop_table("google_oauth_accounts")
