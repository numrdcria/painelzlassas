from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict

import requests
from flask import current_app

from app.models import Charge


API_BASE = "https://api.mercadopago.com"


class MercadoPagoError(RuntimeError):
    pass


def configured() -> bool:
    return bool(current_app.config.get("MP_ACCESS_TOKEN"))


def _headers() -> Dict[str, str]:
    token = current_app.config.get("MP_ACCESS_TOKEN")
    if not token:
        raise MercadoPagoError("Defina MP_ACCESS_TOKEN no .env para ativar o Mercado Pago.")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def create_checkout_preference(charge: Charge) -> Dict[str, Any]:
    base_url = current_app.config.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
    item_title = charge.description or f"Mensalidade - {charge.client.name}"
    payload = {
        "items": [
            {
                "id": str(charge.id),
                "title": item_title,
                "description": f"Cobranca do cliente {charge.client.name}",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(charge.amount),
            }
        ],
        "external_reference": charge.external_reference,
        "notification_url": f"{base_url}/integracoes/mercadopago/webhook",
        "back_urls": {
            "success": f"{base_url}/cobrancas/{charge.id}/retorno?status=success",
            "pending": f"{base_url}/cobrancas/{charge.id}/retorno?status=pending",
            "failure": f"{base_url}/cobrancas/{charge.id}/retorno?status=failure",
        },
        "auto_return": "approved",
        "metadata": {
            "charge_id": charge.id,
            "client_id": charge.client_id,
        },
        "payer": {
            "name": charge.client.name,
            "email": charge.client.email or "comprador@example.com",
        },
    }
    response = requests.post(
        f"{API_BASE}/checkout/preferences",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    if response.status_code not in (200, 201):
        raise MercadoPagoError(f"Mercado Pago retornou {response.status_code}: {response.text}")
    return response.json()


def get_payment(payment_id: str | int) -> Dict[str, Any]:
    response = requests.get(
        f"{API_BASE}/v1/payments/{payment_id}",
        headers=_headers(),
        timeout=30,
    )
    if response.status_code != 200:
        raise MercadoPagoError(f"Nao foi possivel consultar o pagamento {payment_id}: {response.text}")
    return response.json()


def validate_webhook_signature(signature_header: str | None, request_id: str | None, data_id: str | None) -> bool:
    secret = current_app.config.get("MP_WEBHOOK_SECRET") or ""
    if not secret:
        return True
    if not signature_header:
        return False

    parts = {}
    for chunk in signature_header.split(","):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        parts[key.strip()] = value.strip()

    ts = parts.get("ts")
    v1 = parts.get("v1")
    if not ts or not v1:
        return False

    manifest_bits = []
    if data_id:
        normalized_id = data_id.lower() if any(ch.isalpha() for ch in data_id) else data_id
        manifest_bits.append(f"id:{normalized_id};")
    if request_id:
        manifest_bits.append(f"request-id:{request_id};")
    if ts:
        manifest_bits.append(f"ts:{ts};")

    manifest = "".join(manifest_bits)
    generated = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated, v1)
