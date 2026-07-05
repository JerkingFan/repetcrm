"""Persist debounced board snapshots and prune old rows."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import BoardSnapshot

logger = logging.getLogger(__name__)


def save_board_snapshot(db: Session, board_id: int, state_json: str) -> None:
    keep = max(1, get_settings().board_snapshot_keep)
    db.add(BoardSnapshot(board_id=board_id, state_json=state_json))
    db.flush()

    stale_ids = (
        db.query(BoardSnapshot.id)
        .filter(BoardSnapshot.board_id == board_id)
        .order_by(BoardSnapshot.created_at.desc(), BoardSnapshot.id.desc())
        .offset(keep)
        .all()
    )
    if not stale_ids:
        return
    ids = [row[0] for row in stale_ids]
    db.query(BoardSnapshot).filter(BoardSnapshot.id.in_(ids)).delete(synchronize_session=False)
    logger.debug("pruned %s old snapshot(s) for board %s", len(ids), board_id)
