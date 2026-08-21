"""
Minimal in-memory rate limiting for sensitive auth endpoints.

This is intentionally dependency-free (stdlib only) so it doesn't require
touching poetry.lock. It is a fixed-window limiter keyed by client IP and
scoped per endpoint via `scope`.

Limitations (by design, given the constraints of this fix):
- State is per-process. If the backend ever runs with multiple workers or
  replicas, each process has its own counters, so the effective limit is
  multiplied by the number of processes. For a real production deployment,
  move this to a shared store (Redis) or enforce it at the reverse proxy
  (nginx `limit_req`, Cloudflare, etc.).
- Trusts `request.client.host`; if the app sits behind a proxy, configure
  Uvicorn/FastAPI to trust `X-Forwarded-For` from that proxy only, otherwise
  this header is trivially spoofable and the limiter becomes a no-op.
"""
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class _FixedWindowLimiter:
    def __init__(self) -> None:
        # (scope, client_key) -> (window_start_epoch, count)
        self._buckets: dict[tuple[str, str], tuple[float, int]] = defaultdict(lambda: (0.0, 0))

    def check(self, scope: str, client_key: str, max_calls: int, window_seconds: int) -> None:
        now = time.monotonic()
        key = (scope, client_key)
        window_start, count = self._buckets[key]

        if now - window_start >= window_seconds:
            # New window
            self._buckets[key] = (now, 1)
            return

        if count >= max_calls:
            retry_after = int(window_seconds - (now - window_start)) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много попыток. Попробуйте позже.",
                headers={"Retry-After": str(retry_after)},
            )

        self._buckets[key] = (window_start, count + 1)


_limiter = _FixedWindowLimiter()


def rate_limit(scope: str, max_calls: int, window_seconds: int):
    """FastAPI dependency factory: limits `max_calls` per `window_seconds` per client IP."""

    def _dependency(request: Request) -> None:
        client_key = request.client.host if request.client else "unknown"
        _limiter.check(scope, client_key, max_calls, window_seconds)

    return _dependency
