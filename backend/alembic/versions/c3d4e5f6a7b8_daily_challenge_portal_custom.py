"""Daily challenges + student portal customization."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("portal_nickname", sa.String(64), nullable=False, server_default=""))
    op.add_column("students", sa.Column("portal_theme", sa.String(32), nullable=False, server_default="ocean"))
    op.add_column("students", sa.Column("portal_avatar", sa.String(32), nullable=False, server_default="rocket"))
    op.create_table(
        "student_daily_challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("challenge_date", sa.Date(), nullable=False, index=True),
        sa.Column("question", sa.Text(), nullable=False, server_default=""),
        sa.Column("topic", sa.String(255), nullable=False, server_default=""),
        sa.Column("difficulty", sa.String(20), nullable=False, server_default="easy"),
        sa.Column("expected_hint", sa.Text(), nullable=False, server_default=""),
        sa.Column("answer_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("ai_verdict", sa.String(30), nullable=False, server_default=""),
        sa.Column("ai_score", sa.Integer(), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("student_id", "challenge_date", name="uq_daily_challenge_student_date"),
    )


def downgrade() -> None:
    op.drop_table("student_daily_challenges")
    op.drop_column("students", "portal_avatar")
    op.drop_column("students", "portal_theme")
    op.drop_column("students", "portal_nickname")
