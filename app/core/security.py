"""Segurança do webhook Meta."""
import hashlib
import hmac
import logging
from typing import Optional

from fastapi import HTTPException, Request

from app.core.config import Settings

logger = logging.getLogger(__name__)


def verify_meta_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    settings: Settings,
) -> None:
    """
    Valida X-Hub-Signature-256 (HMAC SHA-256 do body com META_APP_SECRET).
    """
    if not settings.require_webhook_signature:
        return

    if not settings.meta_app_secret:
        raise HTTPException(status_code=500, detail="META_APP_SECRET não configurado")

    if not signature_header:
        raise HTTPException(status_code=403, detail="Missing X-Hub-Signature-256")

    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Invalid signature format")

    expected = hmac.new(
        settings.meta_app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header.split("=", 1)[1]

    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")


async def read_and_verify_request(request: Request, settings: Settings) -> bytes:
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    verify_meta_signature(raw_body, signature, settings)
    return raw_body
