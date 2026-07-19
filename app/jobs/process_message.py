"""Job assíncrono de processamento de mensagens WhatsApp."""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List

from app.core.config import Settings, get_settings
from app.domain.catalog_service import calc_budget_total, enrich_materials_with_prices
from app.domain.conversation import (
    ConversationSession,
    ConversationState,
    apply_quantity_change,
    apply_remove_material,
    build_confirmation_message,
    build_privacy_policy_message,
    build_processing_started_message,
    digits_only,
    format_destination_number,
    is_cancel_message,
    is_confirmation_message,
    is_delete_data_request,
    is_last_budget_request,
    is_privacy_policy_request,
    is_show_list_request,
    parse_add_material,
    parse_quantity_change,
    parse_remove_item,
)
from app.domain.materials import resolve_materials_from_text
from app.infrastructure.budget_repository import (
    delete_budgets_for_wa,
    get_last_budget,
    save_budget,
)
from app.infrastructure.messaging import send_pdf, send_text
from app.infrastructure.retry import with_retries
from app.infrastructure.store import StateStore, get_state_store
from app.services.gladia_transcription import transcribe_audio_gladia
from app.services.nlp_obras import extract_construction_context
from app.services.pdf_obras_generator import create_construction_budget_pdf
from app.services.transcription import transcribe_audio
from app.services.whatsapp_cliente import download_media

logger = logging.getLogger(__name__)


def _ensure_temp_dir() -> None:
    os.makedirs("app/temp", exist_ok=True)


def _generate_and_send_pdf(
    *,
    formatted_number: str,
    wa_id: str,
    materials: List[Dict[str, Any]],
    obra_type: str,
    settings: Settings,
    persist: bool = True,
) -> None:
    _ensure_temp_dir()
    materials = enrich_materials_with_prices(materials)
    total_amount = calc_budget_total(materials)
    pdf_path = f"app/temp/orcamento_obra_{uuid.uuid4()}.pdf"
    try:
        create_construction_budget_pdf(
            materials,
            obra_type,
            pdf_path,
            total_amount=total_amount,
        )
        logger.info("PDF gerado: %s | total=%.2f", pdf_path, total_amount)
        ok = send_pdf(
            formatted_number,
            pdf_path,
            f"Orçamento de Materiais - {obra_type.title()} ({len(materials)} itens) | Total R$ {total_amount:.2f}",
            settings,
        )
        if ok:
            logger.info("PDF enviado com sucesso")
            if persist:
                save_budget(
                    wa_id=wa_id,
                    obra_type=obra_type,
                    materials=materials,
                    total_amount=total_amount,
                    status="sent",
                )
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


def _handle_last_budget(wa_id: str, formatted_number: str, settings: Settings) -> bool:
    last = get_last_budget(wa_id)
    if not last:
        send_text(
            formatted_number,
            "Não encontrei orçamento anterior para este número. Envie um áudio para gerar um novo.",
            settings,
        )
        return True

    materials = last.get("materials") or []
    obra_type = last.get("obra_type") or "obra"
    send_text(formatted_number, "Reenviando seu último orçamento...", settings)
    _generate_and_send_pdf(
        formatted_number=formatted_number,
        wa_id=wa_id,
        materials=materials,
        obra_type=obra_type,
        settings=settings,
        persist=False,
    )
    return True


def _handle_lgpd(
    *,
    body: str,
    wa_id: str,
    formatted_number: str,
    store: StateStore,
    settings: Settings,
) -> bool:
    if is_privacy_policy_request(body):
        send_text(formatted_number, build_privacy_policy_message(), settings)
        return True

    if is_delete_data_request(body):
        store.clear_session(wa_id)
        deleted = delete_budgets_for_wa(wa_id)
        send_text(
            formatted_number,
            "Pronto. Apaguei a sessão deste chat"
            + (f" e {deleted} orçamento(ns) do histórico." if deleted else ".")
            + "\nSe quiser um novo orçamento, envie um áudio com os materiais.",
            settings,
        )
        return True

    return False


def _save_edited_session(
    *,
    store: StateStore,
    wa_id: str,
    materials: List[Dict[str, Any]],
    obra_type: str,
    texto: str,
    note: str,
    formatted_number: str,
    settings: Settings,
) -> None:
    materials = enrich_materials_with_prices(materials)
    session = ConversationSession(
        state=ConversationState.AWAITING_CONFIRMATION,
        materials=materials,
        obra_type=obra_type,
        texto=texto,
    )
    store.save_session(wa_id, session)
    send_text(
        formatted_number,
        f"{note}\n\n" + build_confirmation_message(materials, obra_type),
        settings,
    )


def _handle_list_edit(
    *,
    body: str,
    session: ConversationSession,
    wa_id: str,
    formatted_number: str,
    store: StateStore,
    settings: Settings,
) -> bool:
    """Handlers de edição enquanto aguarda confirmação. True se consumiu a mensagem."""
    if is_show_list_request(body):
        send_text(
            formatted_number,
            build_confirmation_message(session.materials, session.obra_type),
            settings,
        )
        return True

    remove_target = parse_remove_item(body)
    if remove_target:
        # Evita conflito com "apagar meus dados" (já tratado antes)
        updated, note = apply_remove_material(list(session.materials), remove_target)
        if note and "Não encontrei" in note:
            send_text(formatted_number, note, settings)
            return True
        if not updated:
            store.clear_session(wa_id)
            send_text(
                formatted_number,
                f"{note}\nA lista ficou vazia. Envie um novo áudio com os materiais.",
                settings,
            )
            return True
        _save_edited_session(
            store=store,
            wa_id=wa_id,
            materials=updated,
            obra_type=session.obra_type,
            texto=session.texto,
            note=note or "Lista atualizada.",
            formatted_number=formatted_number,
            settings=settings,
        )
        return True

    qty_change = parse_quantity_change(body)
    if qty_change:
        index, qty = qty_change
        updated, note = apply_quantity_change(list(session.materials), index, qty)
        if note and "Não encontrei" in note:
            send_text(formatted_number, note, settings)
            return True
        _save_edited_session(
            store=store,
            wa_id=wa_id,
            materials=updated,
            obra_type=session.obra_type,
            texto=session.texto,
            note=note or "Quantidade atualizada.",
            formatted_number=formatted_number,
            settings=settings,
        )
        return True

    add_text = parse_add_material(body)
    if add_text:
        ctx = extract_construction_context(add_text)
        new_items = enrich_materials_with_prices(ctx.get("materiais") or [])
        if not new_items:
            send_text(
                formatted_number,
                "Não consegui identificar o material para adicionar. "
                "Ex.: *adiciona 10 saco cimento*",
                settings,
            )
            return True
        merged = list(session.materials) + new_items
        names = ", ".join(i["material"] for i in new_items)
        _save_edited_session(
            store=store,
            wa_id=wa_id,
            materials=merged,
            obra_type=session.obra_type,
            texto=session.texto,
            note=f"Adicionei: {names}.",
            formatted_number=formatted_number,
            settings=settings,
        )
        return True

    return False


def _handle_text(
    *,
    body: str,
    wa_id: str,
    formatted_number: str,
    store: StateStore,
    settings: Settings,
) -> None:
    if _handle_lgpd(
        body=body,
        wa_id=wa_id,
        formatted_number=formatted_number,
        store=store,
        settings=settings,
    ):
        return

    if is_last_budget_request(body):
        _handle_last_budget(wa_id, formatted_number, settings)
        return

    session = store.get_session(wa_id)
    in_confirm = session.state in {
        ConversationState.AWAITING_CONFIRMATION,
        ConversationState.EDITING,
    }

    if in_confirm and is_confirmation_message(body):
        materials = session.materials
        obra_type = session.obra_type
        store.clear_session(wa_id)
        send_text(formatted_number, "Confirmado! Gerando o PDF do orçamento...", settings)
        _generate_and_send_pdf(
            formatted_number=formatted_number,
            wa_id=wa_id,
            materials=materials,
            obra_type=obra_type,
            settings=settings,
        )
        store.save_session(
            wa_id,
            ConversationSession(state=ConversationState.PDF_SENT),
        )
        return

    if in_confirm and is_cancel_message(body):
        store.clear_session(wa_id)
        send_text(
            formatted_number,
            "Orçamento cancelado. Envie um novo áudio com os materiais.",
            settings,
        )
        return

    if in_confirm and _handle_list_edit(
        body=body,
        session=session,
        wa_id=wa_id,
        formatted_number=formatted_number,
        store=store,
        settings=settings,
    ):
        return

    if in_confirm:
        send_text(
            formatted_number,
            "Há uma lista aguardando confirmação.\n"
            "Responda *SIM*, *NÃO*, ou edite com `remove N` / `qtd N=X` / `adiciona ...`.\n\n"
            + build_confirmation_message(session.materials, session.obra_type),
            settings,
        )
        return

    ok = send_text(
        formatted_number,
        "Envie um áudio descrevendo os materiais da obra para eu montar o orçamento.\n"
        "Se quiser, peça também: *último orçamento* ou *privacidade*.",
        settings,
    )
    if not ok:
        logger.error("Falha ao enviar resposta de orientação para %s", formatted_number)


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

        final_text, materials, obra_type, total = resolve_materials_from_text(transcribed, settings)
        logger.info("Materiais: %s | obra=%s | total=%.2f", materials, obra_type, total)

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

    # ACK imediato após claim (webhook já devolveu 200; usuário sente progresso)
    try:
        send_text(
            formatted_number,
            build_processing_started_message(msg_type if isinstance(msg_type, str) else None),
            settings,
        )
    except Exception:
        logger.exception("Falha ao enviar ACK de processamento para %s", formatted_number)

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
