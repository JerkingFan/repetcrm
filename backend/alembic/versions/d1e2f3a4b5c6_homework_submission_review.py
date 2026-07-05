"""Homework submission review fields."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "homework_submissions",
        sa.Column("status", sa.String(20), nullable=False, server_default="submitted"),
    )
    op.add_column(
        "homework_submissions",
        sa.Column("tutor_comment", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "homework_submissions",
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("homework_submissions", "reviewed_at")
    op.drop_column("homework_submissions", "tutor_comment")
    op.drop_column("homework_submissions", "status")
