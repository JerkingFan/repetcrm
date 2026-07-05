"""Student portal, lesson packages, homework submissions."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("portal_token", sa.String(64), nullable=True))
    op.add_column("students", sa.Column("balance", sa.Float(), nullable=False, server_default="0"))
    op.create_index("ix_students_portal_token", "students", ["portal_token"], unique=True)

    op.create_table(
        "lesson_packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tutor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("lessons_total", sa.Integer(), nullable=False),
        sa.Column("lessons_remaining", sa.Integer(), nullable=False),
        sa.Column("price_per_lesson", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_lesson_packages_student_id", "lesson_packages", ["student_id"])

    op.add_column("lessons", sa.Column("package_id", sa.Integer(), nullable=True))
    op.create_index("ix_lessons_package_id", "lessons", ["package_id"])

    op.create_table(
        "homework_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("homework_id", sa.Integer(), sa.ForeignKey("homeworks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_homework_submissions_homework_id", "homework_submissions", ["homework_id"])


def downgrade() -> None:
    op.drop_index("ix_homework_submissions_homework_id", table_name="homework_submissions")
    op.drop_table("homework_submissions")
    op.drop_index("ix_lessons_package_id", table_name="lessons")
    op.drop_column("lessons", "package_id")
    op.drop_index("ix_lesson_packages_student_id", table_name="lesson_packages")
    op.drop_table("lesson_packages")
    op.drop_index("ix_students_portal_token", table_name="students")
    op.drop_column("students", "balance")
    op.drop_column("students", "portal_token")
