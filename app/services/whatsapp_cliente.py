import os
import requests

API_VERSION = "v18.0"

def get_meta_tokens():
    meta_token = os.getenv("META_WA_TOKEN")
    phone_id = os.getenv("WA_PHONE_NUMBER_ID")
    if not meta_token or not phone_id:
        print("[Config] META_WA_TOKEN ou WA_PHONE_NUMBER_ID não definidos nas variáveis de ambiente.")
    return meta_token, phone_id

def download_media(media_id: str, local_path: str) -> bool:
    meta_token, _ = get_meta_tokens()
    if not meta_token:
        print("[Erro] META_WA_TOKEN ausente. Não é possível baixar mídia.")
        return False

    headers = {"Authorization": f"Bearer {meta_token}"}
    
    # 1. Obter a URL da mídia
    url_info = f"https://graph.facebook.com/{API_VERSION}/{media_id}"
    response_info = requests.get(url_info, headers=headers)
    if response_info.status_code != 200:
        try:
            print(f"Error getting media URL: {response_info.json()}")
        except Exception:
            print(f"Error getting media URL: status={response_info.status_code} body={response_info.text}")
        return False
    
    media_url = response_info.json()["url"]
    
    # 2. Baixar o arquivo de mídia
    response_media = requests.get(media_url, headers=headers)
    if response_media.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(response_media.content)
        print(f"Media downloaded to {local_path}")
        return True
    else:
        try:
            print(f"Error downloading media: {response_media.json()}")
        except Exception:
            print(f"Error downloading media: status={response_media.status_code} body={response_media.text}")
        return False

def send_pdf_message(to_number: str, pdf_path: str, caption: str):
    # 1. Upload do PDF para a API da Meta
    meta_token, phone_id = get_meta_tokens()
    if not meta_token or not phone_id:
        print("[Erro] Tokens ausentes. Não é possível enviar PDF.")
        return

    url_upload = f"https://graph.facebook.com/{API_VERSION}/{phone_id}/media"
    headers = {"Authorization": f"Bearer {meta_token}"}
    files = {
        'file': (os.path.basename(pdf_path), open(pdf_path, 'rb'), 'application/pdf'),
    }
    data = {
        'messaging_product': 'WHATSAPP',
        'type': 'application/pdf'
    }
    response_upload = requests.post(url_upload, headers=headers, files=files, data=data)
    if response_upload.status_code != 200:
        try:
            print(f"Error uploading PDF: {response_upload.json()}")
        except Exception:
            print(f"Error uploading PDF: status={response_upload.status_code} body={response_upload.text}")
        return
    
    media_id = response_upload.json()["id"]

    # 2. Enviar a mensagem com o ID do PDF
    url_send = f"https://graph.facebook.com/{API_VERSION}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "document",
        "document": {
            "id": media_id,
            "caption": caption,
            "filename": os.path.basename(pdf_path)
        }
    }
    response_send = requests.post(url_send, headers=headers, json=payload)
    try:
        print(f"Send message response: {response_send.json()}")
    except Exception:
        print(f"Send message response: status={response_send.status_code} body={response_send.text}")