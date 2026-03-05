from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정. 환경변수 및 .env 파일에서 로드."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Smart Task Manager"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database (기본값: SQLite, 배포 시 PostgreSQL URL로 교체)
    database_url: str = "sqlite:///./taskmanager.db"

    # AI / Claude
    anthropic_api_key: SecretStr = SecretStr("")
    claude_model: str = "claude-sonnet-4-20250514"

    # Notion Integration
    notion_api_key: SecretStr = SecretStr("")
    notion_database_id: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """캐싱된 설정 반환. FastAPI 의존성으로 사용."""
    return Settings()
