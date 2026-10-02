from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Voxera"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://voxera:voxera@postgres:5432/voxera"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
