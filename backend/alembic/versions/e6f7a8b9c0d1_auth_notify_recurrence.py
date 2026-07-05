"""Auth reset, notifications, recurring lessons."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_chat_id", sa.String(64), nullable=False, server_default=""))
    op.add_column("users", sa.Column("notify_email", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("notify_telegram", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        "users", sa.Column("notify_lesson_tomorrow", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.add_column("users", sa.Column("notify_unpaid", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column(
        "users", sa.Column("notify_homework_ready", sa.Boolean(), nullable=False, server_default=sa.true())
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("ref_key", sa.String(120), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_notification_log_ref_key", "notification_log", ["ref_key"], unique=True)
    op.create_index("ix_notification_log_user_id", "notification_log", ["user_id"])

    op.create_table(
        "lesson_series",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tutor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("lesson_time", sa.String(5), nullable=False, server_default="10:00"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("payment_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("until_date", sa.Date(), nullable=True),
        sa.Column("weeks_ahead", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("last_generated_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_lesson_series_tutor_id", "lesson_series", ["tutor_id"])

    # SQLite cannot add a column with inline FK — add column first, index only
    op.add_column("lessons", sa.Column("series_id", sa.Integer(), nullable=True))
    op.create_index("ix_lessons_series_id", "lessons", ["series_id"])


def downgrade() -> None:
    op.drop_index("ix_lessons_series_id", table_name="lessons")
    op.drop_column("lessons", "series_id")
    op.drop_index("ix_lesson_series_tutor_id", table_name="lesson_series")
    op.drop_table("lesson_series")
    op.drop_index("ix_notification_log_user_id", table_name="notification_log")
    op.drop_index("ix_notification_log_ref_key", table_name="notification_log")
    op.drop_table("notification_log")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    for col in (
        "notify_homework_ready",
        "notify_unpaid",
        "notify_lesson_tomorrow",
        "notify_telegram",
        "notify_email",
        "telegram_chat_id",
    ):
        op.drop_column("users", col)
