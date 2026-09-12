"""Application settings.

Every value is read from the environment; `.env.example` in the repository root
lists all of them. No secret has a usable default — `SUTRADHAR_JWT_SECRET` must
be supplied or the application refuses to start.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SUTRADHAR_",
        env_file=(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database -----------------------------------------------------------
    # A filesystem path, not a URL: the two engines derive different URLs from
    # it (read-write and read-only). See app/db/app.py and app/db/readonly.py.
    db_path: Path = Field(default=REPO_ROOT / "data" / "app.db")

    # --- Auth ---------------------------------------------------------------
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_minutes: int = 720
    cookie_secure: bool = True
    cookie_domain: str | None = None

    # --- Uploads ------------------------------------------------------------
    upload_dir: Path = Field(default=REPO_ROOT / "storage" / "uploads")
    max_upload_bytes: int = 10 * 1024 * 1024

    # --- Frontend / CORS ----------------------------------------------------
    frontend_origin: str = "http://localhost:3000"

    # --- AI provider (wired in a later phase; recorded here for the seam) ---
    llm_provider: Literal["gemini", "local"] = "gemini"
    gemini_api_key: str | None = None
    local_model_base_url: str = "http://localhost:11434"

    environment: Literal["development", "production"] = "development"

    @field_validator("jwt_secret")
    @classmethod
    def _reject_placeholder_secret(cls, v: str) -> str:
        if v.strip().lower() in {"change-me", "changeme", "secret", "placeholder"}:
            raise ValueError(
                "SUTRADHAR_JWT_SECRET is still the placeholder value. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        return v

    @property
    def readonly_database_url(self) -> str:
        """SQLite URI opened in read-only mode.

        The driver refuses writes before they reach the database file. The
        Postgres equivalent is a role holding GRANT SELECT and nothing else —
        see the README section "The AI can read, never write".
        """
        return f"sqlite:///file:{self.db_path}?mode=ro&uri=true"

    @property
    def app_database_url(self) -> str:
        """Read-write SQLite URL. Only the application layer may use this."""
        return f"sqlite:///{self.db_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
