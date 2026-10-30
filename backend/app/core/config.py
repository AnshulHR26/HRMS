"""Environment-based application configuration (pydantic-settings)."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "HRMS API"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = Field(..., description="SQLAlchemy URL, e.g. postgresql+psycopg://...")
    TEST_DATABASE_URL: str | None = None
    DB_ECHO: bool = False

    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, ge=1, le=24 * 60)

    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    COOKIE_NAME: str = "hrms_access_token"
    CSRF_COOKIE_NAME: str = "hrms_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    LOGIN_MAX_FAILED_ATTEMPTS: int = Field(5, ge=1)
    LOGIN_LOCKOUT_MINUTES: int = Field(15, ge=1)

    BOOTSTRAP_ADMIN_USER_ID: str = "admin"
    BOOTSTRAP_ADMIN_PASSWORD: str | None = None
    BOOTSTRAP_ADMIN_NAME: str = "System Administrator"
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@example.com"
    DEMO_USER_PASSWORD: str | None = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("DATABASE_URL", "TEST_DATABASE_URL")
    @classmethod
    def require_postgres(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("postgresql"):
            raise ValueError("PostgreSQL is the only supported database (postgresql+psycopg://...)")
        return value

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
