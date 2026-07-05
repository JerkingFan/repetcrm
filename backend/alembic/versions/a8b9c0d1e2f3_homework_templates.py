"""Homework templates for reuse."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "homework_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tutor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("subject", sa.String(255), nullable=False, server_default=""),
        sa.Column("homework_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("homework_prefs", sa.Text(), nullable=False, server_default=""),
        sa.Column("checklist_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_lesson_id", sa.Integer(), sa.ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_homework_templates_tutor_id", "homework_templates", ["tutor_id"])


def downgrade() -> None:
    op.drop_index("ix_homework_templates_tutor_id", table_name="homework_templates")
    op.drop_table("homework_templates")
