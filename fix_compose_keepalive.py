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
    environment:
      - OLLAMA_URL=http://ollama:11434
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      ollama:
        condition: service_started

  ollama:
    image: ollama/ollama:latest
    container_name: voxera-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_KEEP_ALIVE=24h
    restart: unless-stopped

  postgres:
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

  redis:
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
  ollama_data:
'''

Path("docker-compose.yml").write_text(content, encoding="utf-8")
text = Path("docker-compose.yml").read_text(encoding="utf-8")
print("Wrote docker-compose.yml")
print("Contains OLLAMA_KEEP_ALIVE:", "OLLAMA_KEEP_ALIVE" in text)