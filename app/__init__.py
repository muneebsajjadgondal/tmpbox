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

    os.makedirs(app.config["STORAGE_DIR"], exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(app.instance_path), "instance"), exist_ok=True)

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
