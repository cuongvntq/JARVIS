"""Sprint 9: create calendar_sync_states and calendar_events (Calendar read cache)."""

import sqlalchemy as sa
from alembic import op

revision = "010_sprint9_calendar_events"
down_revision = "009_sprint8_google_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calendar_sync_states",
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
        ),
        sa.Column("google_calendar_id", sa.String(255), nullable=False),
        sa.Column("calendar_summary", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("time_zone", sa.String(64), nullable=True),
        sa.Column("access_role", sa.String(20), nullable=True),
        sa.Column("sync_token", sa.String(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("horizon_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_full_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "user_id", "google_calendar_id", name="uq_calendar_sync_states_user_calendar"
        ),
    )

    op.create_table(
        "calendar_events",
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
        ),
        sa.Column("google_calendar_id", sa.String(255), nullable=False),
        sa.Column("google_event_id", sa.String(255), nullable=False),
        sa.Column("ical_uid", sa.String(255), nullable=True),
        sa.Column("summary", sa.String(500), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("is_all_day", sa.Boolean(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("event_timezone", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="confirmed"),
        sa.Column("html_link", sa.String(), nullable=True),
        sa.Column("etag", sa.String(), nullable=True),
        sa.Column("google_updated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "user_id",
            "google_calendar_id",
            "google_event_id",
            name="uq_calendar_events_user_calendar_event",
        ),
    )
    op.create_index("ix_calendar_events_user_start_at", "calendar_events", ["user_id", "start_at"])
    op.create_index(
        "ix_calendar_events_user_start_date", "calendar_events", ["user_id", "start_date"]
    )
    op.create_index(
        "ix_calendar_events_user_calendar", "calendar_events", ["user_id", "google_calendar_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_calendar_events_user_calendar", table_name="calendar_events")
    op.drop_index("ix_calendar_events_user_start_date", table_name="calendar_events")
    op.drop_index("ix_calendar_events_user_start_at", table_name="calendar_events")
    op.drop_table("calendar_events")
    op.drop_table("calendar_sync_states")
