"""Global exception handlers with unified JSON error schema."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings
from app.request_context import get_request_id, resolve_request_id

logger = logging.getLogger(__name__)


def error_payload(
    *,
    request: Request,
    detail: str | list | dict,
    code: str,
    errors: list | None = None,
) -> dict:
    body: dict = {
        "detail": detail,
        "code": code,
        "request_id": resolve_request_id(request),
    }
    if errors is not None:
        body["errors"] = errors
    return body


def register_exception_handlers(app: FastAPI, cfg: Settings) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                request=request,
                detail="Validation failed",
                code="validation_error",
                errors=exc.errors(),
            ),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                request=request,
                detail="Validation failed",
                code="validation_error",
                errors=exc.errors(),
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception(
            "database error path=%s",
            request.url.path,
            extra={"request_id": get_request_id()},
        )
        detail = (
            "Database error"
            if cfg.is_production
            else f"Database error: {exc.__class__.__name__}"
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(detail=detail, code="database_error", request=request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(detail=exc.detail, code="http_error", request=request),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "unhandled error path=%s",
            request.url.path,
            extra={"request_id": get_request_id()},
        )
        detail = (
            "Internal server error"
            if cfg.is_production
            else f"{exc.__class__.__name__}: {exc}"
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(detail=detail, code="internal_error", request=request),
        )
