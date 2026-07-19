import os
import uuid
import hashlib
import time
import re
from fastapi import FastAPI, Request, Response, HTTPException
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env ANTES de importar serviços que dependem delas
load_dotenv(override=True)

from app.services.whatsapp_cliente import download_media
from app.services.transcription import transcribe_audio
from app.services.gladia_transcription import transcribe_audio_gladia
from app.services.gemini_correction import (
    correct_transcription_with_gemini,
    extract_materials_json_with_gemini,
)
from app.services.nlp_obras import (
    extract_construction_context,
    format_materials_for_message,
)
from app.services.pdf_obras_generator import create_construction_budget_pdf
from app.services.twilio_client import send_pdf_message, send_text_message
from app.services.whatsapp_api_client import send_whatsapp_pdf_message, send_whatsapp_text_message

# Configuração do FastAPI
app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
TRANSCRIPTION_SERVICE = os.getenv("TRANSCRIPTION_SERVICE", "elevenlabs")
ENABLE_GEMINI_CORRECTION = os.getenv("ENABLE_GEMINI_CORRECTION", "true").lower() == "true"
MESSAGE_SERVICE = os.getenv("MESSAGE_SERVICE", "twilio").lower()

# Cache para evitar processamento duplicado
processed_messages = {}

# Confirmações pendentes por número: { materials, obra_type, created_at }
pending_confirmations = {}
CONFIRMATION_TTL_SECONDS = 30 * 60


def send_message_with_configured_service(to_number: str, message_text: str) -> bool:
    if MESSAGE_SERVICE == "whatsapp":
        return send_whatsapp_text_message(to_number, message_text)
    return send_text_message(to_number, message_text)


def send_pdf_with_configured_service(to_number: str, pdf_path: str, caption: str) -> bool:
    if MESSAGE_SERVICE == "whatsapp":
        return send_whatsapp_pdf_message(to_number, pdf_path, caption)
    return send_pdf_message(to_number, pdf_path, caption)


def format_destination_number(from_number: str) -> str:
    digits = "".join(ch for ch in from_number.replace("whatsapp:", "") if ch.isdigit())
    if MESSAGE_SERVICE == "whatsapp":
        return digits
    return f"whatsapp:+{digits}"


def cleanup_pending_confirmations():
    now = time.time()
    expired = [k for k, v in pending_confirmations.items() if now - v.get("created_at", 0) >= CONFIRMATION_TTL_SECONDS]
    for key in expired:
        del pending_confirmations[key]


def is_confirmation_message(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    normalized = re.sub(r"[!?.]", "", normalized)
    confirm_words = {
        "sim",
        "s",
        "ok",
        "okay",
        "confirmo",
        "confirma",
        "confirmar",
        "pode",
        "pode gerar",
        "gerar",
        "gerar pdf",
        "isso",
        "correto",
        "certo",
        "yes",
        "y",
    }
    return normalized in confirm_words


def is_cancel_message(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    normalized = re.sub(r"[!?.]", "", normalized)
    cancel_words = {
        "nao",
        "não",
        "n",
        "cancelar",
        "cancela",
        "corrigir",
        "errado",
        "refazer",
    }
    return normalized in cancel_words


def build_confirmation_message(materials, obra_type: str) -> str:
    lista = format_materials_for_message(materials)
    return (
        f"Identifiquei estes materiais para *{obra_type}*:\n\n"
        f"{lista}\n\n"
        "Responda *SIM* para gerar o PDF do orçamento.\n"
        "Responda *NÃO* para cancelar e enviar outro áudio."
    )


def generate_and_send_pdf(formatted_number: str, materials, obra_type: str) -> None:
    pdf_filename = f"orcamento_obra_{uuid.uuid4()}.pdf"
    pdf_path = f"app/temp/{pdf_filename}"
    try:
        create_construction_budget_pdf(materials, obra_type, pdf_path)
        print(f"PDF gerado com sucesso: {pdf_path}")

        service_name = "WhatsApp API" if MESSAGE_SERVICE == "whatsapp" else "Twilio"
        print(f"Enviando PDF via {service_name}...")

        send_success = send_pdf_with_configured_service(
            formatted_number,
            pdf_path,
            f"Orçamento de Materiais - {obra_type.title()} ({len(materials)} itens)",
        )
        if send_success:
            print(f"PDF enviado com sucesso via {service_name}")
        else:
            print(f"Aviso: Falha ao enviar via {service_name}")
            send_message_with_configured_service(
                formatted_number,
                f"Orçamento gerado com {len(materials)} materiais, mas houve problema no envio do PDF. Tente novamente.",
            )
    except Exception as pdf_error:
        print(f"Erro ao gerar PDF: {pdf_error}")
        send_message_with_configured_service(
            formatted_number,
            f"Erro ao gerar orçamento. Materiais identificados: {', '.join([m['material'] for m in materials])}",
        )
    finally:
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception as cleanup_error:
                print(f"Aviso: Erro na limpeza de {pdf_path}: {cleanup_error}")


def resolve_materials_from_text(transcribed_text: str):
    """
    Prioriza Gemini JSON validado; cai para NLP regex se necessário.
    """
    obra_type = "obra"
    materials = []
    final_text = transcribed_text

    if ENABLE_GEMINI_CORRECTION:
        print("Extraindo materiais com Gemini JSON...")
        gemini_result = extract_materials_json_with_gemini(transcribed_text)
        if gemini_result and gemini_result.get("materiais"):
            materials = gemini_result["materiais"]
            obra_type = gemini_result.get("tipo_obra") or "obra"
            if gemini_result.get("texto_corrigido"):
                final_text = gemini_result["texto_corrigido"]
            print(f"Materiais via Gemini JSON: {materials}")
            return final_text, materials, obra_type

        print("Gemini JSON sem materiais válidos; tentando correção + NLP...")
        corrected = correct_transcription_with_gemini(transcribed_text, "obras")
        if corrected:
            final_text = corrected

    construction_context = extract_construction_context(final_text)
    materials = construction_context["materiais"]
    obra_type = construction_context["tipo_obra"]
    print(f"Materiais via NLP: {materials}")
    return final_text, materials, obra_type


@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED")
        return Response(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Fluxo:
    1) Áudio -> extrai materiais -> pede confirmação
    2) Texto SIM -> gera PDF
    3) Texto NÃO -> cancela
    """
    data = await request.json()
    print("Received data:", data)

    audio_path = None

    try:
        changes = data["entry"][0]["changes"][0]
        if changes["field"] != "messages":
            return Response(status_code=200)

        value = changes["value"]
        if "messages" not in value:
            return Response(status_code=200)

        message_data = value["messages"][0]
        from_number = message_data["from"]
        message_id = message_data["id"]

        message_hash = hashlib.md5(f"{message_id}_{from_number}".encode()).hexdigest()
        if message_hash in processed_messages:
            print(f"Mensagem {message_id} já processada, ignorando...")
            return Response(status_code=200)

        processed_messages[message_hash] = time.time()
        current_time = time.time()
        for key in [k for k, v in processed_messages.items() if current_time - v >= 3600]:
            del processed_messages[key]

        cleanup_pending_confirmations()
        formatted_number = format_destination_number(from_number)
        pending_key = "".join(ch for ch in from_number if ch.isdigit())

        # ---- Texto: confirmação / cancelamento / ajuda ----
        if message_data["type"] == "text":
            body = (message_data.get("text") or {}).get("body", "")
            pending = pending_confirmations.get(pending_key)

            if pending and is_confirmation_message(body):
                materials = pending["materials"]
                obra_type = pending["obra_type"]
                del pending_confirmations[pending_key]
                send_message_with_configured_service(
                    formatted_number,
                    "Confirmado! Gerando o PDF do orçamento...",
                )
                generate_and_send_pdf(formatted_number, materials, obra_type)
                return Response(status_code=200)

            if pending and is_cancel_message(body):
                del pending_confirmations[pending_key]
                send_message_with_configured_service(
                    formatted_number,
                    "Orçamento cancelado. Envie um novo áudio com os materiais.",
                )
                return Response(status_code=200)

            if pending:
                send_message_with_configured_service(
                    formatted_number,
                    "Há uma lista aguardando confirmação.\n"
                    "Responda *SIM* para gerar o PDF ou *NÃO* para cancelar.\n\n"
                    + build_confirmation_message(pending["materials"], pending["obra_type"]),
                )
                return Response(status_code=200)

            send_message_with_configured_service(
                formatted_number,
                "Envie um áudio descrevendo os materiais da obra para eu montar o orçamento.",
            )
            return Response(status_code=200)

        # ---- Áudio: extrai e pede confirmação ----
        if message_data["type"] != "audio":
            send_message_with_configured_service(
                formatted_number,
                "Envie um áudio descrevendo os materiais da obra para eu gerar o orçamento em PDF.",
            )
            return Response(status_code=200)

        audio_id = message_data["audio"]["id"]
        audio_path = f"app/temp/{audio_id}.ogg"
        if not download_media(audio_id, audio_path):
            raise HTTPException(status_code=500, detail="Failed to download audio")

        if TRANSCRIPTION_SERVICE.lower() == "gladia":
            print("Usando Gladia para transcrição...")
            transcribed_text = transcribe_audio_gladia(audio_path)
        else:
            print("Usando ElevenLabs para transcrição...")
            transcribed_text = transcribe_audio(audio_path)

        if not transcribed_text:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio")
        print(f"Texto Transcrito ({TRANSCRIPTION_SERVICE}): {transcribed_text}")

        final_text, materials, obra_type = resolve_materials_from_text(transcribed_text)
        print(f"Texto final: {final_text}")
        print(f"Contexto de Obra Detectado: {obra_type}")
        print(f"Materiais Encontrados: {materials}")

        if not materials:
            send_message_with_configured_service(
                formatted_number,
                "Não foi possível identificar materiais de construção no áudio. "
                "Tente falar mais claramente sobre os materiais necessários.",
            )
            return Response(status_code=200)

        pending_confirmations[pending_key] = {
            "materials": materials,
            "obra_type": obra_type,
            "created_at": time.time(),
            "texto": final_text,
        }
        send_message_with_configured_service(
            formatted_number,
            build_confirmation_message(materials, obra_type),
        )

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return Response(status_code=200)
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception as cleanup_error:
                print(f"Aviso: Erro na limpeza de {audio_path}: {cleanup_error}")

    return Response(status_code=200)
