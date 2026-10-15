"""
CARspective — Server Configuration
"""

import os
from pathlib import Path
from typing import List, Set

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = DATA_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)


class ConfigurationError(ValueError):
    """Raised when server configuration is invalid or violates production security invariants."""
    pass


INSECURE_SECRET_KEYS: Set[str] = {
    "",
    "PRODUCTION_SECRET_KEY_NOT_SET",
    "carspective-dev-secret-key-phase2",
    "dev-secret-key",
    "secret",
    "changeme",
    "password",
    "123456",
}

INSECURE_ADMIN_KEYS: Set[str] = {
    "",
    "carspective-admin-phase17-key",
    "admin-secret-key",
    "admin",
    "changeme",
    "password",
    "123456",
}



def normalize_database_url(url: str) -> str:
    """
    Normalizes database connection URLs.

    In SQLAlchemy 2.1+, generic 'postgresql://' URIs default to the 'psycopg' (v3) driver.
    Because CarSpective standardized on psycopg2 ('psycopg2-binary'), generic
    'postgresql://' and legacy 'postgres://' URLs are normalized to 'postgresql+psycopg2://'
    to ensure explicit, deterministic driver binding without altering credentials,
    hosts, ports, paths, or query parameters.

    Already-qualified URLs (e.g. 'postgresql+psycopg2://', 'postgresql+asyncpg://'),
    SQLite URLs, and non-PostgreSQL schemes are preserved unchanged.
    """
    if not url or not isinstance(url, str):
        return "" if url is None else str(url)

    trimmed = url.strip()
    if trimmed.startswith("postgresql://"):
        return "postgresql+psycopg2://" + trimmed[len("postgresql://"):]
    elif trimmed.startswith("postgres://"):
        return "postgresql+psycopg2://" + trimmed[len("postgres://"):]

    return trimmed


def mask_database_url(url: str) -> str:
    """Masks credentials in database URLs for safe logging."""
    if not url or not isinstance(url, str):
        return ""
    import re
    return re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1*****\3', url)


class Settings:
    def __init__(self):
        self.reload()

    def reload(self) -> None:
        """Reloads settings from environment variables."""
        self.ENV: str = os.getenv("CARSPECTIVE_ENV", "development").lower()
        self.IS_PRODUCTION: bool = (self.ENV == "production")

        # In production, DEBUG is strictly False by default unless explicitly set to True
        if self.IS_PRODUCTION:
            self.DEBUG: bool = os.getenv("CARSPECTIVE_DEBUG", "False").lower() in ("true", "1")
        else:
            self.DEBUG: bool = os.getenv("CARSPECTIVE_DEBUG", "True").lower() in ("true", "1")

        # Database URL: default to SQLite in dev, configure via DATABASE_URL in prod
        raw_db_url: str = os.getenv(
            "DATABASE_URL",
            f"sqlite:///{DATABASE_DIR / 'carspective.db'}"
        )
        self.DATABASE_URL: str = normalize_database_url(raw_db_url)


        self.API_PREFIX: str = "/api/v1"

        # Secret Key: require secure environment variable in production
        env_secret: str = os.getenv("SECRET_KEY", "")
        if self.IS_PRODUCTION and not env_secret:
            self.SECRET_KEY: str = "PRODUCTION_SECRET_KEY_NOT_SET"
        else:
            self.SECRET_KEY: str = env_secret or "carspective-dev-secret-key-phase2"

        # Admin API Key for protected ingestion/pipeline administrative tasks
        self.ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "carspective-admin-phase17-key")

        # Allowed host headers (DNS rebinding / host spoofing protection)
        raw_hosts: str = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,testserver")
        self.ALLOWED_HOSTS: List[str] = [h.strip() for h in raw_hosts.split(",") if h.strip()]

        # Trusted reverse proxy hops (for ProxyFix middleware)
        try:
            self.TRUSTED_PROXIES: int = int(os.getenv("TRUSTED_PROXIES", "0"))
        except ValueError:
            self.TRUSTED_PROXIES: int = 0

        # CORS: Explicit allowed origins (wildcard disallowed in production)
        raw_origins: str = os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
        )
        self.ALLOWED_ORIGINS: List[str] = [o.strip() for o in raw_origins.split(",") if o.strip()]

        # Baseline dataset & taxonomy
        self.DATASET_PATH: Path = DATA_DIR / "raw" / "indian_used_cars_raw_57480.csv"
        self.TAXONOMY_SEEDS_DIR: Path = DATA_DIR / "taxonomy_seeds"

    def validate_production_config(self) -> None:
        """
        Validates configuration strictly against production requirements.
        Raises ConfigurationError immediately if any required security invariant is violated.
        """
        if not self.IS_PRODUCTION:
            return

        # 1. SECRET_KEY validation
        secret = (self.SECRET_KEY or "").strip()
        if not secret or secret in INSECURE_SECRET_KEYS or len(secret) < 16:
            raise ConfigurationError(
                "Production security violation: SECRET_KEY is missing, empty, shorter than 16 characters, "
                "or configured with an insecure default. A cryptographically random secret must be provided."
            )

        # 2. ADMIN_API_KEY validation
        admin_key = (self.ADMIN_API_KEY or "").strip()
        if not admin_key or admin_key in INSECURE_ADMIN_KEYS or len(admin_key) < 16:
            raise ConfigurationError(
                "Production security violation: ADMIN_API_KEY is missing, empty, shorter than 16 characters, "
                "or configured with an insecure default. A dedicated secure administrative key must be provided."
            )

        # 3. ALLOWED_HOSTS validation
        if not self.ALLOWED_HOSTS or len(self.ALLOWED_HOSTS) == 0:
            raise ConfigurationError(
                "Production security violation: ALLOWED_HOSTS must be non-empty in production."
            )

        # 4. CORS Origins validation
        if not self.ALLOWED_ORIGINS or len(self.ALLOWED_ORIGINS) == 0:
            raise ConfigurationError(
                "Production security violation: ALLOWED_ORIGINS must be non-empty in production."
            )
        if any(origin == "*" for origin in self.ALLOWED_ORIGINS):
            raise ConfigurationError(
                "Production security violation: Wildcard '*' is strictly forbidden in ALLOWED_ORIGINS in production."
            )

        # 5. TRUSTED_PROXIES validation
        if self.TRUSTED_PROXIES < 0:
            raise ConfigurationError(
                "Production configuration violation: TRUSTED_PROXIES must be a non-negative integer."
            )

        # 6. DEBUG mode validation
        if self.IS_PRODUCTION and self.DEBUG and (self.ENV == "production" or os.getenv("CARSPECTIVE_DEBUG", "").lower() in ("true", "1")):
            raise ConfigurationError(
                "Production security violation: DEBUG mode (CARSPECTIVE_DEBUG) must be disabled in production."
            )

        # 7. DATABASE_URL validation
        if not self.DATABASE_URL or not self.DATABASE_URL.strip():
            raise ConfigurationError(
                "Production configuration violation: DATABASE_URL must be specified and non-empty in production."
            )


settings = Settings()
