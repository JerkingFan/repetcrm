"""HTTP helpers (client IP behind reverse proxy)."""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """First hop from X-Forwarded-For, then X-Real-IP, then direct client."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
