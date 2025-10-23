import os
import uuid
from fastapi import FastAPI, Request, Response, HTTPException
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env ANTES de importar serviços que dependem delas
load_dotenv()

from app.services.whatsapp_cliente import download_media
from app.services.transcription import transcribe_audio
from app.services.gladia_transcription import transcribe_audio_gladia
from app.services.nlp import extract_products_from_text
from app.services.pdf_generator import create_product_list_pdf
from app.services.twilio_client import send_pdf_message

# Configuração do FastAPI
app = FastAPI()

# Token para verificação do Webhook (deve ser o mesmo configurado na Meta)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Configuração do serviço de transcrição (elevenlabs ou gladia)
TRANSCRIPTION_SERVICE = os.getenv("TRANSCRIPTION_SERVICE", "elevenlabs")

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
    Recebe e processa as mensagens de áudio do WhatsApp.
    """
    data = await request.json()
    print("Received data:", data) # Log para debug

    try:
        # Extrai informações relevantes da mensagem
        changes = data["entry"][0]["changes"][0]
        if changes["field"] == "messages":
            message_data = changes["value"]["messages"][0]
            from_number = message_data["from"]
            
            # Verifica se a mensagem é do tipo áudio
            if message_data["type"] == "audio":
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

                # 3. Extrair a lista de produtos do texto
                products = extract_products_from_text(transcribed_text)
                print(f"Produtos Encontrados: {products}")
                
                if not products:
                    # Implementar lógica para avisar o usuário que nenhum produto foi encontrado
                    return Response(status_code=200)

                # 4. Gerar o arquivo PDF com a lista de produtos (FUNCIONALIDADE ORIGINAL)
                pdf_filename = f"lista_de_compras_{uuid.uuid4()}.pdf"
                pdf_path = f"app/temp/{pdf_filename}"
                create_product_list_pdf(products, pdf_path)

                # 5. Enviar o PDF de volta para o usuário via Twilio (com upload para Supabase)
                # Formatar número para o formato internacional (assumindo Brasil +55)
                formatted_number = f"whatsapp:+{from_number}" if not from_number.startswith("+") else from_number
                
                # Tentar enviar via Twilio com upload para Supabase, mas não falhar se der erro
                try:
                    twilio_success = send_pdf_message(formatted_number, pdf_path, f"Sua Lista de Compras + {products}")
                    if not twilio_success:
                        print("Aviso: Falha ao enviar via Twilio, mas continuando...")
                except Exception as twilio_error:
                    print(f"Aviso: Erro no Twilio: {twilio_error}")
                
                # Limpeza dos arquivos temporários
                try:
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except Exception as cleanup_error:
                    print(f"Aviso: Erro na limpeza: {cleanup_error}")

    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Retornar 200 para o WhatsApp não reenviar a notificação indefinidamente
        return Response(status_code=200)

    return Response(status_code=200)