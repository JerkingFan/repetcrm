"""Attach X-Request-ID to each request and response."""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.request_context import request_id_ctx, set_request_id

logger = logging.getLogger(__name__)

_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming = (request.headers.get(_HEADER) or "").strip()
        request_id = incoming if incoming else str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        response.headers[_HEADER] = request_id
        return response
