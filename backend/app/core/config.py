from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL
from sqlalchemy.engine import make_url

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    database_url_override: SecretStr | None = Field(default=None, validation_alias="DATABASE_URL")
    postgres_db: str = "sunpower"
    postgres_user: str = "sunpower"
    postgres_password: SecretStr | None = None
    postgres_host: str = "127.0.0.1"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    jwt_secret: SecretStr | None = Field(default=None, min_length=32)
    jwt_ttl_seconds: int = Field(default=8 * 60 * 60, gt=0)
    secure_cookies: bool = False
    frontend_origin: str = "http://localhost:5173"
    advance_percent: int = Field(default=30, ge=0, le=100)
    uploads_dir: Path = REPO_ROOT / "uploads"

    @property
    def database_url(self) -> URL:
        if self.database_url_override is not None:
            url = make_url(self.database_url_override.get_secret_value())
            if url.drivername == "postgresql":
                return url.set(drivername="postgresql+psycopg")
            return url
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value() if self.postgres_password else None,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
