import os
import uuid
from datetime import datetime
from supabase import create_client, Client
from typing import Optional

def get_supabase_credentials():
    """
    Obtém as credenciais do Supabase das variáveis de ambiente.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "pdf-files")
    
    if not all([url, key]):
        print("[Erro] Credenciais do Supabase não encontradas nas variáveis de ambiente.")
        print("Necessário: SUPABASE_URL, SUPABASE_KEY")
        return None, None, None
    
    return url, key, bucket_name

def get_supabase_client() -> Optional[Client]:
    """
    Cria e retorna um cliente do Supabase.
    """
    url, key, _ = get_supabase_credentials()
    
    if not all([url, key]):
        return None
    
    try:
        supabase: Client = create_client(url, key)
        return supabase
    except Exception as e:
        print(f"Erro ao criar cliente Supabase: {e}")
        return None

def upload_pdf_to_supabase(pdf_path: str, original_filename: str = None) -> Optional[str]:
    """
    Faz upload de um arquivo PDF para o bucket do Supabase.
    
    Args:
        pdf_path: Caminho local do arquivo PDF
        original_filename: Nome original do arquivo (opcional)
    
    Returns:
        URL pública do arquivo ou None em caso de erro
    """
    supabase = get_supabase_client()
    if not supabase:
        return None
    
    _, _, bucket_name = get_supabase_credentials()
    
    try:
        # Gera um nome único para o arquivo
        if not original_filename:
            original_filename = f"lista_compras_{uuid.uuid4()}.pdf"
        
        # Adiciona timestamp para evitar conflitos
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{original_filename}"
        
        # Lê o arquivo
        with open(pdf_path, 'rb') as file:
            file_data = file.read()
        
        # Faz upload para o bucket
        result = supabase.storage.from_(bucket_name).upload(
            path=unique_filename,
            file=file_data,
            file_options={"content-type": "application/pdf"}
        )
        
        if result:
            # Obtém a URL pública do arquivo
            public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
            print(f"PDF enviado com sucesso para o Supabase: {public_url}")
            return public_url
        else:
            print("Erro ao fazer upload do PDF para o Supabase")
            return None
            
    except Exception as e:
        print(f"Erro ao fazer upload do PDF para o Supabase: {e}")
        return None

def delete_pdf_from_supabase(file_path: str) -> bool:
    """
    Remove um arquivo PDF do bucket do Supabase.
    
    Args:
        file_path: Caminho do arquivo no bucket
    
    Returns:
        True se removido com sucesso, False caso contrário
    """
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    _, _, bucket_name = get_supabase_credentials()
    
    try:
        result = supabase.storage.from_(bucket_name).remove([file_path])
        if result:
            print(f"Arquivo removido com sucesso do Supabase: {file_path}")
            return True
        else:
            print(f"Erro ao remover arquivo do Supabase: {file_path}")
            return False
    except Exception as e:
        print(f"Erro ao remover arquivo do Supabase: {e}")
        return False

def test_supabase_connection() -> bool:
    """
    Testa a conexão com o Supabase.
    
    Returns:
        True se a conexão for bem-sucedida, False caso contrário
    """
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        # Tenta listar os buckets para testar a conexão
        buckets = supabase.storage.list_buckets()
        print("Conexão com Supabase estabelecida com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao testar conexão com Supabase: {e}")
        return False

