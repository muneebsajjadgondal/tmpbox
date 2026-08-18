import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _resolve_db_uri() -> str:
    """Vercel's Postgres integration sets POSTGRES_URL (Neon-backed);
    plain DATABASE_URL also works if you wire up your own Postgres.
    Falls back to local SQLite for local dev. SQLAlchemy needs the
    'postgresql://' scheme, but some providers hand out 'postgres://'."""
    uri = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    if uri:
        return uri
    return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'tmpbox.db')}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _resolve_db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Shared secret the /api/cleanup route checks against the Authorization
    # header Vercel Cron sends. Leave unset locally to skip the check.
    CRON_SECRET = os.environ.get("CRON_SECRET")

    STORAGE_DIR = os.environ.get("STORAGE_DIR", os.path.join(BASE_DIR, "storage"))

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 100)) * 1024 * 1024

    # Allowed expiry presets, in minutes, shown to the user
    EXPIRY_PRESETS = {
        "1h": 60,
        "1d": 60 * 24,
        "7d": 60 * 24 * 7,
    }
    DEFAULT_EXPIRY_KEY = "1d"

    # How often the background cleanup job runs
    CLEANUP_INTERVAL_MINUTES = int(os.environ.get("CLEANUP_INTERVAL_MINUTES", 15))

    # Extensions that are blocked outright regardless of MIME sniffing
    BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".msi", ".com", ".scr"}

    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_UPLOAD = os.environ.get("RATELIMIT_UPLOAD", "10 per hour")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    STORAGE_DIR = os.path.join(BASE_DIR, "tests", "_tmp_storage")
    RATELIMIT_ENABLED = False
