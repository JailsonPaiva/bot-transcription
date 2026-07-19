import os
import requests
import json
from typing import Optional

# Importar wrapper local se disponível
try:
    from app.services.local_whatsapp_wrapper import (
        send_local_whatsapp_text_message,
        send_local_whatsapp_document_message,
        send_local_whatsapp_pdf_message,
        get_local_whatsapp_status
    )
    LOCAL_WRAPPER_AVAILABLE = True
except ImportError:
    LOCAL_WRAPPER_AVAILABLE = False

def should_use_local_wrapper() -> bool:
    """
    Verifica se deve usar o wrapper local em vez da API real.
    """
    if not LOCAL_WRAPPER_AVAILABLE:
        return False
    
    local_enabled = os.getenv("LOCAL_WHATSAPP_ENABLED", "false").lower() == "true"
    return local_enabled

def get_whatsapp_api_credentials():
    """
    Obtém as credenciais da WhatsApp Business API das variáveis de ambiente.
    """
    access_token = os.getenv("META_WA_TOKEN")
    phone_number_id = os.getenv("WA_PHONE_NUMBER_ID")
    
    if not all([access_token, phone_number_id]):
        print("[Erro] Credenciais da WhatsApp Business API não encontradas nas variáveis de ambiente.")
        print("Necessário: META_WA_TOKEN, WA_PHONE_NUMBER_ID")
        return None, None
    
    return access_token, phone_number_id


def normalize_whatsapp_to_number(to_number: str) -> str:
    """Cloud API da Meta espera apenas dígitos (ex.: 5565996047289)."""
    return "".join(ch for ch in to_number.replace("whatsapp:", "") if ch.isdigit())

def send_whatsapp_text_message(to_number: str, message_text: str) -> bool:
    """
    Envia uma mensagem de texto via WhatsApp Business API ou wrapper local.
    
    Args:
        to_number: Número de telefone de destino (formato internacional)
        message_text: Texto da mensagem
        
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    # Verificar se deve usar wrapper local
    if should_use_local_wrapper():
        print("[WHATSAPP API] Usando wrapper local para envio de mensagem")
        return send_local_whatsapp_text_message(to_number, message_text)
    
    # Usar API real
    access_token, phone_number_id = get_whatsapp_api_credentials()
    
    if not all([access_token, phone_number_id]):
        print("[Erro] Não foi possível enviar mensagem: credenciais da WhatsApp API ausentes.")
        return False

    to_number = normalize_whatsapp_to_number(to_number)
    
    try:
        # URL da API do WhatsApp Business
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        
        # Headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Payload da mensagem
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {
                "body": message_text
            }
        }
        
        print(f"Enviando mensagem de texto via WhatsApp API para {to_number}...")
        print(f"Mensagem: {message_text}")
        
        # Fazer a requisição
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get("messages", [{}])[0].get("id", "unknown")
            print(f"Mensagem de texto enviada com sucesso via WhatsApp API. ID: {message_id}")
            return True
        else:
            print(f"Erro ao enviar mensagem via WhatsApp API: {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"Erro ao enviar mensagem de texto via WhatsApp API: {e}")
        return False

def send_whatsapp_document_message(to_number: str, document_url: str, filename: str, caption: str = "") -> bool:
    """
    Envia uma mensagem com documento (PDF) via WhatsApp Business API ou wrapper local.
    
    Args:
        to_number: Número de telefone de destino (formato internacional)
        document_url: URL do documento (PDF)
        filename: Nome do arquivo
        caption: Legenda da mensagem
        
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    # Verificar se deve usar wrapper local
    if should_use_local_wrapper():
        print("[WHATSAPP API] Usando wrapper local para envio de documento")
        return send_local_whatsapp_document_message(to_number, document_url, filename, caption)
    
    # Usar API real
    access_token, phone_number_id = get_whatsapp_api_credentials()
    
    if not all([access_token, phone_number_id]):
        print("[Erro] Não foi possível enviar documento: credenciais da WhatsApp API ausentes.")
        return False

    to_number = normalize_whatsapp_to_number(to_number)
    
    try:
        # URL da API do WhatsApp Business
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        
        # Headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Payload da mensagem
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "document",
            "document": {
                "link": document_url,
                "filename": filename,
                "caption": caption
            }
        }
        
        print(f"Enviando documento via WhatsApp API para {to_number}...")
        print(f"URL do documento: {document_url}")
        print(f"Legenda: {caption}")
        
        # Fazer a requisição
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get("messages", [{}])[0].get("id", "unknown")
            print(f"Documento enviado com sucesso via WhatsApp API. ID: {message_id}")
            return True
        else:
            print(f"Erro ao enviar documento via WhatsApp API: {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"Erro ao enviar documento via WhatsApp API: {e}")
        return False

def send_whatsapp_document_by_media_id(
    to_number: str,
    media_id: str,
    filename: str,
    caption: str = "",
) -> bool:
    """Envia documento já hospedado na Meta (media_id)."""
    access_token, phone_number_id = get_whatsapp_api_credentials()
    if not all([access_token, phone_number_id]):
        print("[Erro] Não foi possível enviar documento: credenciais da WhatsApp API ausentes.")
        return False

    to_number = normalize_whatsapp_to_number(to_number)

    try:
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "document",
            "document": {
                "id": media_id,
                "filename": filename,
                "caption": caption,
            },
        }

        print(f"Enviando documento (media_id) via WhatsApp API para {to_number}...")
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get("messages", [{}])[0].get("id", "unknown")
            print(f"Documento enviado com sucesso via WhatsApp API. ID: {message_id}")
            return True

        print(f"Erro ao enviar documento via WhatsApp API: {response.status_code}")
        print(f"Resposta: {response.text}")
        return False
    except Exception as e:
        print(f"Erro ao enviar documento via WhatsApp API: {e}")
        return False


def upload_pdf_to_whatsapp_media(pdf_path: str) -> Optional[str]:
    """
    Faz upload do PDF para a Graph API da Meta e retorna o media_id.
    """
    access_token, phone_number_id = get_whatsapp_api_credentials()
    if not all([access_token, phone_number_id]):
        print("[Erro] Credenciais da WhatsApp API ausentes para upload de mídia.")
        return None

    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/media"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        with open(pdf_path, "rb") as pdf_file:
            files = {
                "file": (os.path.basename(pdf_path), pdf_file, "application/pdf"),
            }
            data = {
                "messaging_product": "whatsapp",
                "type": "application/pdf",
            }
            print(f"Fazendo upload do PDF para a mídia da Meta: {os.path.basename(pdf_path)}")
            response = requests.post(url, headers=headers, files=files, data=data)

        if response.status_code == 200:
            media_id = response.json().get("id")
            print(f"Upload na Meta concluído. media_id={media_id}")
            return media_id

        print(f"Erro no upload de mídia para a Meta: {response.status_code}")
        print(f"Resposta: {response.text}")
        return None
    except Exception as e:
        print(f"Erro ao fazer upload do PDF para a Meta: {e}")
        return None


def send_whatsapp_pdf_message(to_number: str, pdf_path: str, caption: str = "Orçamento de Materiais") -> bool:
    """
    Envia PDF via WhatsApp Business API fazendo upload direto na Meta.
    (Evita depender de URL pública do Supabase, que a Meta rejeita se o bucket não for público.)
    """
    if should_use_local_wrapper():
        print("[WHATSAPP API] Usando wrapper local para envio de PDF")
        return send_local_whatsapp_pdf_message(to_number, pdf_path, caption)

    try:
        media_id = upload_pdf_to_whatsapp_media(pdf_path)
        if not media_id:
            print("[Erro] Falha ao fazer upload do PDF para a Meta")
            return False

        filename = os.path.basename(pdf_path)
        success = send_whatsapp_document_by_media_id(to_number, media_id, filename, caption)
        if success:
            print("PDF enviado com sucesso via WhatsApp API (media_id)")
        return success
    except Exception as e:
        print(f"Erro ao enviar PDF via WhatsApp API: {e}")
        return False


def get_whatsapp_api_status() -> bool:
    """
    Verifica se a WhatsApp Business API ou wrapper local está funcionando.
    """
    # Verificar se deve usar wrapper local
    if should_use_local_wrapper():
        return get_local_whatsapp_status()
    
    # Verificar API real
    access_token, phone_number_id = get_whatsapp_api_credentials()
    
    if not all([access_token, phone_number_id]):
        return False
    
    try:
        # URL para verificar informações da conta
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(url, headers=headers)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Erro ao verificar status da WhatsApp API: {e}")
        return False
