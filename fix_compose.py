from pathlib import Path

content = '''services:
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
      - ./backend/alembic:/app/alembic
      - ./backend/alembic.ini:/app/alembic.ini
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
'''

p = Path("docker-compose.yml")
p.write_text(content, encoding="utf-8")
print(f"Overwrote {p}")

# Verify mounts are present
text = p.read_text(encoding="utf-8")
alembic_lines = [l for l in text.splitlines() if "alembic" in l]
print(f"\nalembic mount lines ({len(alembic_lines)}):")
for l in alembic_lines:
    print(f"  {l}")