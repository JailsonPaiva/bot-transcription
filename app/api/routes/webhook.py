"""Webhook Meta — endpoint fino (responde 200 rápido e enfileira job)."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

from app.core.config import get_settings
from app.core.security import read_and_verify_request
from app.jobs.process_message import process_incoming_message

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])


@router.get("/webhook")
async def verify_webhook(request: Request):
    settings = get_settings()
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.verify_token:
        logger.info("WEBHOOK_VERIFIED")
        return Response(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    settings = get_settings()

    try:
        raw_body = await read_and_verify_request(request, settings)
        data = json.loads(raw_body.decode("utf-8") or "{}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Payload inválido no webhook: %s", exc)
        return Response(status_code=200)

    logger.info("Webhook recebido (enfileirando processamento)")

    try:
        changes = data["entry"][0]["changes"][0]
        if changes.get("field") != "messages":
            return Response(status_code=200)

        value = changes.get("value") or {}
        if "messages" not in value:
            # status sent/delivered/failed
            return Response(status_code=200)

        message_data = value["messages"][0]
        background_tasks.add_task(process_incoming_message, message_data, settings)
    except Exception as exc:
        logger.exception("Falha ao enfileirar mensagem: %s", exc)

    # Meta exige ACK rápido — processamento pesado fica no background
    return Response(status_code=200)
