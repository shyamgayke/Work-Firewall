# sample_repo/config.py
"""
Application configuration loaded from environment variables.
All secrets accessed through this module — never hardcoded.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DatabaseConfig:
    url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///app.db"))
    pool_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "5")))
    echo_sql: bool = field(default_factory=lambda: os.getenv("ECHO_SQL", "false").lower() == "true")


@dataclass
class JWTConfig:
    secret_key: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    )
    refresh_token_expire_days: int = 30


@dataclass
class AppConfig:
    # Server
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    allowed_origins: list[str] = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    )

    # Sub-configs
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    jwt: JWTConfig = field(default_factory=JWTConfig)

    # Feature flags
    rate_limiting_enabled: bool = True
    mfa_required: bool = field(
        default_factory=lambda: os.getenv("MFA_REQUIRED", "false").lower() == "true"
    )
    audit_logging: bool = True


# Singleton pattern — instantiated once at startup
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def validate_config(cfg: AppConfig) -> list[str]:
    """Return a list of validation errors. Empty list = valid."""
    errors = []
    if cfg.jwt.secret_key == "CHANGE_ME_IN_PRODUCTION":
        errors.append("JWT_SECRET_KEY must be set to a secure random value in production")
    if cfg.database.url.startswith("sqlite") and not cfg.debug:
        errors.append("SQLite is not recommended for production; use PostgreSQL")
    return errors
