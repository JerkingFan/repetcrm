"""Public trial lesson booking."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("booking_slug", sa.String(64), nullable=True))
    op.add_column(
        "users",
        sa.Column("booking_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("booking_hours", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "users",
        sa.Column("booking_reply_text", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_users_booking_slug", "users", ["booking_slug"], unique=True)

    op.create_table(
        "trial_bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_time", sa.String(5), nullable=False, server_default="10:00"),
        sa.Column("parent_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trial_bookings_tutor_id", "trial_bookings", ["tutor_id"])
    op.create_index("ix_trial_bookings_student_id", "trial_bookings", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_trial_bookings_student_id", table_name="trial_bookings")
    op.drop_index("ix_trial_bookings_tutor_id", table_name="trial_bookings")
    op.drop_table("trial_bookings")
    op.drop_index("ix_users_booking_slug", table_name="users")
    op.drop_column("users", "booking_reply_text")
    op.drop_column("users", "booking_hours")
    op.drop_column("users", "booking_enabled")
    op.drop_column("users", "booking_slug")
