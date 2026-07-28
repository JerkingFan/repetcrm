"""Student portal v2: meeting URL, HW due date, tutor contact, reschedule."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lessons", sa.Column("meeting_url", sa.String(500), nullable=False, server_default=""))
    op.add_column("homeworks", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("contact_telegram", sa.String(64), nullable=False, server_default=""))
    op.add_column("users", sa.Column("contact_url", sa.String(500), nullable=False, server_default=""))
    op.add_column(
        "users",
        sa.Column("hide_balance_in_portal", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "lesson_reschedule_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tutor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("preferred_date", sa.Date(), nullable=True),
        sa.Column("preferred_time", sa.String(5), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("tutor_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("lesson_reschedule_requests")
    op.drop_column("users", "hide_balance_in_portal")
    op.drop_column("users", "contact_url")
    op.drop_column("users", "contact_telegram")
    op.drop_column("homeworks", "due_date")
    op.drop_column("lessons", "meeting_url")
