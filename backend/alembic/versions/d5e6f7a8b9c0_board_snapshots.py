"""board_snapshots table for point-in-time recovery."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "board_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("board_id", sa.Integer(), sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_board_snapshots_board_id", "board_snapshots", ["board_id"])
    op.create_index("ix_board_snapshots_created_at", "board_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_board_snapshots_created_at", table_name="board_snapshots")
    op.drop_index("ix_board_snapshots_board_id", table_name="board_snapshots")
    op.drop_table("board_snapshots")
