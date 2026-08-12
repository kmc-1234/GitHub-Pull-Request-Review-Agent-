from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://review:review@localhost:5432/review"
    redis_url: str = "redis://localhost:6379/0"
    github_webhook_secret: str = Field(default="", min_length=0)
    github_app_id: str = ""
    github_private_key: str = ""
    github_api_url: str = "https://api.github.com"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    min_confidence: float = 0.72
    max_comments: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()
