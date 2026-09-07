"""Απλός in-memory rate limiter (ανά IP).

Αρκετός για ένα single-instance deployment (Render free). Για πολλαπλά
instances θα χρειαζόταν κοινός χώρος (π.χ. Redis).
"""
import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_hits: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request, bucket: str, max_calls: int, window_seconds: int) -> None:
    if os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "false":
        return

    key = f"{bucket}:{_client_ip(request)}"
    now = time.monotonic()
    q = _hits[key]

    while q and now - q[0] > window_seconds:
        q.popleft()

    if len(q) >= max_calls:
        raise HTTPException(
            status_code=429,
            detail="Πάρα πολλές προσπάθειες. Περίμενε λίγο και δοκίμασε ξανά.",
        )

    q.append(now)


def clear_all() -> None:
    """Μόνο για tests."""
    _hits.clear()
