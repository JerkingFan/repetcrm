"""Payments, analytics fields, prompt marketplace."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("first_lesson_at", sa.Date(), nullable=True))
    op.add_column("students", sa.Column("last_lesson_at", sa.Date(), nullable=True))
    op.add_column(
        "students",
        sa.Column("student_status", sa.String(20), nullable=False, server_default="active"),
    )

    op.add_column("lessons", sa.Column("paid_at", sa.DateTime(), nullable=True))
    op.add_column("lessons", sa.Column("payment_source", sa.String(30), nullable=True))

    op.create_table(
        "payment_intents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tutor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BYN"),
        sa.Column("purpose", sa.String(30), nullable=False, server_default="balance_topup"),
        sa.Column("purpose_ref_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("public_token", sa.String(64), nullable=False),
        sa.Column("external_order_id", sa.String(128), nullable=True),
        sa.Column("erip_code", sa.String(32), nullable=True),
        sa.Column("payment_url", sa.String(512), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_payment_intents_public_token", "payment_intents", ["public_token"], unique=True)
    op.create_index("ix_payment_intents_tutor_id", "payment_intents", ["tutor_id"])
    op.create_index("ix_payment_intents_student_id", "payment_intents", ["student_id"])

    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("intent_id", sa.Integer(), sa.ForeignKey("payment_intents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tutor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BYN"),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="paid"),
        sa.Column("raw_payload", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_payment_transactions_external", "payment_transactions", ["provider", "external_id"], unique=True)

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("subject", sa.String(255), nullable=False, server_default=""),
        sa.Column("grade", sa.String(50), nullable=False, server_default=""),
        sa.Column("homework_prefs", sa.Text(), nullable=False, server_default=""),
        sa.Column("checklist_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("sample_homework_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="public"),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_prompt_templates_subject", "prompt_templates", ["subject"])
    op.create_index("ix_prompt_templates_grade", "prompt_templates", ["grade"])

    op.create_table(
        "prompt_template_installs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tutor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("prompt_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("homework_template_id", sa.Integer(), sa.ForeignKey("homework_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("installed_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index(
        "ix_prompt_installs_tutor_template",
        "prompt_template_installs",
        ["tutor_id", "template_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_prompt_installs_tutor_template", table_name="prompt_template_installs")
    op.drop_table("prompt_template_installs")
    op.drop_index("ix_prompt_templates_grade", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_subject", table_name="prompt_templates")
    op.drop_table("prompt_templates")
    op.drop_index("ix_payment_transactions_external", table_name="payment_transactions")
    op.drop_table("payment_transactions")
    op.drop_index("ix_payment_intents_student_id", table_name="payment_intents")
    op.drop_index("ix_payment_intents_tutor_id", table_name="payment_intents")
    op.drop_index("ix_payment_intents_public_token", table_name="payment_intents")
    op.drop_table("payment_intents")
    op.drop_column("lessons", "payment_source")
    op.drop_column("lessons", "paid_at")
    op.drop_column("students", "student_status")
    op.drop_column("students", "last_lesson_at")
    op.drop_column("students", "first_lesson_at")
