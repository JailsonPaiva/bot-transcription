import os
from twilio.rest import Client
from app.services.supabase_client import upload_pdf_to_supabase

def get_twilio_credentials():
    """
    Obtém as credenciais do Twilio das variáveis de ambiente.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    
    if not all([account_sid, auth_token, from_number]):
        print("[Erro] Credenciais do Twilio não encontradas nas variáveis de ambiente.")
        print("Necessário: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER")
        return None, None, None
    
    return account_sid, auth_token, from_number

def send_pdf_message(to_number: str, pdf_path: str, caption: str = "Sua Lista de Compras"):
    """
    Envia uma mensagem com PDF via Twilio usando Supabase para hospedar o arquivo.
    
    Args:
        to_number: Número de telefone de destino (formato internacional)
        pdf_path: Caminho local do arquivo PDF
        caption: Legenda da mensagem
    """
    account_sid, auth_token, from_number = get_twilio_credentials()
    
    if not all([account_sid, auth_token, from_number]):
        print("[Erro] Não foi possível enviar mensagem: credenciais do Twilio ausentes.")
        return False
    
    try:
        # Primeiro, faz upload do PDF para o Supabase
        print("Fazendo upload do PDF para o Supabase...")
        pdf_url = upload_pdf_to_supabase(pdf_path)
        
        if not pdf_url:
            print("[Erro] Falha ao fazer upload do PDF para o Supabase")
            return False
        
        client = Client(account_sid, auth_token)
        
        # Envia mensagem com o link do PDF
        message_body = f"{caption}\n\n📄 Seu PDF está pronto para download:\n{pdf_url}"
        
        message = client.messages.create(
            from_=from_number,
            body=message_body,
            to=to_number
        )
        
        print(f"Mensagem com link do PDF enviada com sucesso. SID: {message.sid}")
        print(f"Link do PDF: {pdf_url}")
        return True
        
    except Exception as e:
        print(f"Erro ao enviar mensagem via Twilio: {e}")
        return False

def send_pdf_link_message(to_number: str, pdf_url: str, caption: str = "Sua Lista de Compras"):
    """
    Envia uma mensagem com link do PDF via Twilio.
    
    Args:
        to_number: Número de telefone de destino (formato internacional)
        pdf_url: URL do PDF no Supabase
        caption: Legenda da mensagem
    """
    account_sid, auth_token, from_number = get_twilio_credentials()
    
    if not all([account_sid, auth_token, from_number]):
        print("[Erro] Não foi possível enviar mensagem: credenciais do Twilio ausentes.")
        return False
    
    try:
        client = Client(account_sid, auth_token)
        
        # Envia mensagem com o link do PDF
        message_body = f"{caption}\n\n📄 Seu PDF está pronto para download:\n{pdf_url}"
        
        message = client.messages.create(
            from_=from_number,
            body=message_body,
            to=to_number
        )
        
        print(f"Mensagem com link do PDF enviada com sucesso. SID: {message.sid}")
        print(f"Link do PDF: {pdf_url}")
        return True
        
    except Exception as e:
        print(f"Erro ao enviar mensagem via Twilio: {e}")
        return False

def send_text_message(to_number: str, messageText: str):
    """
    Envia uma mensagem de texto via Twilio.
    
    Args:
        to_number: Número de telefone de destino (formato internacional)
        message: Texto da mensagem
    """
    account_sid, auth_token, from_number = get_twilio_credentials()
    
    if not all([account_sid, auth_token, from_number]):
        print("[Erro] Não foi possível enviar mensagem: credenciais do Twilio ausentes.")
        return False
    
    try:
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            from_=from_number,
            body=messageText,
            to=to_number
        )
        
        print(f"Mensagem de texto enviada com sucesso. SID: {message.sid}")
        return True
        
    except Exception as e:
        print(f"Erro ao enviar mensagem de texto via Twilio: {e}")
        return False
