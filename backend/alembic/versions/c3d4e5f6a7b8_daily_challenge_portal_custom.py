"""Daily challenges + student portal customization."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    cols = _existing_columns("students")
    if "portal_nickname" not in cols:
        op.add_column(
            "students",
            sa.Column("portal_nickname", sa.String(64), nullable=False, server_default=""),
        )
    if "portal_theme" not in cols:
        op.add_column(
            "students",
            sa.Column("portal_theme", sa.String(32), nullable=False, server_default="ocean"),
        )
    if "portal_avatar" not in cols:
        op.add_column(
            "students",
            sa.Column("portal_avatar", sa.String(32), nullable=False, server_default="rocket"),
        )

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("student_daily_challenges"):
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
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("student_daily_challenges"):
        op.drop_table("student_daily_challenges")
    cols = _existing_columns("students")
    if "portal_avatar" in cols:
        op.drop_column("students", "portal_avatar")
    if "portal_theme" in cols:
        op.drop_column("students", "portal_theme")
    if "portal_nickname" in cols:
        op.drop_column("students", "portal_nickname")
