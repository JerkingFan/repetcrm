"""Parent contact fields and parent portal token."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, None] = "b9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _split_parent_contact(raw: str) -> tuple[str, str]:
    value = (raw or "").strip()
    if not value:
        return "", ""
    if "@" in value:
        return value, ""
    return "", value


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("parent_name", sa.String(255), nullable=False, server_default=""),
    )
    op.add_column(
        "students",
        sa.Column("parent_email", sa.String(255), nullable=False, server_default=""),
    )
    op.add_column(
        "students",
        sa.Column("parent_phone", sa.String(64), nullable=False, server_default=""),
    )
    op.add_column(
        "students",
        sa.Column("parent_notify_email", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("students", sa.Column("parent_portal_token", sa.String(64), nullable=True))
    op.create_index(
        "ix_students_parent_portal_token",
        "students",
        ["parent_portal_token"],
        unique=True,
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, parent_contact FROM students WHERE parent_contact IS NOT NULL AND parent_contact != ''")
    ).fetchall()
    for row in rows:
        email, phone = _split_parent_contact(row.parent_contact)
        conn.execute(
            sa.text(
                "UPDATE students SET parent_email = :email, parent_phone = :phone WHERE id = :id"
            ),
            {"email": email, "phone": phone, "id": row.id},
        )


def downgrade() -> None:
    op.drop_index("ix_students_parent_portal_token", table_name="students")
    op.drop_column("students", "parent_portal_token")
    op.drop_column("students", "parent_notify_email")
    op.drop_column("students", "parent_phone")
    op.drop_column("students", "parent_email")
    op.drop_column("students", "parent_name")
