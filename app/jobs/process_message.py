"""Job assíncrono de processamento de mensagens WhatsApp."""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict

from app.core.config import Settings, get_settings
from app.domain.conversation import (
    ConversationSession,
    ConversationState,
    build_confirmation_message,
    digits_only,
    format_destination_number,
    is_cancel_message,
    is_confirmation_message,
)
from app.domain.materials import resolve_materials_from_text
from app.infrastructure.messaging import send_pdf, send_text
from app.infrastructure.retry import with_retries
from app.infrastructure.store import StateStore, get_state_store
from app.services.gladia_transcription import transcribe_audio_gladia
from app.services.pdf_obras_generator import create_construction_budget_pdf
from app.services.transcription import transcribe_audio
from app.services.whatsapp_cliente import download_media

logger = logging.getLogger(__name__)


def _ensure_temp_dir() -> None:
    os.makedirs("app/temp", exist_ok=True)


def _generate_and_send_pdf(
    formatted_number: str,
    materials,
    obra_type: str,
    settings: Settings,
) -> None:
    _ensure_temp_dir()
    pdf_path = f"app/temp/orcamento_obra_{uuid.uuid4()}.pdf"
    try:
        create_construction_budget_pdf(materials, obra_type, pdf_path)
        logger.info("PDF gerado: %s", pdf_path)
        ok = send_pdf(
            formatted_number,
            pdf_path,
            f"Orçamento de Materiais - {obra_type.title()} ({len(materials)} itens)",
            settings,
        )
        if ok:
            logger.info("PDF enviado com sucesso")
        else:
            send_text(
                formatted_number,
                f"Orçamento gerado com {len(materials)} materiais, mas houve problema no envio do PDF. Tente novamente.",
                settings,
            )
    except Exception as exc:
        logger.exception("Erro ao gerar/enviar PDF: %s", exc)
        send_text(
            formatted_number,
            f"Erro ao gerar orçamento. Materiais: {', '.join(m['material'] for m in materials)}",
            settings,
        )
    finally:
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                pass


def _handle_text(
    *,
    body: str,
    wa_id: str,
    formatted_number: str,
    store: StateStore,
    settings: Settings,
) -> None:
    session = store.get_session(wa_id)

    if session.state == ConversationState.AWAITING_CONFIRMATION and is_confirmation_message(body):
        materials = session.materials
        obra_type = session.obra_type
        store.clear_session(wa_id)
        send_text(formatted_number, "Confirmado! Gerando o PDF do orçamento...", settings)
        _generate_and_send_pdf(formatted_number, materials, obra_type, settings)
        store.save_session(
            wa_id,
            ConversationSession(state=ConversationState.PDF_SENT),
        )
        return

    if session.state == ConversationState.AWAITING_CONFIRMATION and is_cancel_message(body):
        store.clear_session(wa_id)
        send_text(
            formatted_number,
            "Orçamento cancelado. Envie um novo áudio com os materiais.",
            settings,
        )
        return

    if session.state == ConversationState.AWAITING_CONFIRMATION:
        send_text(
            formatted_number,
            "Há uma lista aguardando confirmação.\n"
            "Responda *SIM* para gerar o PDF ou *NÃO* para cancelar.\n\n"
            + build_confirmation_message(session.materials, session.obra_type),
            settings,
        )
        return

    send_text(
        formatted_number,
        "Envie um áudio descrevendo os materiais da obra para eu montar o orçamento.",
        settings,
    )


def _handle_audio(
    *,
    audio_id: str,
    wa_id: str,
    formatted_number: str,
    store: StateStore,
    settings: Settings,
) -> None:
    if not store.check_audio_rate_limit(wa_id, settings.max_audio_per_hour):
        send_text(
            formatted_number,
            "Você atingiu o limite de áudios por hora. Tente novamente mais tarde.",
            settings,
        )
        return

    _ensure_temp_dir()
    audio_path = f"app/temp/{audio_id}.ogg"

    try:
        def _download() -> bool:
            ok = download_media(audio_id, audio_path)
            if not ok:
                raise RuntimeError("download_media retornou False")
            return ok

        try:
            with_retries("download_media", _download, settings)
        except Exception:
            send_text(
                formatted_number,
                "Não consegui baixar o áudio. Pode enviar novamente?",
                settings,
            )
            return

        def _transcribe() -> str:
            if settings.transcription_service_normalized == "gladia":
                text = transcribe_audio_gladia(audio_path) or ""
            else:
                text = transcribe_audio(audio_path) or ""
            if not text:
                raise RuntimeError("transcrição vazia")
            return text

        try:
            transcribed = with_retries("transcription", _transcribe, settings)
        except Exception:
            send_text(
                formatted_number,
                "Não consegui entender o áudio. Pode repetir falando os materiais com clareza?",
                settings,
            )
            return

        logger.info("Texto transcrito: %s", transcribed)

        final_text, materials, obra_type = resolve_materials_from_text(transcribed, settings)
        logger.info("Materiais: %s | obra=%s", materials, obra_type)

        if not materials:
            send_text(
                formatted_number,
                "Não foi possível identificar materiais de construção no áudio. "
                "Tente falar mais claramente sobre os materiais necessários.",
                settings,
            )
            return

        session = ConversationSession(
            state=ConversationState.AWAITING_CONFIRMATION,
            materials=materials,
            obra_type=obra_type,
            texto=final_text,
        )
        store.save_session(wa_id, session)
        send_text(
            formatted_number,
            build_confirmation_message(materials, obra_type),
            settings,
        )
    except Exception as exc:
        logger.exception("Falha no processamento de áudio: %s", exc)
        send_text(
            formatted_number,
            "Tive um problema ao processar seu áudio. Pode tentar novamente em instantes?",
            settings,
        )
    finally:
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass


def process_incoming_message(message_data: Dict[str, Any], settings: Settings | None = None) -> None:
    """
    Processa uma mensagem já validada/extraída do webhook.
    Projetado para rodar em BackgroundTasks (Sprint 1) ou worker Redis/RQ (próximo passo).
    """
    settings = settings or get_settings()
    store = get_state_store(settings)

    from_number = message_data["from"]
    message_id = message_data["id"]
    wa_id = digits_only(from_number)
    formatted_number = format_destination_number(
        from_number,
        settings.message_service_normalized,
    )

    if not store.claim_message(message_id, from_number):
        logger.info("Mensagem %s já processada — ignorando", message_id)
        return

    msg_type = message_data.get("type")
    try:
        if msg_type == "text":
            body = (message_data.get("text") or {}).get("body", "")
            _handle_text(
                body=body,
                wa_id=wa_id,
                formatted_number=formatted_number,
                store=store,
                settings=settings,
            )
            return

        if msg_type == "audio":
            audio_id = message_data["audio"]["id"]
            _handle_audio(
                audio_id=audio_id,
                wa_id=wa_id,
                formatted_number=formatted_number,
                store=store,
                settings=settings,
            )
            return

        send_text(
            formatted_number,
            "Envie um áudio descrevendo os materiais da obra para eu gerar o orçamento em PDF.",
            settings,
        )
    except Exception as exc:
        logger.exception("Erro no job de mensagem: %s", exc)
        try:
            send_text(
                formatted_number,
                "Ocorreu um erro interno. Tente novamente em alguns minutos.",
                settings,
            )
        except Exception:
            pass
