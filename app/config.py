"""Application settings (pydantic-settings).

Defaults make the API run with **zero configuration** on SQLite so it works on any
machine without Docker/Postgres. Point ``DATABASE_URL`` at a PostgreSQL+PostGIS
instance for the production spatial path described in implementation_plan.md §7.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    # --- core ---
    app_name: str = "LandSecure API"
    environment: str = "development"

    # SQLite by default → runs anywhere. Use postgresql+psycopg://… for PostGIS.
    database_url: str = "sqlite:///./data/landsecure.db"

    # --- auth ---
    jwt_secret: str = "dev-secret-change-me-in-production-please-32chars"
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 60 * 12       # 12h access token
    refresh_token_ttl_days: int = 7

    # --- CORS (Next.js dev origin) ---
    # NoDecode: take the raw env string as-is (comma-separated) instead of letting
    # pydantic-settings JSON-decode it; the validator below splits it into a list.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    # Optional regex to also allow dynamic origins (e.g. Vercel preview URLs):
    #   CORS_ORIGIN_REGEX=https://.*\.vercel\.app
    cors_origin_regex: str | None = None

    # --- seed demo accounts ---
    seed_admin_name: str = "LandSecure Admin"
    seed_admin_email: str = "admin@landsecure.ng"
    seed_admin_password: str = "admin1234"
    seed_buyer_name: str = "Sodiq Adiamo"
    seed_buyer_email: str = "buyer@landsecure.ng"
    seed_buyer_password: str = "buyer1234"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_url(cls, v):
        """Managed hosts (Render/Heroku) hand out ``postgres://`` or bare
        ``postgresql://`` URLs that default to the absent psycopg2 driver. Pin
        them to psycopg v3 so the same wheel works locally and in production."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = "postgresql+psycopg://" + v[len("postgres://"):]
            elif v.startswith("postgresql://"):
                v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgres")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
