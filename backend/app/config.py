from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Voxera"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://voxera:voxera@postgres:5432/voxera"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "change-me"

    # Comma-separated list; "*" only allowed in development
    cors_origins_raw: str = "http://localhost:8080,http://127.0.0.1:8080"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


settings = Settings()
