"""WebSocket room management and cross-worker board sync."""

from __future__ import annotations

import asyncio
import copy
import json
from datetime import datetime

from fastapi import WebSocket

from app.config import get_settings
from app.database import SessionLocal
from app.models import Board
from app.services.board_state import apply_op, compact_state


class BoardRoomStore:
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
        return apply_op(state, op)

    def schedule_persist(self, board_id: int) -> None:
        task = self._persist_tasks.get(board_id)
        if task and not task.done():
            task.cancel()
        delay = float(get_settings().board_persist_debounce_sec)
        self._persist_tasks[board_id] = asyncio.create_task(self._persist_after_delay(board_id, delay))

    async def _persist_after_delay(self, board_id: int, delay_sec: float) -> None:
        try:
            await asyncio.sleep(max(0.5, delay_sec))
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
        compact_state(state)
        db = SessionLocal()
        try:
            b = db.query(Board).filter(Board.id == board_id).first()
            if not b:
                return
            b.state_json = json.dumps(state, ensure_ascii=False)
            b.updated_at = datetime.utcnow()
            from app.services.board_snapshots import save_board_snapshot

            save_board_snapshot(db, board_id, b.state_json)
            db.commit()
        finally:
            db.close()


class BoardConnectionManager:
    def __init__(self, store: BoardRoomStore):
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
                self.disconnect(board_id, ws)

    async def publish_op(self, board_id: int, op: dict, *, exclude: WebSocket | None = None) -> None:
        if op.get("op") in ("cursor", "cursor_leave"):
            await self.broadcast(board_id, {"type": "op", "op": op}, exclude=exclude)
            from app.services.board_bus import board_bus

            await board_bus.publish(board_id, {"type": "op", "op": op})
            return

        self._store.apply(board_id, op)
        self._store.schedule_persist(board_id)
        await self.broadcast(board_id, {"type": "op", "op": op}, exclude=exclude)
        from app.services.board_bus import board_bus

        await board_bus.publish(board_id, {"type": "op", "op": op})


room_store = BoardRoomStore()
connection_manager = BoardConnectionManager(room_store)


async def handle_remote_board_op(board_id: int, payload: dict) -> None:
    """Ops from another API worker via Redis pub/sub."""
    op = payload.get("op")
    if not isinstance(op, dict):
        return
    if op.get("op") in ("cursor", "cursor_leave"):
        await connection_manager.broadcast(board_id, {"type": "op", "op": op})
        return
    if board_id not in room_store._states:
        return
    room_store.apply(board_id, op)
    await connection_manager.broadcast(board_id, {"type": "op", "op": op})


async def setup_board_bus() -> None:
    from app.services.board_bus import board_bus

    board_bus.set_handler(handle_remote_board_op)
    await board_bus.start()


async def shutdown_board_bus() -> None:
    from app.services.board_bus import board_bus

    await board_bus.stop()
