import os
from elevenlabs.client import ElevenLabs
import mimetypes

# O SDK da ElevenLabs é inteligente e busca a chave da variável de ambiente
# "ELEVENLABS_API_KEY" automaticamente.
# Mas podemos instanciar explicitamente para garantir.
api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    print("Erro: ELEVENLABS_API_KEY não encontrada no .env")
    # Em um app real, lançaríamos uma exceção aqui
    
client = ElevenLabs(api_key=api_key)

# ... (início do arquivo igual) ...

def transcribe_audio(audio_path: str) -> str:
    """
    Transcreve um arquivo de áudio usando a API de Speech-to-Text da ElevenLabs.
    """
    try:
        with open(audio_path, 'rb') as audio_file:
            
            response = client.speech_to_text.convert(
                file=audio_file,
                # CORREÇÃO AQUI:
                # O modelo de Speech-to-Text chama-se 'scribe_v1'
                model_id="scribe_v1"
            )
            
            print(f"Texto Transcrito (ElevenLabs): {response.text}")
            return response.text

    except Exception as e:
        print(f"Erro durante a transcrição com ElevenLabs: {e}")
        return ""