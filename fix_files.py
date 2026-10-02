from pathlib import Path

files = {}

files["docker-compose.yml"] = """services:
  voxera-frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: voxera-frontend
    ports:
      - "8080:80"
    depends_on:
      - voxera-backend

  voxera-backend:
    build:
      context: ./backend
    container_name: voxera-backend
    env_file:
      - .env
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app:/app/app
    depends_on:
      voxera-postgres:
        condition: service_healthy
      voxera-redis:
        condition: service_healthy

  voxera-postgres:
    image: postgres:16-alpine
    container_name: voxera-postgres
    environment:
      POSTGRES_USER: voxera
      POSTGRES_PASSWORD: voxera
      POSTGRES_DB: voxera
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U voxera -d voxera"]
      interval: 5s
      timeout: 5s
      retries: 10

  voxera-redis:
    image: redis:7-alpine
    container_name: voxera-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
"""

files["backend/app/config.py"] = '''from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Voxera"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://voxera:voxera@postgres:5432/voxera"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
'''

files["backend/app/database.py"] = '''from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def check_database() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def check_redis() -> bool:
    try:
        get_redis().ping()
        return True
    except Exception:
        return False
'''

files["backend/app/main.py"] = '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import check_database, check_redis

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "voxera"}


@app.get("/health/database")
def health_database():
    ok = check_database()
    return {"status": "ok" if ok else "error", "service": "postgres"}


@app.get("/health/redis")
def health_redis():
    ok = check_redis()
    return {"status": "ok" if ok else "error", "service": "redis"}


@app.get("/")
def root():
    return {"service": settings.app_name, "env": settings.app_env}
'''

files["backend/Dockerfile"] = '''FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
'''

files["frontend/Dockerfile"] = '''FROM nginx:1.27-alpine

COPY frontend/ /usr/share/nginx/html/
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
'''

files["frontend/index.html"] = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Voxera</title>
  <link rel="stylesheet" href="css/main.css" />
</head>
<body>
  <main class="card">
    <h1>VOXERA</h1>
    <p class="tagline">AI Voice Agent Platform</p>
    <div class="status" id="overall">System Online</div>

    <ul class="checks">
      <li><span>API</span><span id="api">...</span></li>
      <li><span>Database</span><span id="db">...</span></li>
      <li><span>Redis</span><span id="redis">...</span></li>
    </ul>
  </main>
  <script src="js/app.js"></script>
</body>
</html>
'''

files["frontend/js/app.js"] = '''const API_BASE = "/api";

const endpoints = {
  api: API_BASE + "/health",
  db: API_BASE + "/health/database",
  redis: API_BASE + "/health/redis",
};

async function check(key) {
  const el = document.getElementById(key);
  try {
    const res = await fetch(endpoints[key]);
    const data = await res.json();
    const ok = data.status === "ok";
    el.textContent = ok ? "OK" : "FAIL";
    el.className = ok ? "ok" : "err";
    return ok;
  } catch (e) {
    el.textContent = "FAIL";
    el.className = "err";
    return false;
  }
}

(async () => {
  const results = await Promise.all(Object.keys(endpoints).map(check));
  const overall = document.getElementById("overall");
  const allOk = results.every(Boolean);
  overall.textContent = allOk ? "System Online" : "Degraded";
  overall.style.color = allOk ? "var(--accent)" : "var(--error)";
})();
'''

files["docker/nginx.conf"] = '''server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
'''

for path, content in files.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print("\nDone. All files rewritten.")