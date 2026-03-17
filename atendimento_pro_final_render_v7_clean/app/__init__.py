from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_login import current_user

from app.auth import bp as auth_bp
from app.extensions import db, login_manager
from app.main import bp as main_bp
from app.models import Client, User
from app.utils import DEFAULT_TIMEZONE, generate_csrf_token, local_today, validate_csrf



def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    default_sqlite = f"sqlite:///{instance_path / 'app.db'}"
    database_url = os.getenv("DATABASE_URL", default_sqlite).strip()
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
    elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "troque-esta-chave"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        APP_BASE_URL=os.getenv("APP_BASE_URL", "http://localhost:8000"),
        APP_TIMEZONE=os.getenv("APP_TIMEZONE", DEFAULT_TIMEZONE),
        COMPANY_NAME=os.getenv("COMPANY_NAME", "Minha Empresa"),
        COMPANY_WHATSAPP=os.getenv("COMPANY_WHATSAPP", "5511999999999"),
        MP_ACCESS_TOKEN=os.getenv("MP_ACCESS_TOKEN", ""),
        MP_WEBHOOK_SECRET=os.getenv("MP_WEBHOOK_SECRET", ""),
        ALERT_WINDOW_DAYS=int(os.getenv("ALERT_WINDOW_DAYS", "3")),
    )

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        alerts = []
        alert_summary = {"overdue": 0, "today": 0, "soon": 0}
        alert_window_days = app.config.get("ALERT_WINDOW_DAYS", 3)
        if current_user.is_authenticated:
            try:
                today = local_today()
                due_limit = today + timedelta(days=alert_window_days)
                base_query = Client.query.filter(Client.status != "cancelado", Client.status != "inativo")
                alerts = (
                    base_query.filter(Client.due_date <= due_limit)
                    .order_by(Client.due_date.asc(), Client.name.asc())
                    .limit(5)
                    .all()
                )
                alert_summary = {
                    "overdue": base_query.filter(Client.due_date < today).count(),
                    "today": base_query.filter(Client.due_date == today).count(),
                    "soon": base_query.filter(Client.due_date > today, Client.due_date <= due_limit).count(),
                }
            except Exception:
                pass

        return {
            "csrf_token": generate_csrf_token,
            "company_name": app.config["COMPANY_NAME"],
            "company_whatsapp": app.config["COMPANY_WHATSAPP"],
            "global_due_alerts": alerts,
            "global_alert_summary": alert_summary,
            "global_alert_window_days": alert_window_days,
        }

    @app.before_request
    def csrf_protect():
        validate_csrf()

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
