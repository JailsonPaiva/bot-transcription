import os
import requests
import time
import uuid

def get_gladia_credentials():
    """
    Obtém as credenciais da Gladia das variáveis de ambiente.
    """
    api_key = os.getenv("GLADIA_API_KEY")
    if not api_key:
        print("[Erro] GLADIA_API_KEY não encontrada nas variáveis de ambiente.")
        return None
    
    return api_key

def transcribe_audio_gladia(audio_path: str) -> str:
    """
    Transcreve um arquivo de áudio usando a API da Gladia.
    
    Args:
        audio_path: Caminho local do arquivo de áudio
        
    Returns:
        Texto transcrito ou string vazia se falhar
    """
    api_key = get_gladia_credentials()
    if not api_key:
        return ""
    
    try:
        # 1. Upload do arquivo de áudio
        upload_url = "https://api.gladia.io/v2/upload"
        headers = {
            "x-gladia-key": api_key
        }
        
        with open(audio_path, 'rb') as audio_file:
            files = {
                'audio': (os.path.basename(audio_path), audio_file, 'audio/ogg')
            }
            
            print("Fazendo upload do áudio para Gladia...")
            upload_response = requests.post(upload_url, headers=headers, files=files)
            
            if upload_response.status_code != 200:
                print(f"Erro no upload: {upload_response.status_code} - {upload_response.text}")
                return ""
            
            upload_data = upload_response.json()
            audio_url = upload_data.get('audio_url')
            
            if not audio_url:
                print("Erro: URL do áudio não retornada")
                return ""
            
            print(f"Áudio enviado com sucesso. URL: {audio_url}")
        
        # 2. Iniciar transcrição
        transcription_url = "https://api.gladia.io/v2/pre-recorded"
        transcription_payload = {
            "audio_url": audio_url,
            "language": "pt",
            "detect_language": True
        }
        
        print("Iniciando transcrição...")
        print(f"Payload: {transcription_payload}")
        transcription_response = requests.post(
            transcription_url, 
            headers=headers, 
            json=transcription_payload
        )
        
        if transcription_response.status_code not in [200, 201]:
            print(f"Erro na transcrição: {transcription_response.status_code} - {transcription_response.text}")
            return ""
        
        transcription_data = transcription_response.json()
        transcription_id = transcription_data.get('id')
        
        if not transcription_id:
            print("Erro: ID da transcrição não retornado")
            return ""
        
        print(f"Transcrição iniciada. ID: {transcription_id}")
        
        # 3. Aguardar conclusão da transcrição
        result_url = f"https://api.gladia.io/v2/pre-recorded/{transcription_id}"
        
        max_attempts = 30  # Máximo 30 tentativas (5 minutos)
        attempt = 0
        
        while attempt < max_attempts:
            print(f"Verificando status da transcrição... (tentativa {attempt + 1}/{max_attempts})")
            
            status_response = requests.get(result_url, headers=headers)
            
            if status_response.status_code != 200:
                print(f"Erro ao verificar status: {status_response.status_code}")
                time.sleep(10)
                attempt += 1
                continue
            
            status_data = status_response.json()
            status = status_data.get('status')
            
            if status == 'done':
                # Transcrição concluída
                result = status_data.get('result')
                if result:
                    # Extrair o texto da estrutura da Gladia
                    if isinstance(result, dict) and 'transcription' in result:
                        transcription_data = result['transcription']
                        if 'full_transcript' in transcription_data:
                            transcribed_text = transcription_data['full_transcript']
                        else:
                            # Se não houver full_transcript, tentar extrair dos utterances
                            utterances = transcription_data.get('utterances', [])
                            if utterances:
                                transcribed_text = ' '.join([utterance.get('text', '') for utterance in utterances])
                            else:
                                transcribed_text = str(result)
                    else:
                        transcribed_text = str(result)
                    
                    print(f"Transcrição concluída com Gladia: {transcribed_text}")
                    return transcribed_text
                else:
                    print("Erro: Resultado da transcrição não encontrado")
                    return ""
            
            elif status == 'error':
                print(f"Erro na transcrição: {status_data.get('error', 'Erro desconhecido')}")
                return ""
            
            # Aguardar antes da próxima verificação
            time.sleep(10)
            attempt += 1
        
        print("Timeout: Transcrição não concluída no tempo esperado")
        return ""
        
    except Exception as e:
        print(f"Erro durante transcrição com Gladia: {e}")
        return ""

def transcribe_audio_gladia_simple(audio_path: str) -> str:
    """
    Versão simplificada da transcrição usando Gladia (para casos onde não há upload de arquivo).
    Esta função assume que o arquivo já está acessível via URL.
    
    Args:
        audio_path: Caminho local do arquivo de áudio
        
    Returns:
        Texto transcrito ou string vazia se falhar
    """
    api_key = get_gladia_credentials()
    if not api_key:
        return ""
    
    try:
        # Para esta versão simplificada, vamos usar o endpoint direto
        # Nota: Esta é uma implementação básica - em produção, você deve fazer upload do arquivo
        transcription_url = "https://api.gladia.io/v2/transcription"
        headers = {
            "x-gladia-key": api_key,
            "Content-Type": "application/json"
        }
        
        # Esta é uma implementação simplificada
        # Em produção, você deve fazer upload do arquivo primeiro
        print("Usando transcrição simplificada da Gladia...")
        print("Nota: Para produção, implemente o upload de arquivo primeiro")
        
        return ""
        
    except Exception as e:
        print(f"Erro na transcrição simplificada com Gladia: {e}")
        return ""

def get_supported_languages():
    """
    Retorna as linguagens suportadas pela Gladia.
    """
    return [
        "portuguese",  # Português
        "english",     # Inglês
        "spanish",     # Espanhol
        "french",      # Francês
        "german",      # Alemão
        "italian",     # Italiano
        "auto"         # Detecção automática
    ]

def get_gladia_status():
    """
    Verifica o status da API da Gladia.
    """
    api_key = get_gladia_credentials()
    if not api_key:
        return False
    
    try:
        # Endpoint para verificar status (se disponível)
        headers = {"x-gladia-key": api_key}
        response = requests.get("https://api.gladia.io/v2/", headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao verificar status da Gladia: {e}")
        return False
