"""Application settings using pydantic-settings with .env support."""

import logging
from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Log level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="JSON_FORCE_PROXY_",
        case_sensitive=False,
    )

    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8080, description="Port to listen on")
    target_url: str = Field(
        default="http://168.253.224.242:9091/dst/info",
        description="Target URL to proxy",
    )
    reload: bool = Field(default=False, description="Enable auto-reload for development")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    request_timeout: float = Field(default=10.0, description="HTTP request timeout in seconds")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def configure_logging(settings: Settings) -> None:
    """Configure logging based on settings."""
    logging.basicConfig(
        level=settings.log_level.value,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
