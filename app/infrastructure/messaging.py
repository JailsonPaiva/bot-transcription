"""Envio de mensagens (Twilio / WhatsApp)."""
from __future__ import annotations

from app.core.config import Settings
from app.services.twilio_client import send_pdf_message, send_text_message
from app.services.whatsapp_api_client import (
    send_whatsapp_pdf_message,
    send_whatsapp_text_message,
)


def send_text(to_number: str, message: str, settings: Settings) -> bool:
    if settings.message_service_normalized == "whatsapp":
        return send_whatsapp_text_message(to_number, message)
    return send_text_message(to_number, message)


def send_pdf(to_number: str, pdf_path: str, caption: str, settings: Settings) -> bool:
    if settings.message_service_normalized == "whatsapp":
        return send_whatsapp_pdf_message(to_number, pdf_path, caption)
    return send_pdf_message(to_number, pdf_path, caption)
