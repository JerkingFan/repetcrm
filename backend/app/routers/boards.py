import asyncio
import copy
import json
import math
import os
import secrets
from datetime import datetime
from typing import Any

PERSIST_DEBOUNCE_SEC = 1.5

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
        state = payload["state_json"]
        if isinstance(state, dict):
            _compact_state(state)
            _room_store.replace(board_id, state)
            b.state_json = json.dumps(state, ensure_ascii=False)
        else:
            b.state_json = json.dumps(state, ensure_ascii=False)
        b.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(b)
    return _board_to_dict(b)


@router.put("/{board_id}/public")
def update_board_public(board_id: int, token: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    b = _allow_board_access(db, board_id, share_token=token)
    if payload.get("state_json") is not None:
        state = payload["state_json"]
        if isinstance(state, dict):
            _compact_state(state)
            _room_store.replace(board_id, state)
            b.state_json = json.dumps(state, ensure_ascii=False)
        else:
            b.state_json = json.dumps(state, ensure_ascii=False)
        b.updated_at = datetime.utcnow()
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


def _perpendicular_distance(p: dict, a: dict, b: dict) -> float:
    ax, ay = float(a["x"]), float(a["y"])
    bx, by = float(b["x"]), float(b["y"])
    px, py = float(p["x"]), float(p["y"])
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _douglas_peucker(points: list[dict], epsilon: float) -> list[dict]:
    if len(points) <= 2:
        return points
    max_dist = 0.0
    index = 0
    end = len(points) - 1
    for i in range(1, end):
        d = _perpendicular_distance(points[i], points[0], points[end])
        if d > max_dist:
            max_dist = d
            index = i
    if max_dist > epsilon:
        left = _douglas_peucker(points[: index + 1], epsilon)
        right = _douglas_peucker(points[index:], epsilon)
        return left[:-1] + right
    return [points[0], points[end]]


def _simplify_stroke_points(points: list, epsilon: float = 0.002) -> list:
    clean = []
    for pt in points:
        if not isinstance(pt, dict):
            continue
        x, y = pt.get("x"), pt.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            clean.append({"x": float(x), "y": float(y)})
    if len(clean) <= 3:
        return clean
    return _douglas_peucker(clean, epsilon)


def _compact_state(state: dict) -> None:
    """Упрощает полилинии in-place перед записью в БД."""
    for st in state.get("strokes", []):
        if not isinstance(st, dict):
            continue
        pts = st.get("points")
        if isinstance(pts, list) and len(pts) > 4:
            st["points"] = _simplify_stroke_points(pts)


class _BoardRoomStore:
    """
    In-memory state per board + debounced SQLite/Postgres persist.

    Продакшен: при uvicorn --workers > 1 нужен Redis pub/sub для broadcast между
    процессами или один воркер для WS. См. deploy/WEBSOCKET.md.
    """

    def __init__(self):
        self._states: dict[int, dict] = {}
        self._persist_tasks: dict[int, asyncio.Task] = {}

    def ensure_loaded(self, board_id: int, initial: dict) -> dict:
        if board_id not in self._states:
            self._states[board_id] = copy.deepcopy(initial)
        return self._states[board_id]

    def replace(self, board_id: int, state: dict) -> None:
        self._states[board_id] = copy.deepcopy(state)

    def apply(self, board_id: int, op: dict) -> dict:
        state = self._states[board_id]
        return _apply_op(state, op)

    def schedule_persist(self, board_id: int) -> None:
        task = self._persist_tasks.get(board_id)
        if task and not task.done():
            task.cancel()
        self._persist_tasks[board_id] = asyncio.create_task(self._persist_after_delay(board_id))

    async def _persist_after_delay(self, board_id: int) -> None:
        try:
            await asyncio.sleep(PERSIST_DEBOUNCE_SEC)
            await self.flush(board_id)
        except asyncio.CancelledError:
            pass

    async def flush(self, board_id: int) -> None:
        task = self._persist_tasks.pop(board_id, None)
        if task and not task.done():
            task.cancel()
        state = self._states.get(board_id)
        if state is None:
            return
        _compact_state(state)
        db = SessionLocal()
        try:
            b = db.query(Board).filter(Board.id == board_id).first()
            if not b:
                return
            b.state_json = json.dumps(state, ensure_ascii=False)
            b.updated_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()


_room_store = _BoardRoomStore()


class _BoardConnectionManager:
    def __init__(self, store: _BoardRoomStore):
        self._store = store
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
            asyncio.create_task(self._store.flush(board_id))

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


_manager = _BoardConnectionManager(_room_store)

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


def _text_hit(t: dict, px: float, py: float, r: float) -> bool:
    if not isinstance(t, dict):
        return False
    x = t.get("x")
    y = t.get("y")
    text = t.get("text")
    size = t.get("size")
    if not all(isinstance(v, (int, float)) for v in (x, y, size)) or not isinstance(text, str):
        return False
    w = max(len(text), 1) * float(size) * 0.55
    h = float(size) * 1.25
    return (
        float(px) >= float(x) - r
        and float(px) <= float(x) + w + r
        and float(py) >= float(y) - r
        and float(py) <= float(y) + h + r
    )


def _image_hit(im: dict, px: float, py: float, r: float) -> bool:
    if not isinstance(im, dict):
        return False
    x = im.get("x")
    y = im.get("y")
    w = im.get("w")
    h = im.get("h")
    if not all(isinstance(v, (int, float)) for v in (x, y, w, h)):
        return False
    return (
        float(px) >= float(x) - r
        and float(px) <= float(x) + float(w) + r
        and float(py) >= float(y) - r
        and float(py) <= float(y) + float(h) + r
    )


def _apply_op(state: dict, op: dict) -> dict:
    t = op.get("op")
    # presence ops are ephemeral; caller should not persist them
    if t in ("cursor", "cursor_leave"):
        return state
    if t == "set_state":
        new_state = op.get("state")
        if not isinstance(new_state, dict):
            return state
        return {
            "version": 1,
            "strokes": new_state.get("strokes") if isinstance(new_state.get("strokes"), list) else [],
            "texts": new_state.get("texts") if isinstance(new_state.get("texts"), list) else [],
            "images": new_state.get("images") if isinstance(new_state.get("images"), list) else [],
        }
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

    if t == "stroke_simplify":
        sid = op.get("id")
        points = op.get("points")
        if not isinstance(sid, str) or not isinstance(points, list):
            return state
        simplified = _simplify_stroke_points(points, epsilon=0.002)
        for st in state.get("strokes", []):
            if isinstance(st, dict) and st.get("id") == sid:
                st["points"] = simplified if len(simplified) >= 2 else st.get("points", [])
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
            iid = item.get("id")
            if isinstance(iid, str) and iid:
                for it in state.get("images", []):
                    if isinstance(it, dict) and it.get("id") == iid:
                        return state
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

    if t == "image_update":
        iid = op.get("id")
        x = op.get("x")
        y = op.get("y")
        w = op.get("w")
        h = op.get("h")
        if (
            not isinstance(iid, str)
            or not isinstance(x, (int, float))
            or not isinstance(y, (int, float))
            or not isinstance(w, (int, float))
            or not isinstance(h, (int, float))
        ):
            return state
        for it in state.get("images", []):
            if isinstance(it, dict) and it.get("id") == iid:
                it["x"] = float(x)
                it["y"] = float(y)
                it["w"] = max(0.02, float(w))
                it["h"] = max(0.02, float(h))
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
        texts = []
        for titem in state.get("texts", []):
            if not _text_hit(titem, float(px), float(py), float(r)):
                texts.append(titem)
        state["texts"] = texts
        images = []
        for im in state.get("images", []):
            if not _image_hit(im, float(px), float(py), float(r)):
                images.append(im)
        state["images"] = images
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

        initial = _load_state(b)
        state = _room_store.ensure_loaded(board_id, initial)
        await ws.send_json({"type": "state", "state": state})

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
                _room_store.apply(board_id, op)
                _room_store.schedule_persist(board_id)
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
        # If room still active, debounced flush continues; empty room flushes in disconnect.

