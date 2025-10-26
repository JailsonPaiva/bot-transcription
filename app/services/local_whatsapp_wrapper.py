import os
import json
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

def get_local_whatsapp_config():
    """
    Obtém as configurações do wrapper local do WhatsApp.
    """
    # Configurações padrão para o wrapper local
    config = {
        "enabled": os.getenv("LOCAL_WHATSAPP_ENABLED", "false").lower() == "true",
        "log_file": os.getenv("LOCAL_WHATSAPP_LOG_FILE", "whatsapp_messages.log"),
        "simulate_delay": os.getenv("LOCAL_WHATSAPP_SIMULATE_DELAY", "true").lower() == "true",
        "delay_seconds": float(os.getenv("LOCAL_WHATSAPP_DELAY_SECONDS", "1.0")),
        "success_rate": float(os.getenv("LOCAL_WHATSAPP_SUCCESS_RATE", "0.95"))  # 95% de sucesso
    }
    return config

def log_message_to_file(log_file: str, message_type: str, to_number: str, content: str, success: bool):
    """
    Registra mensagem no arquivo de log local.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_id = str(uuid.uuid4())[:8]
        
        log_entry = {
            "timestamp": timestamp,
            "message_id": message_id,
            "type": message_type,
            "to_number": to_number,
            "content": content,
            "success": success,
            "service": "local_whatsapp_wrapper"
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
        print(f"[LOCAL WHATSAPP] {timestamp} - {message_type.upper()} para {to_number}: {'SUCESSO' if success else 'FALHA'}")
        
    except Exception as e:
        print(f"[LOCAL WHATSAPP] Erro ao registrar log: {e}")

def simulate_api_delay(config: Dict[str, Any]):
    """
    Simula o delay da API real.
    """
    if config["simulate_delay"]:
        delay = config["delay_seconds"]
        print(f"[LOCAL WHATSAPP] Simulando delay da API: {delay}s...")
        time.sleep(delay)

def simulate_api_response(config: Dict[str, Any]) -> bool:
    """
    Simula a resposta da API (sucesso/falha baseado na taxa configurada).
    """
    import random
    success_rate = config["success_rate"]
    return random.random() < success_rate

def send_local_whatsapp_text_message(to_number: str, message_text: str) -> bool:
    """
    Simula envio de mensagem de texto via WhatsApp Business API.
    
    Args:
        to_number: Número de telefone de destino
        message_text: Texto da mensagem
        
    Returns:
        True se simulado com sucesso, False caso contrário
    """
    config = get_local_whatsapp_config()
    
    if not config["enabled"]:
        print("[LOCAL WHATSAPP] Wrapper local desabilitado")
        return False
    
    try:
        print(f"[LOCAL WHATSAPP] Simulando envio de mensagem de texto...")
        print(f"[LOCAL WHATSAPP] Para: {to_number}")
        print(f"[LOCAL WHATSAPP] Mensagem: {message_text}")
        
        # Simular delay da API
        simulate_api_delay(config)
        
        # Simular resposta da API
        success = simulate_api_response(config)
        
        # Registrar no log
        log_message_to_file(
            config["log_file"], 
            "text", 
            to_number, 
            message_text, 
            success
        )
        
        if success:
            message_id = str(uuid.uuid4())[:8]
            print(f"[LOCAL WHATSAPP] SUCESSO: Mensagem simulada enviada! ID: {message_id}")
            return True
        else:
            print(f"[LOCAL WHATSAPP] FALHA: Falha simulada no envio da mensagem")
            return False
            
    except Exception as e:
        print(f"[LOCAL WHATSAPP] Erro na simulação: {e}")
        log_message_to_file(config["log_file"], "text", to_number, message_text, False)
        return False

def send_local_whatsapp_document_message(to_number: str, document_url: str, filename: str, caption: str = "") -> bool:
    """
    Simula envio de documento via WhatsApp Business API.
    
    Args:
        to_number: Número de telefone de destino
        document_url: URL do documento
        filename: Nome do arquivo
        caption: Legenda da mensagem
        
    Returns:
        True se simulado com sucesso, False caso contrário
    """
    config = get_local_whatsapp_config()
    
    if not config["enabled"]:
        print("[LOCAL WHATSAPP] Wrapper local desabilitado")
        return False
    
    try:
        print(f"[LOCAL WHATSAPP] Simulando envio de documento...")
        print(f"[LOCAL WHATSAPP] Para: {to_number}")
        print(f"[LOCAL WHATSAPP] Arquivo: {filename}")
        print(f"[LOCAL WHATSAPP] URL: {document_url}")
        print(f"[LOCAL WHATSAPP] Legenda: {caption}")
        
        # Simular delay da API
        simulate_api_delay(config)
        
        # Simular resposta da API
        success = simulate_api_response(config)
        
        # Criar conteúdo para log
        content = f"Documento: {filename}\nURL: {document_url}\nLegenda: {caption}"
        
        # Registrar no log
        log_message_to_file(
            config["log_file"], 
            "document", 
            to_number, 
            content, 
            success
        )
        
        if success:
            message_id = str(uuid.uuid4())[:8]
            print(f"[LOCAL WHATSAPP] SUCESSO: Documento simulado enviado! ID: {message_id}")
            return True
        else:
            print(f"[LOCAL WHATSAPP] FALHA: Falha simulada no envio do documento")
            return False
            
    except Exception as e:
        print(f"[LOCAL WHATSAPP] Erro na simulação: {e}")
        content = f"Documento: {filename}\nURL: {document_url}\nLegenda: {caption}"
        log_message_to_file(config["log_file"], "document", to_number, content, False)
        return False

def send_local_whatsapp_pdf_message(to_number: str, pdf_path: str, caption: str = "Sua Lista de Compras") -> bool:
    """
    Simula envio de PDF via WhatsApp Business API.
    
    Args:
        to_number: Número de telefone de destino
        pdf_path: Caminho local do arquivo PDF
        caption: Legenda da mensagem
        
    Returns:
        True se simulado com sucesso, False caso contrário
    """
    config = get_local_whatsapp_config()
    
    if not config["enabled"]:
        print("[LOCAL WHATSAPP] Wrapper local desabilitado")
        return False
    
    try:
        # Simular upload para Supabase (criar URL fictícia)
        fake_url = f"https://fake-supabase-url.com/storage/v1/object/public/pdf_orcamento/{os.path.basename(pdf_path)}"
        
        print(f"[LOCAL WHATSAPP] Simulando upload do PDF para Supabase...")
        print(f"[LOCAL WHATSAPP] Arquivo local: {pdf_path}")
        print(f"[LOCAL WHATSAPP] URL simulada: {fake_url}")
        
        # Simular delay do upload
        simulate_api_delay(config)
        
        # Simular envio do documento
        filename = os.path.basename(pdf_path)
        success = send_local_whatsapp_document_message(to_number, fake_url, filename, caption)
        
        if success:
            print(f"[LOCAL WHATSAPP] SUCESSO: PDF simulado enviado!")
            print(f"[LOCAL WHATSAPP] Link simulado: {fake_url}")
        
        return success
        
    except Exception as e:
        print(f"[LOCAL WHATSAPP] Erro na simulação do PDF: {e}")
        return False

def get_local_whatsapp_status() -> bool:
    """
    Verifica se o wrapper local está funcionando.
    """
    config = get_local_whatsapp_config()
    return config["enabled"]

def show_local_whatsapp_logs(log_file: str = None):
    """
    Exibe os logs do wrapper local.
    """
    if not log_file:
        config = get_local_whatsapp_config()
        log_file = config["log_file"]
    
    try:
        if not os.path.exists(log_file):
            print(f"[LOCAL WHATSAPP] Arquivo de log não encontrado: {log_file}")
            return
        
        print(f"\n=== LOGS DO WRAPPER LOCAL WHATSAPP ===")
        print(f"Arquivo: {log_file}")
        print("=" * 50)
        
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        if not lines:
            print("Nenhuma mensagem registrada ainda.")
            return
            
        # Mostrar últimas 10 mensagens
        recent_lines = lines[-10:] if len(lines) > 10 else lines
        
        for line in recent_lines:
            try:
                log_entry = json.loads(line.strip())
                status = "OK" if log_entry["success"] else "ERRO"
                print(f"{status} {log_entry['timestamp']} - {log_entry['type'].upper()} para {log_entry['to_number']}")
                print(f"   Conteudo: {log_entry['content'][:100]}...")
                print()
            except:
                print(f"Linha invalida: {line.strip()}")
                
    except Exception as e:
        print(f"[LOCAL WHATSAPP] Erro ao ler logs: {e}")

def clear_local_whatsapp_logs(log_file: str = None):
    """
    Limpa os logs do wrapper local.
    """
    if not log_file:
        config = get_local_whatsapp_config()
        log_file = config["log_file"]
    
    try:
        if os.path.exists(log_file):
            os.remove(log_file)
            print(f"[LOCAL WHATSAPP] Logs limpos: {log_file}")
        else:
            print(f"[LOCAL WHATSAPP] Arquivo de log não encontrado: {log_file}")
    except Exception as e:
        print(f"[LOCAL WHATSAPP] Erro ao limpar logs: {e}")

# Função para testar o wrapper
def test_local_whatsapp_wrapper():
    """
    Testa o wrapper local do WhatsApp.
    """
    print("=== TESTE DO WRAPPER LOCAL WHATSAPP ===\n")
    
    # Verificar configuração
    config = get_local_whatsapp_config()
    print(f"Wrapper habilitado: {config['enabled']}")
    print(f"Arquivo de log: {config['log_file']}")
    print(f"Simular delay: {config['simulate_delay']}")
    print(f"Delay: {config['delay_seconds']}s")
    print(f"Taxa de sucesso: {config['success_rate']*100}%")
    
    if not config['enabled']:
        print("\nERRO: Wrapper desabilitado. Configure LOCAL_WHATSAPP_ENABLED=true")
        return False
    
    print("\nTestando envio de mensagem de texto...")
    success1 = send_local_whatsapp_text_message("556596047289", "Teste do wrapper local - Mensagem de texto")
    
    print("\nTestando envio de documento...")
    success2 = send_local_whatsapp_document_message(
        "556596047289", 
        "https://fake-url.com/test.pdf", 
        "teste.pdf", 
        "Documento de teste"
    )
    
    print("\nTestando envio de PDF...")
    success3 = send_local_whatsapp_pdf_message("556596047289", "teste.pdf", "PDF de teste")
    
    print(f"\nResultados:")
    print(f"Texto: {'OK' if success1 else 'ERRO'}")
    print(f"Documento: {'OK' if success2 else 'ERRO'}")
    print(f"PDF: {'OK' if success3 else 'ERRO'}")
    
    print(f"\nLogs gerados:")
    show_local_whatsapp_logs()
    
    return success1 and success2 and success3
