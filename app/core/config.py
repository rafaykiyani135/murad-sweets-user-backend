import os
from typing import List
from pydantic import AnyHttpUrl, Field, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./murad_sweets.db",
        description="Database connection URL. If using Postgres, use postgresql+asyncpg://"
    )
    APP_ENV: str = Field(default="development")
    FRONTEND_ORIGIN: str = Field(default="http://localhost:3000")
    CORS_ORIGINS: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins. If empty, defaults to FRONTEND_ORIGIN + localhost."
    )
    JWT_SECRET: str = Field(default="supersecret_replace_this_in_production_92138402138")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=720)  # 12 hours

    # SMTP Settings
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="")
    SMTP_PASS: str = Field(default="")
    OWNER_NOTIFICATION_EMAIL: str = Field(default="admin@muradsweets.com")

    # Stripe Settings
    STRIPE_SECRET_KEY: str = Field(default="")
    STRIPE_WEBHOOK_SECRET: str = Field(default="")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS into a deduplicated list. Falls back to FRONTEND_ORIGIN + localhost."""
        origins = set()
        if self.CORS_ORIGINS:
            for origin in self.CORS_ORIGINS.split(","):
                origin = origin.strip()
                if origin:
                    origins.add(origin)
        # Always include FRONTEND_ORIGIN and common local dev origins
        origins.add(self.FRONTEND_ORIGIN)
        origins.add("http://localhost:3000")
        origins.add("http://127.0.0.1:3000")
        return list(origins)

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        # If user provides postgresql:// or postgres://, convert to asyncpg driver
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        # If using SQLite, convert to async sqlite if it isn't already
        elif url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
