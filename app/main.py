import os
import uuid
import hashlib
import time
from fastapi import FastAPI, Request, Response, HTTPException
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env ANTES de importar serviços que dependem delas
load_dotenv(override=True)

from app.services.whatsapp_cliente import download_media
from app.services.transcription import transcribe_audio
from app.services.gladia_transcription import transcribe_audio_gladia
from app.services.gemini_correction import correct_transcription_with_gemini
from app.services.nlp_obras import extract_construction_context
from app.services.pdf_obras_generator import create_construction_budget_pdf
from app.services.twilio_client import send_pdf_message, send_text_message
from app.services.whatsapp_api_client import send_whatsapp_pdf_message, send_whatsapp_text_message

# Configuração do FastAPI
app = FastAPI()

# Token para verificação do Webhook (deve ser o mesmo configurado na Meta)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Configuração do serviço de transcrição (elevenlabs ou gladia)
TRANSCRIPTION_SERVICE = os.getenv("TRANSCRIPTION_SERVICE", "elevenlabs")

# Configuração para correção de transcrição com Gemini
ENABLE_GEMINI_CORRECTION = os.getenv("ENABLE_GEMINI_CORRECTION", "true").lower() == "true"

# Configuração do serviço de envio de mensagens (twilio ou whatsapp)
MESSAGE_SERVICE = os.getenv("MESSAGE_SERVICE", "twilio").lower()

# Cache para evitar processamento duplicado
processed_messages = {}


def send_message_with_configured_service(to_number: str, message_text: str) -> bool:
    """
    Envia mensagem de texto usando o serviço configurado (Twilio ou WhatsApp API).
    """
    if MESSAGE_SERVICE == "whatsapp":
        return send_whatsapp_text_message(to_number, message_text)
    else:  # twilio (padrão)
        return send_text_message(to_number, message_text)


def send_pdf_with_configured_service(to_number: str, pdf_path: str, caption: str) -> bool:
    """
    Envia PDF usando o serviço configurado (Twilio ou WhatsApp API).
    """
    if MESSAGE_SERVICE == "whatsapp":
        return send_whatsapp_pdf_message(to_number, pdf_path, caption)
    else:  # twilio (padrão)
        return send_pdf_message(to_number, pdf_path, caption)


def format_destination_number(from_number: str) -> str:
    """
    Normaliza o número do destinatário conforme o serviço de envio.
    Meta Cloud API: apenas dígitos (ex.: 5565996047289).
    Twilio: prefixo whatsapp:+.
    """
    digits = "".join(ch for ch in from_number.replace("whatsapp:", "") if ch.isdigit())
    if MESSAGE_SERVICE == "whatsapp":
        return digits
    return f"whatsapp:+{digits}"


@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verificação do endpoint do webhook pela Meta.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED")
        return Response(content=challenge, status_code=200)
    else:
        raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Recebe e processa as mensagens de áudio do WhatsApp (orçamento de obras).
    """
    data = await request.json()
    print("Received data:", data)

    audio_path = None
    pdf_path = None

    try:
        changes = data["entry"][0]["changes"][0]
        if changes["field"] != "messages":
            return Response(status_code=200)

        value = changes["value"]
        # Ignora webhooks de status (sent/delivered/failed) sem mensagem
        if "messages" not in value:
            return Response(status_code=200)

        message_data = value["messages"][0]
        from_number = message_data["from"]
        message_id = message_data["id"]

        # Evita processamento duplicado
        message_hash = hashlib.md5(f"{message_id}_{from_number}".encode()).hexdigest()
        if message_hash in processed_messages:
            print(f"Mensagem {message_id} já processada, ignorando...")
            return Response(status_code=200)

        processed_messages[message_hash] = time.time()

        current_time = time.time()
        keys_to_remove = [k for k, v in processed_messages.items() if current_time - v >= 3600]
        for key in keys_to_remove:
            del processed_messages[key]

        formatted_number = format_destination_number(from_number)

        if message_data["type"] != "audio":
            send_message_with_configured_service(
                formatted_number,
                "Envie um áudio descrevendo os materiais da obra para eu gerar o orçamento em PDF.",
            )
            return Response(status_code=200)

        audio_id = message_data["audio"]["id"]

        # 1. Baixar o arquivo de áudio
        audio_path = f"app/temp/{audio_id}.ogg"
        if not download_media(audio_id, audio_path):
            raise HTTPException(status_code=500, detail="Failed to download audio")

        # 2. Transcrever o áudio para texto
        if TRANSCRIPTION_SERVICE.lower() == "gladia":
            print("Usando Gladia para transcrição...")
            transcribed_text = transcribe_audio_gladia(audio_path)
        else:
            print("Usando ElevenLabs para transcrição...")
            transcribed_text = transcribe_audio(audio_path)

        if not transcribed_text:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio")
        print(f"Texto Transcrito ({TRANSCRIPTION_SERVICE}): {transcribed_text}")

        # 3. Corrigir transcrição com Gemini (se habilitado)
        final_text = transcribed_text
        if ENABLE_GEMINI_CORRECTION:
            print("Aplicando correção de transcrição com Gemini...")
            corrected_text = correct_transcription_with_gemini(transcribed_text, "obras")
            if corrected_text:
                final_text = corrected_text
                print(f"Texto corrigido pelo Gemini: {final_text}")
            else:
                print("Falha na correção com Gemini, usando texto original")
        else:
            print("Correção com Gemini desabilitada, usando texto original")

        # 4. Extrair materiais de construção
        construction_context = extract_construction_context(final_text)
        materials = construction_context["materiais"]
        obra_type = construction_context["tipo_obra"]

        print(f"Contexto de Obra Detectado: {obra_type}")
        print(f"Materiais Encontrados: {materials}")

        if not materials:
            send_message_with_configured_service(
                formatted_number,
                "Não foi possível identificar materiais de construção no áudio. "
                "Tente falar mais claramente sobre os materiais necessários.",
            )
            return Response(status_code=200)

        # 5. Gerar PDF de orçamento
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

    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Retornar 200 para o WhatsApp não reenviar a notificação indefinidamente
        return Response(status_code=200)
    finally:
        for path in (audio_path, pdf_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as cleanup_error:
                    print(f"Aviso: Erro na limpeza de {path}: {cleanup_error}")

    return Response(status_code=200)
