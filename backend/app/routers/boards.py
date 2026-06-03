import json
import os
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user
from app.models import Board, User


router = APIRouter(prefix="/boards", tags=["boards"])


def _new_share_token() -> str:
    # URL-safe, short enough for links, long enough to be unguessable.
    return secrets.token_urlsafe(24)


def _board_to_dict(b: Board) -> dict:
    try:
        state = json.loads(b.state_json or "{}")
        if not isinstance(state, dict):
            state = {}
    except Exception:
        state = {}
    # Normalize state for frontend (arrays must exist).
    state = {
        "version": 1,
        "strokes": state.get("strokes") if isinstance(state.get("strokes"), list) else [],
        "texts": state.get("texts") if isinstance(state.get("texts"), list) else [],
        "images": state.get("images") if isinstance(state.get("images"), list) else [],
    }
    return {
        "id": b.id,
        "owner_id": b.owner_id,
        "title": b.title,
        "share_token": b.share_token,
        "state_json": state,
        "created_at": b.created_at.isoformat() if isinstance(b.created_at, datetime) else str(b.created_at),
        "updated_at": b.updated_at.isoformat() if isinstance(b.updated_at, datetime) else str(b.updated_at),
    }


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
    return [_board_to_dict(b) for b in boards]


@router.post("")
def create_board(payload: dict[str, Any] | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    title = ""
    if payload and isinstance(payload.get("title"), str):
        title = payload["title"].strip()
    b = Board(owner_id=user.id, title=title or "Виртуальная доска", share_token=_new_share_token())
    db.add(b)
    db.commit()
    db.refresh(b)
    return _board_to_dict(b)


@router.get("/{board_id}")
def get_board(board_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = _get_board_for_owner(db, board_id, user.id)
    return _board_to_dict(b)


@router.get("/{board_id}/public")
def get_board_public(board_id: int, token: str, db: Session = Depends(get_db)):
    b = _allow_board_access(db, board_id, share_token=token)
    return _board_to_dict(b)


@router.put("/{board_id}")
def update_board(board_id: int, payload: dict[str, Any], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = _get_board_for_owner(db, board_id, user.id)
    if isinstance(payload.get("title"), str):
        b.title = payload["title"].strip() or b.title
    if payload.get("state_json") is not None:
        # state_json is stored as JSON string
        b.state_json = json.dumps(payload["state_json"], ensure_ascii=False)
    db.commit()
    db.refresh(b)
    return _board_to_dict(b)


@router.put("/{board_id}/public")
def update_board_public(board_id: int, token: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    b = _allow_board_access(db, board_id, share_token=token)
    if payload.get("state_json") is not None:
        b.state_json = json.dumps(payload["state_json"], ensure_ascii=False)
    db.commit()
    db.refresh(b)
    return _board_to_dict(b)


@router.post("/{board_id}/assets")
async def upload_board_asset(
    board_id: int,
    file: UploadFile,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    # MVP: загрузка картинок доступна только по share token
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    b = _allow_board_access(db, board_id, share_token=token)

    media_root = os.environ.get("MEDIA_DIR") or "./media"
    board_dir = os.path.join(media_root, "boards", str(b.id))
    os.makedirs(board_dir, exist_ok=True)

    # Keep extension if present
    name = file.filename or "image"
    ext = ""
    if "." in name:
        ext = "." + name.split(".")[-1].lower()
        if len(ext) > 10:
            ext = ""
    fname = f"{secrets.token_hex(12)}{ext}"
    path = os.path.join(board_dir, fname)

    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)

    # Serve via backend StaticFiles mount. In production behind nginx,
    # frontend calls API through /api, so return an /api/media/... path.
    url_path = f"/api/media/boards/{b.id}/{fname}"
    return JSONResponse({"url": url_path})


class _BoardConnectionManager:
    def __init__(self):
        self._rooms: dict[int, set[WebSocket]] = {}

    async def connect(self, board_id: int, ws: WebSocket):
        await ws.accept()
        self._rooms.setdefault(board_id, set()).add(ws)

    def disconnect(self, board_id: int, ws: WebSocket):
        room = self._rooms.get(board_id)
        if not room:
            return
        room.discard(ws)
        if not room:
            self._rooms.pop(board_id, None)

    async def broadcast(self, board_id: int, message: dict, *, exclude: WebSocket | None = None):
        room = list(self._rooms.get(board_id, set()))
        for ws in room:
            if exclude is not None and ws is exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                # drop silently; client will reconnect
                self.disconnect(board_id, ws)


_manager = _BoardConnectionManager()

def _load_state(b: Board) -> dict:
    try:
        state = json.loads(b.state_json or "{}")
        if not isinstance(state, dict):
            state = {}
    except Exception:
        state = {}
    return {
        "version": 1,
        "strokes": state.get("strokes") if isinstance(state.get("strokes"), list) else [],
        "texts": state.get("texts") if isinstance(state.get("texts"), list) else [],
        "images": state.get("images") if isinstance(state.get("images"), list) else [],
    }


def _apply_op(state: dict, op: dict) -> dict:
    t = op.get("op")
    # presence ops are ephemeral; caller should not persist them
    if t in ("cursor", "cursor_leave"):
        return state
    if t == "clear":
        return {"version": 1, "strokes": [], "texts": [], "images": []}

    if t == "stroke_begin":
        sid = op.get("id")
        if not isinstance(sid, str) or not sid:
            return state
        color = op.get("color") if isinstance(op.get("color"), str) else "#1E3A8A"
        width = op.get("width") if isinstance(op.get("width"), (int, float)) else 3
        p = op.get("p")
        if not isinstance(p, dict) or "x" not in p or "y" not in p:
            return state
        state["strokes"].append({"id": sid, "color": color, "width": width, "points": [p]})
        return state

    if t == "stroke_point":
        sid = op.get("id")
        p = op.get("p")
        if not isinstance(sid, str) or not isinstance(p, dict):
            return state
        for st in reversed(state["strokes"]):
            if st.get("id") == sid and isinstance(st.get("points"), list):
                st["points"].append(p)
                break
        return state

    if t == "text_add":
        item = op.get("item")
        if isinstance(item, dict):
            state["texts"].append(item)
        return state

    if t == "image_add":
        item = op.get("item")
        if isinstance(item, dict):
            state["images"].append(item)
        return state

    if t == "image_move":
        iid = op.get("id")
        x = op.get("x")
        y = op.get("y")
        if not isinstance(iid, str) or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return state
        for it in state.get("images", []):
            if isinstance(it, dict) and it.get("id") == iid:
                it["x"] = x
                it["y"] = y
                break
        return state

    if t == "erase":
        p = op.get("p")
        r = op.get("r")
        if not isinstance(p, dict) or not isinstance(r, (int, float)):
            return state
        px = p.get("x")
        py = p.get("y")
        if not isinstance(px, (int, float)) or not isinstance(py, (int, float)):
            return state
        r2 = float(r) * float(r)
        strokes = []
        for st in state.get("strokes", []):
            if not isinstance(st, dict):
                continue
            pts = st.get("points")
            if not isinstance(pts, list):
                continue
            hit = False
            for pt in pts:
                if not isinstance(pt, dict):
                    continue
                x = pt.get("x")
                y = pt.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    dx = float(x) - float(px)
                    dy = float(y) - float(py)
                    if dx * dx + dy * dy <= r2:
                        hit = True
                        break
            if not hit:
                strokes.append(st)
        state["strokes"] = strokes
        return state

    return state


@router.websocket("/ws/{board_id}")
async def board_ws(ws: WebSocket, board_id: int):
    """
    Realtime sync for a board.
    Query params:
      - token: share_token for guest access
      - auth: JWT access token for owner access (optional; not required if token is present)
    Messages:
      - client -> server: {type: "op", op: {...}}
      - server -> client: {type: "op", op: {...}} (broadcast)
      - server -> client: {type: "state", state: {...}} (initial snapshot)
    """
    token = ws.query_params.get("token")
    auth = ws.query_params.get("auth")

    db = SessionLocal()
    try:
        b: Board | None = None
        if token:
            b = db.query(Board).filter(Board.id == board_id, Board.share_token == token).first()
        elif auth:
            # validate JWT by reusing decode logic via dependencies module
            from app.auth import decode_token

            payload = decode_token(auth)
            if not payload or "sub" not in payload:
                await ws.close(code=4401)
                return
            user_id = int(payload["sub"])
            b = db.query(Board).filter(Board.id == board_id, Board.owner_id == user_id).first()
        if not b:
            await ws.close(code=4404)
            return

        await _manager.connect(board_id, ws)

        # send initial state
        await ws.send_json({"type": "state", "state": _load_state(b)})

        while True:
            msg = await ws.receive_json()
            if not isinstance(msg, dict):
                continue
            if msg.get("type") == "op" and isinstance(msg.get("op"), dict):
                op = msg["op"]
                # Presence: broadcast only, do not persist.
                if op.get("op") in ("cursor", "cursor_leave"):
                    await _manager.broadcast(board_id, {"type": "op", "op": op}, exclude=ws)
                    continue
                state = _load_state(b)
                state = _apply_op(state, op)
                b.state_json = json.dumps(state, ensure_ascii=False)
                db.commit()
                await _manager.broadcast(board_id, {"type": "op", "op": op}, exclude=ws)
            elif msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        _manager.disconnect(board_id, ws)
        try:
            db.close()
        except Exception:
            pass

