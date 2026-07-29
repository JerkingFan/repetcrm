"""Per-request context (correlation ID for logs and error responses)."""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def set_request_id(value: str | None) -> None:
    request_id_ctx.set(value)


def resolve_request_id(request: Request | None = None) -> str | None:
    if request is not None:
        rid = getattr(getattr(request, "state", None), "request_id", None)
        if rid:
            return str(rid)
    return get_request_id()