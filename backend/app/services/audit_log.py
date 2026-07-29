"""Structured audit trail (JSON) for security/operations monitoring.

We currently emit audit events via the existing structured logger so they appear
in production JSON logs together with request_id correlation.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger("audit")


def audit_event(
    *,
    action: str,
    entity_type: str,
    entity_id: int | str | None,
    actor_user_id: int | None,
    success: bool = True,
    meta: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor_user_id": actor_user_id,
        "success": success,
    }
    if meta:
        payload["meta"] = meta

    logger.info("audit", extra={"audit": payload})

