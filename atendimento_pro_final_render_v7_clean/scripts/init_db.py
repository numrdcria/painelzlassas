import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()


def migrate_attendances_if_needed() -> None:
    inspector = inspect(db.engine)
    if "attendances" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("attendances")}
    if {"contact_name", "contact_phone"}.issubset(columns):
        return

    if db.engine.url.get_backend_name().startswith("sqlite"):
        with db.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE attendances_new (
                    id INTEGER PRIMARY KEY,
                    client_id INTEGER,
                    user_id INTEGER NOT NULL,
                    contact_name VARCHAR(160) NOT NULL DEFAULT '',
                    contact_phone VARCHAR(30),
                    title VARCHAR(180) NOT NULL,
                    description TEXT NOT NULL,
                    attended_at DATETIME NOT NULL,
                    next_follow_up DATE,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY(client_id) REFERENCES clients (id),
                    FOREIGN KEY(user_id) REFERENCES users (id)
                )
            """))
            conn.execute(text("""
                INSERT INTO attendances_new (
                    id, client_id, user_id, contact_name, contact_phone, title, description,
                    attended_at, next_follow_up, created_at, updated_at
                )
                SELECT a.id, a.client_id, a.user_id,
                       COALESCE(c.name, ''), COALESCE(c.whatsapp, ''),
                       a.title, a.description, a.attended_at, a.next_follow_up, a.created_at, a.updated_at
                FROM attendances a
                LEFT JOIN clients c ON c.id = a.client_id
            """))
            conn.execute(text("DROP TABLE attendances"))
            conn.execute(text("ALTER TABLE attendances_new RENAME TO attendances"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_attendances_client_id ON attendances (client_id)"))
        print("[OK] tabela attendances atualizada")


def bootstrap() -> None:
    admin_name = os.getenv("ADMIN_NAME", "Administrador")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@empresa.com").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "123456")

    for attempt in range(1, 31):
        try:
            with app.app_context():
                db.create_all()
                migrate_attendances_if_needed()
                admin = User.query.filter_by(email=admin_email).first()
                if not admin:
                    admin = User(name=admin_name, email=admin_email, role="admin", active=True)
                    admin.set_password(admin_password)
                    db.session.add(admin)
                    db.session.commit()
                    print(f"[OK] admin criado: {admin_email}")
                else:
                    print(f"[OK] admin existente: {admin_email}")
            return
        except OperationalError as exc:
            if attempt == 30:
                raise
            print(f"[wait] banco indisponivel ({attempt}/30): {exc}")
            time.sleep(2)


if __name__ == "__main__":
    bootstrap()
    sys.exit(0)
