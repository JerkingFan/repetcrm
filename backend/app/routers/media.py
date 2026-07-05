"""Authenticated media serving (replaces public StaticFiles mount)."""

from __future__ import annotations

import os
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user, get_optional_user
from app.models import Board, Homework, Lesson, User

router = APIRouter(tags=["media"])

_BOARD_FILENAME_RE = re.compile(r"^[a-f0-9]{24}(\.[a-z0-9]{1,10})?$", re.IGNORECASE)


def _media_root() -> str:
    return get_settings().media_dir


def _safe_join(root: str, *parts: str) -> str | None:
    """Resolve path and reject directory traversal."""
    base = os.path.realpath(root)
    target = os.path.realpath(os.path.join(base, *parts))
    if not target.startswith(base + os.sep) and target != base:
        return None
    return target


def _board_access(
    db: Session,
    board_id: int,
    *,
    share_token: str | None,
    user: User | None,
) -> Board | None:
    if user is not None:
        board = db.query(Board).filter(Board.id == board_id, Board.owner_id == user.id).first()
        if board:
            return board
    if share_token:
        return (
            db.query(Board)
            .filter(Board.id == board_id, Board.share_token == share_token.strip())
            .first()
        )
    return None


@router.get("/media/boards/{board_id}/{filename}")
def serve_board_asset(
    board_id: int,
    filename: str,
    token: str | None = Query(None, description="Board share token"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not _BOARD_FILENAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    board = _board_access(db, board_id, share_token=token, user=user)
    if not board:
        raise HTTPException(status_code=401, detail="Unauthorized")

    path = _safe_join(_media_root(), "boards", str(board_id), filename)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path)


@router.get("/media/homework/{homework_id}.pdf")
def serve_homework_pdf_cached(
    homework_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Direct cache access blocked elsewhere; this route requires ownership."""
    hw = (
        db.query(Homework)
        .join(Lesson)
        .filter(Homework.id == homework_id, Lesson.tutor_id == user.id)
        .first()
    )
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")

    path = _safe_join(_media_root(), f"homework_{homework_id}.pdf")
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(path, media_type="application/pdf")
