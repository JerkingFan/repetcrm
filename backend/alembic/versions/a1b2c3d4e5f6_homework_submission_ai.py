"""Homework submission AI review fields."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "homework_submissions",
        sa.Column("ai_review_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column(
        "homework_submissions",
        sa.Column("ai_verdict", sa.String(30), nullable=False, server_default=""),
    )
    op.add_column("homework_submissions", sa.Column("ai_score", sa.Integer(), nullable=True))
    op.add_column(
        "homework_submissions",
        sa.Column("ai_feedback", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "homework_submissions",
        sa.Column("ai_review_error", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column("homework_submissions", sa.Column("ai_reviewed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("homework_submissions", "ai_reviewed_at")
    op.drop_column("homework_submissions", "ai_review_error")
    op.drop_column("homework_submissions", "ai_feedback")
    op.drop_column("homework_submissions", "ai_score")
    op.drop_column("homework_submissions", "ai_verdict")
    op.drop_column("homework_submissions", "ai_review_status")
