import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config

db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    on_vercel = bool(os.environ.get("VERCEL"))

    # Local disk writes only happen in local dev (no BLOB token = local
    # storage fallback, no DATABASE_URL/POSTGRES_URL = local SQLite fallback).
    # Vercel's filesystem is read-only outside /tmp, so never attempt this
    # when actually running on Vercel - Postgres/Blob must be configured there.
    if not on_vercel:
        os.makedirs(app.config["STORAGE_DIR"], exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(app.instance_path), "instance"), exist_ok=True)
    else:
        if not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")):
            raise RuntimeError(
                "Running on Vercel but no DATABASE_URL/POSTGRES_URL is set. "
                "Connect Postgres from the project's Storage tab, then redeploy."
            )
        if not os.environ.get("BLOB_READ_WRITE_TOKEN"):
            raise RuntimeError(
                "Running on Vercel but BLOB_READ_WRITE_TOKEN is not set. "
                "Connect Blob storage from the project's Storage tab, then redeploy."
            )

    db.init_app(app)
    limiter.init_app(app)

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    # Background cleanup job - only makes sense on a long-running process.
    # On Vercel (serverless, no persistent process) cleanup instead runs via
    # a Vercel Cron hitting /api/cleanup (see vercel.json + app/routes.py).
    if not app.config.get("TESTING") and not os.environ.get("VERCEL"):
        from app.scheduler import start_scheduler
        start_scheduler(app)

    return app
