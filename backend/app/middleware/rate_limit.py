import time

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..database import get_redis

# Endpoint-specific (path_prefix, method) → (limit, window_seconds)
RULES = [
    ("/auth/login",     "POST",  20,  60),
    ("/auth/register",  "POST",  20,  60),
    ("/knowledge/search","POST", 60,  60),
    ("/evaluations/",   "POST",  10,  60),
    ("/debug/calls/",   "POST",  30,  60),
    ("/agents/",        "POST",  60,  60),
]


def _match_rule(path: str, method: str):
    for prefix, m, limit, window in RULES:
        if m == method and path.startswith(prefix):
            return prefix, limit, window
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rule = _match_rule(request.url.path, request.method)
        if rule is None:
            return await call_next(request)

        prefix, limit, window = rule

        # Key by JWT-sub if present else client IP
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            identifier = auth[-32:]  # last 32 chars of JWT — stable-ish
        else:
            identifier = request.client.host if request.client else "unknown"

        key = f"rl:{prefix}:{identifier}"
        try:
            r = get_redis()
            count = r.incr(key)
            if count == 1:
                r.expire(key, window)
            if count > limit:
                ttl = r.ttl(key)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": f"Rate limit exceeded for {prefix}. Retry in {ttl}s."},
                    headers={"Retry-After": str(ttl)},
                )
        except Exception:
            # Redis down — fail open
            pass

        return await call_next(request)
