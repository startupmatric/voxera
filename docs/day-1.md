# Day 1 - Production Foundation

Goal: Voxera runs end-to-end with one command.

Services:
- voxera-frontend -> nginx on :8080
- voxera-backend  -> FastAPI on :8000
- voxera-postgres -> Postgres 16 on :5432
- voxera-redis    -> Redis 7 on :6379

Endpoints: /health, /health/database, /health/redis
