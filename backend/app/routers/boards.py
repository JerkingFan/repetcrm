import json
import logging
import os
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.dependencies import get_current_user
from app.models import Board, BoardSnapshot, User
from app.schemas import BoardSnapshotOut
from app.services.board_realtime import (
    connection_manager,
    room_store,
    setup_board_bus,
    shutdown_board_bus,
)
from app.services.board_state import board_to_dict, compact_state, is_persisted_write_op, load_state

router = APIRouter(prefix="/boards", tags=["boards"])
logger = logging.getLogger(__name__)


def _require_share_write(b: Board) -> None:
    if not b.share_writable:
        raise HTTPException(
            status_code=403,
            detail="Guest write is disabled for this board. Owner can enable collaboration.",
        )


def _new_share_token() -> str:
    return secrets.token_urlsafe(24)


def _get_board_for_owner(db: Session, board_id: int, user_id: int) -> Board:
    b = db.query(Board).filter(Board.id == board_id, Board.owner_id == user_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Board not found")
    return b


def _allow_board_access(
    db: Session,
    board_id: int,
    *,
    user: User | None = None,
    share_token: str | None = None,
) -> Board:
    if user is not None:
        return _get_board_for_owner(db, board_id, user.id)
    if not share_token:
        raise HTTPException(status_code=401, detail="Missing token")
    b = db.query(Board).filter(Board.id == board_id, Board.share_token == share_token).first()
    if not b:
        raise HTTPException(status_code=404, detail="Board not found")
    return b


@router.get("")
def list_boards(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    boards = (
        db.query(Board)
        .filter(Board.owner_id == user.id)
        .order_by(Board.updated_at.desc(), Board.id.desc())
        .all()
    )
    return [board_to_dict(b) for b in boards]


@router.post("")
def create_board(payload: dict[str, Any] | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    title = ""
    if payload and isinstance(payload.get("title"), str):
        title = payload["title"].strip()
    b = Board(
        owner_id=user.id,
        title=title or "Виртуальная доска",
        share_token=_new_share_token(),
        share_writable=False,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return board_to_dict(b)


@router.get("/{board_id}")
def get_board(board_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = _get_board_for_owner(db, board_id, user.id)
    return board_to_dict(b)


@router.get("/{board_id}/snapshots", response_model=list[BoardSnapshotOut])
def list_board_snapshots(
    board_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_board_for_owner(db, board_id, user.id)
    rows = (
        db.query(BoardSnapshot)
        .filter(BoardSnapshot.board_id == board_id)
        .order_by(BoardSnapshot.created_at.desc(), BoardSnapshot.id.desc())
        .limit(50)
        .all()
    )
    return [BoardSnapshotOut(id=r.id, created_at=r.created_at) for r in rows]


@router.post("/{board_id}/snapshots/{snapshot_id}/restore")
def restore_board_snapshot(
    board_id: int,
    snapshot_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    b = _get_board_for_owner(db, board_id, user.id)
    snap = (
        db.query(BoardSnapshot)
        .filter(BoardSnapshot.id == snapshot_id, BoardSnapshot.board_id == board_id)
        .first()
    )
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    b.state_json = snap.state_json
    b.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(b)
    return board_to_dict(b)


@router.get("/{board_id}/public")
def get_board_public(board_id: int, token: str, db: Session = Depends(get_db)):
    b = _allow_board_access(db, board_id, share_token=token)
    return board_to_dict(b)


@router.put("/{board_id}")
def update_board(board_id: int, payload: dict[str, Any], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = _get_board_for_owner(db, board_id, user.id)
    if isinstance(payload.get("title"), str):
        b.title = payload["title"].strip() or b.title
    if "share_writable" in payload and isinstance(payload.get("share_writable"), bool):
        b.share_writable = payload["share_writable"]
    if payload.get("state_json") is not None:
        state = payload["state_json"]
        if isinstance(state, dict):
            compact_state(state)
            room_store.replace(board_id, state)
            b.state_json = json.dumps(state, ensure_ascii=False)
        else:
            b.state_json = json.dumps(state, ensure_ascii=False)
        b.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(b)
    return board_to_dict(b)


@router.put("/{board_id}/public")
def update_board_public(board_id: int, token: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    b = _allow_board_access(db, board_id, share_token=token)
    _require_share_write(b)
    if payload.get("state_json") is not None:
        state = payload["state_json"]
        if isinstance(state, dict):
            compact_state(state)
            room_store.replace(board_id, state)
            b.state_json = json.dumps(state, ensure_ascii=False)
        else:
            b.state_json = json.dumps(state, ensure_ascii=False)
        b.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(b)
    return board_to_dict(b)


@router.post("/{board_id}/assets")
async def upload_board_asset(
    board_id: int,
    file: UploadFile,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    b = _allow_board_access(db, board_id, share_token=token)
    _require_share_write(b)

    media_root = os.environ.get("MEDIA_DIR") or "./media"
    board_dir = os.path.join(media_root, "boards", str(b.id))
    os.makedirs(board_dir, exist_ok=True)

    cfg = get_settings()
    max_bytes = int(cfg.board_asset_max_bytes)
    ctype = (file.content_type or "").lower()
    if not ctype.startswith("image/"):
        raise HTTPException(status_code=415, detail="Only image uploads are supported")

    name = file.filename or "image"
    ext = ""
    if "." in name:
        ext = "." + name.split(".")[-1].lower()
        if len(ext) > 10:
            ext = ""
    fname = f"{secrets.token_hex(12)}{ext}"
    path = os.path.join(board_dir, fname)

    total = 0
    try:
        with open(path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail="File too large")
                f.write(chunk)
    except HTTPException:
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
        raise

    url_path = f"/api/media/boards/{b.id}/{fname}"
    return JSONResponse({"url": url_path})


@router.websocket("/ws/{board_id}")
async def board_ws(ws: WebSocket, board_id: int):
    cfg = get_settings()

    # Prefer cookie/header auth over query params so access logs don't contain auth tokens.
    auth_header = (ws.headers.get("authorization") or "").strip()
    auth_cookie = ws.cookies.get(cfg.access_cookie_name)
    auth = auth_header or auth_cookie

    # Legacy support (will be removed): JWT in query string.
    auth_legacy = ws.query_params.get("auth")
    if not auth and auth_legacy:
        logger.warning(
            "WS legacy auth in query string used (board_id=%s)",
            board_id,
            extra={"legacy_auth": True},
        )
        auth = auth_legacy

    guest_token_cookie = ws.cookies.get(cfg.board_share_cookie_name)
    guest_token_query = ws.query_params.get("token")
    guest_token = guest_token_cookie or guest_token_query
    guest_via_token = guest_token is not None and not auth

    db = SessionLocal()
    try:
        b: Board | None = None
        if guest_via_token:
            if guest_token_query and not guest_token_cookie:
                logger.warning(
                    "WS legacy guest token in query string used (board_id=%s)",
                    board_id,
                    extra={"legacy_guest_token": True},
                )
            b = db.query(Board).filter(Board.id == board_id, Board.share_token == guest_token).first()
        elif auth:
            from app.auth import decode_token

            payload = decode_token(auth)
            if not payload or "sub" not in payload:
                await ws.close(code=4401)
                return
            user_id = int(payload["sub"])
            b = db.query(Board).filter(Board.id == board_id, Board.owner_id == user_id).first()
        else:
            await ws.close(code=4401)
            return
        if not b:
            await ws.close(code=4404)
            return

        await connection_manager.connect(board_id, ws)

        initial = load_state(b)
        state = room_store.ensure_loaded(board_id, initial)
        await ws.send_json({"type": "state", "state": state})

        while True:
            msg = await ws.receive_json()
            if not isinstance(msg, dict):
                continue
            if msg.get("type") == "op" and isinstance(msg.get("op"), dict):
                op = msg["op"]
                if guest_via_token and not b.share_writable and is_persisted_write_op(op):
                    await ws.send_json(
                        {
                            "type": "error",
                            "code": "read_only",
                            "detail": "Guest write is disabled for this board",
                        }
                    )
                    continue
                await connection_manager.publish_op(board_id, op, exclude=ws)
            elif msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(board_id, ws)
        try:
            db.close()
        except Exception:
            pass
