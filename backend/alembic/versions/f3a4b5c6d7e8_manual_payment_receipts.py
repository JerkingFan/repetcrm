"""Manual payment receipts: parent uploads proof, tutor confirms."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("payment_details", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "payment_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("file_path", sa.String(512), nullable=False, server_default=""),
        sa.Column("original_filename", sa.String(255), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(80), nullable=False, server_default=""),
        sa.Column("parent_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("tutor_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_receipts_tutor_id", "payment_receipts", ["tutor_id"])
    op.create_index("ix_payment_receipts_student_id", "payment_receipts", ["student_id"])
    op.create_index("ix_payment_receipts_status", "payment_receipts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_payment_receipts_status", table_name="payment_receipts")
    op.drop_index("ix_payment_receipts_student_id", table_name="payment_receipts")
    op.drop_index("ix_payment_receipts_tutor_id", table_name="payment_receipts")
    op.drop_table("payment_receipts")
    op.drop_column("users", "payment_details")
