"""Redis pub/sub bus for whiteboard ops across API workers."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from typing import Awaitable, Callable

from app.config import get_settings

logger = logging.getLogger(__name__)

ChannelHandler = Callable[[int, dict], Awaitable[None]]

_PREFIX = "repetcrm:board:"
_SUFFIX = ":ops"

# Unique per process — skip echo of our own publishes.
INSTANCE_ID = secrets.token_hex(8)


class BoardBus:
    def __init__(self) -> None:
        self._redis = None
        self._pubsub = None
        self._listener_task: asyncio.Task | None = None
        self._handler: ChannelHandler | None = None

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    def set_handler(self, handler: ChannelHandler) -> None:
        self._handler = handler

    async def start(self) -> None:
        url = get_settings().redis_url.strip()
        if not url:
            logger.info("Board bus disabled (REDIS_URL not set)")
            return
        if self._listener_task is not None:
            return

        try:
            from redis import asyncio as aioredis
        except ImportError:
            logger.warning("redis asyncio unavailable — board bus disabled")
            return

        try:
            self._redis = aioredis.from_url(url, decode_responses=True)
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.psubscribe(f"{_PREFIX}*{_SUFFIX}")
            self._listener_task = asyncio.create_task(self._listen())
            logger.info("Board bus started instance=%s", INSTANCE_ID)
        except Exception as exc:
            logger.warning("Board bus start failed: %s", exc)
            await self.stop()

    async def stop(self) -> None:
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe()
                await self._pubsub.aclose()
            except Exception:
                pass
            self._pubsub = None

        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None

    def _channel_for(self, board_id: int) -> str:
        return f"{_PREFIX}{board_id}{_SUFFIX}"

    def _board_id_from_channel(self, channel: str) -> int | None:
        if not channel.startswith(_PREFIX) or not channel.endswith(_SUFFIX):
            return None
        middle = channel[len(_PREFIX) : -len(_SUFFIX)]
        try:
            return int(middle)
        except ValueError:
            return None

    async def publish(self, board_id: int, message: dict) -> None:
        if self._redis is None:
            return
        payload = {**message, "origin": INSTANCE_ID}
        try:
            await self._redis.publish(self._channel_for(board_id), json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            logger.warning("Board bus publish failed board=%s: %s", board_id, exc)

    async def _listen(self) -> None:
        assert self._pubsub is not None
        try:
            async for raw in self._pubsub.listen():
                if raw.get("type") != "pmessage":
                    continue
                channel = raw.get("channel") or ""
                data = raw.get("data")
                if not data or self._handler is None:
                    continue
                board_id = self._board_id_from_channel(channel)
                if board_id is None:
                    continue
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if payload.get("origin") == INSTANCE_ID:
                    continue
                try:
                    await self._handler(board_id, payload)
                except Exception as exc:
                    logger.warning("Board bus handler error board=%s: %s", board_id, exc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Board bus listener stopped: %s", exc)


board_bus = BoardBus()
