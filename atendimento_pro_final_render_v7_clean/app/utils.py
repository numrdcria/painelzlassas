from __future__ import annotations

import calendar
import hmac
import os
import re
import secrets
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from typing import Callable, Optional
from urllib.parse import quote
from zoneinfo import ZoneInfo

from flask import abort, current_app, redirect, request, session, url_for
from flask_login import current_user


DEFAULT_TIMEZONE = "America/Sao_Paulo"
ENTRY_SEQUENCE = ["entrada", "saida_almoco", "volta_almoco", "saida"]
ENTRY_LABELS = {
    "entrada": "Entrada",
    "saida_almoco": "Saida para almoco",
    "volta_almoco": "Volta do almoco",
    "saida": "Saida final",
}
STATUS_BADGES = {
    "ativo": "success",
    "inativo": "secondary",
    "atrasado": "danger",
    "cancelado": "dark",
    "pendente": "warning",
    "pago": "success",
}


def get_timezone_name() -> str:
    try:
        configured = current_app.config.get("APP_TIMEZONE")
        if configured:
            return str(configured)
    except RuntimeError:
        pass
    return os.getenv("APP_TIMEZONE", DEFAULT_TIMEZONE)



def get_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(get_timezone_name())
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)



def local_now() -> datetime:
    return datetime.now(get_timezone()).replace(tzinfo=None, microsecond=0)



def local_today() -> date:
    return local_now().date()



def local_day_bounds(target_date: date | None = None) -> tuple[datetime, datetime]:
    day = target_date or local_today()
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    return start, end



def parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()



def parse_datetime_local(value: str) -> Optional[datetime]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M")



def parse_decimal(value: str | None, default: str = "0") -> Decimal:
    raw = (value or default).strip().replace("R$", "").replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", ".")
    try:
        return Decimal(raw or default)
    except InvalidOperation:
        return Decimal(default)



def add_one_month(original: date) -> date:
    month = original.month + 1
    year = original.year
    if month == 13:
        month = 1
        year += 1
    max_day = calendar.monthrange(year, month)[1]
    return original.replace(year=year, month=month, day=min(original.day, max_day))



def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if digits and not digits.startswith("55") and len(digits) in (10, 11):
        digits = f"55{digits}"
    return digits



def whatsapp_link(phone: str, message: str = "") -> str:
    digits = normalize_phone(phone)
    if not digits:
        return "#"
    base = f"https://wa.me/{digits}"
    if message:
        return f"{base}?text={quote(message)}"
    return base



def currency_br(value: Decimal | float | int | None) -> str:
    if value is None:
        value = Decimal("0.00")
    decimal_value = Decimal(value)
    formatted = f"{decimal_value:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")



def date_br(value: date | datetime | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d/%m/%Y")



def datetime_br(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%d/%m/%Y %H:%M")



def first_name(full_name: str | None) -> str:
    if not full_name:
        return "cliente"
    return (full_name or "cliente").strip().split()[0]



def client_due_state(due_date: date) -> str:
    today = local_today()
    if due_date < today:
        return "atrasado"
    return "ativo"



def days_until_due(due_date: date) -> int:
    return (due_date - local_today()).days



def due_label(due_date: date) -> str:
    days = days_until_due(due_date)
    if days < 0:
        return f"Atrasado ha {abs(days)} dia(s)"
    if days == 0:
        return "Vence hoje"
    if days == 1:
        return "Vence amanha"
    return f"Vence em {days} dia(s)"



def due_badge(due_date: date) -> str:
    days = days_until_due(due_date)
    if days < 0:
        return "danger"
    if days <= 3:
        return "warning"
    return "success"



def renewal_message(client, charge=None, company_name: str | None = None) -> str:
    amount = getattr(charge, "amount", None) or getattr(client, "monthly_fee", Decimal("0.00"))
    due_date = getattr(charge, "due_date", None) or getattr(client, "due_date", None)
    service_name = getattr(client, "service_name", "seu servico")
    payment_link = getattr(charge, "mercado_pago_init_point", None)
    company = company_name or current_app.config.get("COMPANY_NAME", "nossa equipe")

    message = (
        f"Ola, {first_name(getattr(client, 'name', 'cliente'))}! "
        f"Passando para lembrar da renovacao do servico {service_name}. "
        f"O valor desta renovacao e {currency_br(amount)}"
    )
    if due_date:
        message += f" com vencimento em {date_br(due_date)}."
    else:
        message += "."
    if payment_link:
        message += f"\n\nSegue o link para pagamento: {payment_link}"
    message += f"\n\nQualquer duvida, fico a disposicao.\n{company}"
    return message



def roles_required(*roles: str) -> Callable:
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator



def generate_csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_hex(32)
        session["_csrf_token"] = token
    return token



def validate_csrf() -> None:
    if request.method != "POST":
        return
    session_token = session.get("_csrf_token")
    form_token = request.form.get("_csrf_token") or request.headers.get("X-CSRFToken")
    if not session_token or not form_token or not hmac.compare_digest(str(session_token), str(form_token)):
        abort(400, description="Falha na validacao CSRF.")



def next_entry_type(entry_types_today: list[str]) -> str:
    for expected in ENTRY_SEQUENCE:
        if entry_types_today.count(expected) < 1:
            return expected
    return ENTRY_SEQUENCE[0]
