from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .config import settings
from .database import check_database, check_redis
from .middleware.rate_limit import RateLimitMiddleware
from .routers import (
    agents,
    calls,
    chat,
    debug,
    evaluations,
    health,
    knowledge,
    me,
    organizations,
    tenants,
    traces,
    users,
    ws_calls,
)

app = FastAPI(title=settings.app_name, version="0.13.0")

# Rate limit BEFORE anything else
app.add_middleware(RateLimitMiddleware)

# CORS: restricted origins from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_liveness():
    return {"status": "ok", "service": "voxera"}


@app.get("/health/database")
def health_database():
    return {"status": "ok" if check_database() else "error", "service": "postgres"}


@app.get("/health/redis")
def health_redis():
    return {"status": "ok" if check_redis() else "error", "service": "redis"}


@app.get("/")
def root():
    return {"service": settings.app_name, "env": settings.app_env, "version": "0.13.0"}


app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(me.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(traces.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(calls.router)
app.include_router(evaluations.router)
app.include_router(debug.router)
app.include_router(knowledge.router)
app.include_router(ws_calls.router)
