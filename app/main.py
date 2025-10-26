import os
import uuid
import hashlib
import time
from fastapi import FastAPI, Request, Response, HTTPException
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env ANTES de importar serviços que dependem delas
load_dotenv()

from app.services.whatsapp_cliente import download_media
from app.services.transcription import transcribe_audio
from app.services.gladia_transcription import transcribe_audio_gladia
from app.services.gemini_correction import correct_transcription_with_gemini, analyze_transcription_context
from app.services.nlp import extract_products_from_text
from app.services.nlp_obras import extract_construction_context, extract_materials_and_quantities
from app.services.pdf_generator import create_product_list_pdf
from app.services.pdf_obras_generator import create_construction_budget_pdf, create_simple_materials_list_pdf
from app.services.twilio_client import send_pdf_message, send_text_message

# Configuração do FastAPI
app = FastAPI()

# Token para verificação do Webhook (deve ser o mesmo configurado na Meta)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Configuração do serviço de transcrição (elevenlabs ou gladia)
TRANSCRIPTION_SERVICE = os.getenv("TRANSCRIPTION_SERVICE", "elevenlabs")

# Configuração do contexto de análise (compras ou obras)
ANALYSIS_CONTEXT = os.getenv("ANALYSIS_CONTEXT", "compras")  # "compras" ou "obras"

# Configuração para correção de transcrição com Gemini
ENABLE_GEMINI_CORRECTION = os.getenv("ENABLE_GEMINI_CORRECTION", "true").lower() == "true"

# Cache para evitar processamento duplicado
processed_messages = {}

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
            message_id = message_data["id"]
            
            # Verifica se a mensagem já foi processada (evita loop)
            message_hash = hashlib.md5(f"{message_id}_{from_number}".encode()).hexdigest()
            if message_hash in processed_messages:
                print(f"Mensagem {message_id} já processada, ignorando...")
                return Response(status_code=200)
            
            # Marca mensagem como processada
            processed_messages[message_hash] = time.time()
            
            # Limpa cache antigo (mais de 1 hora)
            current_time = time.time()
            # Remove itens antigos do cache
            keys_to_remove = [k for k, v in processed_messages.items() if current_time - v >= 3600]
            for key in keys_to_remove:
                del processed_messages[key]
            
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

                # 3. Corrigir transcrição com Gemini (se habilitado)
                final_text = transcribed_text
                if ENABLE_GEMINI_CORRECTION:
                    print("Aplicando correção de transcrição com Gemini...")
                    
                    # Primeiro, analisar o contexto automaticamente
                    context_analysis = analyze_transcription_context(transcribed_text)
                    detected_context = context_analysis.get("context", ANALYSIS_CONTEXT)
                    confidence = context_analysis.get("confidence", 0.0)
                    
                    print(f"Contexto detectado pelo Gemini: {detected_context} (confiança: {confidence})")
                    
                    # Corrigir o texto com base no contexto detectado
                    corrected_text = correct_transcription_with_gemini(transcribed_text, detected_context)
                    
                    if corrected_text:
                        final_text = corrected_text
                        print(f"Texto corrigido pelo Gemini: {final_text}")
                    else:
                        print("Falha na correção com Gemini, usando texto original")
                else:
                    print("Correção com Gemini desabilitada, usando texto original")

                # 4. Processar o texto baseado no contexto configurado
                if ANALYSIS_CONTEXT.lower() == "obras":
                    # Contexto de obras - extrair materiais de construção
                    construction_context = extract_construction_context(final_text)
                    materials = construction_context["materiais"]
                    obra_type = construction_context["tipo_obra"]
                    
                    print(f"Contexto de Obra Detectado: {obra_type}")
                    print(f"Materiais Encontrados: {materials}")
                    
                    if not materials:
                        # Enviar mensagem informando que nenhum material foi encontrado
                        try:
                            formatted_number = f"whatsapp:+{from_number}" if not from_number.startswith("+") else from_number
                            send_text_message(formatted_number, "Não foi possível identificar materiais de construção no áudio. Tente falar mais claramente sobre os materiais necessários.")
                        except Exception as e:
                            print(f"Erro ao enviar mensagem de erro: {e}")
                        return Response(status_code=200)
                    
                # 4. Gerar PDF de orçamento para obras
                pdf_filename = f"orcamento_obra_{uuid.uuid4()}.pdf"
                pdf_path = f"app/temp/{pdf_filename}"
                
                try:
                    create_construction_budget_pdf(materials, obra_type, pdf_path)
                    print(f"PDF gerado com sucesso: {pdf_path}")
                    
                    # 5. Enviar o PDF de volta para o usuário via Twilio
                    formatted_number = f"whatsapp:+{from_number}" if not from_number.startswith("+") else from_number
                    
                    twilio_success = send_pdf_message(formatted_number, pdf_path, f"Orçamento de Materiais - {obra_type.title()} ({len(materials)} itens)")
                    if twilio_success:
                        print("PDF enviado com sucesso via Twilio")
                    else:
                        print("Aviso: Falha ao enviar via Twilio")
                        # Enviar mensagem de texto como fallback
                        send_text_message(formatted_number, f"Orçamento gerado com {len(materials)} materiais, mas houve problema no envio do PDF. Tente novamente.")
                        
                except Exception as pdf_error:
                    print(f"Erro ao gerar PDF: {pdf_error}")
                    # Enviar mensagem de erro
                    formatted_number = f"whatsapp:+{from_number}" if not from_number.startswith("+") else from_number
                    send_text_message(formatted_number, f"Erro ao gerar orçamento. Materiais identificados: {', '.join([m['material'] for m in materials])}")
                
            else:
                # Contexto original de compras - extrair produtos
                products = extract_products_from_text(final_text)
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