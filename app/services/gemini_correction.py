import os
import google.generativeai as genai
from typing import Dict, Optional

def get_gemini_credentials():
    """
    Obtém as credenciais do Gemini das variáveis de ambiente.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[Erro] GEMINI_API_KEY não encontrada nas variáveis de ambiente.")
        return None
    
    return api_key

def correct_transcription_with_gemini(transcribed_text: str, context: str = "obras") -> Optional[str]:
    """
    Corrige e melhora o texto transcrito usando o Gemini, fornecendo contexto específico.
    
    Args:
        transcribed_text: Texto transcrito original
        context: Contexto da análise ("obras" ou "compras")
        
    Returns:
        Texto corrigido ou None se falhar
    """
    api_key = get_gemini_credentials()
    if not api_key:
        return None
    
    try:
        # Configurar o Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Definir prompt baseado no contexto
        if context.lower() == "obras":
            prompt = f"""
Você é um especialista em construção civil e análise de transcrições de áudio. 
Sua tarefa é corrigir e melhorar o seguinte texto transcrito de um áudio sobre materiais de construção:

TEXTO ORIGINAL: "{transcribed_text}"

INSTRUÇÕES:
1. Corrija erros de transcrição óbvios (palavras mal interpretadas)
2. Padronize termos técnicos de construção
3. Melhore a clareza e legibilidade
4. Mantenha todas as informações sobre materiais e quantidades
5. Use terminologia técnica correta para materiais de construção
6. Preserve números e quantidades exatas
7. Se houver ambiguidade, mantenha o texto original

IMPORTANTE: Retorne APENAS o texto corrigido, sem explicações ou comentários adicionais.
"""
        else:  # contexto de compras
            prompt = f"""
Você é um especialista em análise de transcrições de áudio para listas de compras.
Sua tarefa é corrigir e melhorar o seguinte texto transcrito de um áudio sobre produtos para compra:

TEXTO ORIGINAL: "{transcribed_text}"

INSTRUÇÕES:
1. Corrija erros de transcrição óbvios (palavras mal interpretadas)
2. Padronize nomes de produtos
3. Melhore a clareza e legibilidade
4. Mantenha todas as informações sobre produtos e quantidades
5. Use nomes de produtos corretos e padronizados
6. Preserve números e quantidades exatas
7. Se houver ambiguidade, mantenha o texto original

IMPORTANTE: Retorne APENAS o texto corrigido, sem explicações ou comentários adicionais.
"""
        
        print("Enviando texto para correção com Gemini...")
        print(f"Texto original: {transcribed_text}")
        
        # Fazer a requisição para o Gemini
        response = model.generate_content(prompt)
        
        if response and response.text:
            corrected_text = response.text.strip()
            print(f"Texto corrigido pelo Gemini: {corrected_text}")
            return corrected_text
        else:
            print("Erro: Gemini não retornou texto corrigido")
            return None
            
    except Exception as e:
        print(f"Erro durante correção com Gemini: {e}")
        return None

def analyze_transcription_context(transcribed_text: str) -> Dict[str, any]:
    """
    Analisa o contexto da transcrição usando Gemini para determinar se é sobre obras ou compras.
    
    Args:
        transcribed_text: Texto transcrito
        
    Returns:
        Dicionário com análise do contexto
    """
    api_key = get_gemini_credentials()
    if not api_key:
        return {"context": "obras", "confidence": 0.0, "reasoning": "Erro na configuração"}
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
Analise o seguinte texto transcrito e determine se ele se refere a:
1. MATERIAIS DE CONSTRUÇÃO/OBRAS (cimento, tijolos, telhas, ferramentas, etc.)
2. PRODUTOS DE COMPRAS GERAIS (alimentos, produtos de limpeza, eletrônicos, etc.)

TEXTO: "{transcribed_text}"

Responda APENAS no formato JSON:
{{
    "context": "obras" ou "compras",
    "confidence": número entre 0.0 e 1.0,
    "reasoning": "explicação breve da decisão"
}}
"""
        
        print("Analisando contexto da transcrição com Gemini...")
        response = model.generate_content(prompt)
        
        if response and response.text:
            # Tentar extrair JSON da resposta
            response_text = response.text.strip()
            print(f"Resposta do Gemini: {response_text}")
            
            # Parse simples do JSON (em produção, usar json.loads)
            if '"context": "obras"' in response_text:
                return {"context": "obras", "confidence": 0.8, "reasoning": "Detectado contexto de obras"}
            elif '"context": "compras"' in response_text:
                return {"context": "compras", "confidence": 0.8, "reasoning": "Detectado contexto de compras"}
            else:
                return {"context": "obras", "confidence": 0.5, "reasoning": "Contexto não determinado claramente"}
        else:
            return {"context": "obras", "confidence": 0.0, "reasoning": "Erro na resposta do Gemini"}
            
    except Exception as e:
        print(f"Erro durante análise de contexto com Gemini: {e}")
        return {"context": "obras", "confidence": 0.0, "reasoning": f"Erro: {str(e)}"}

def get_gemini_status():
    """
    Verifica se a API do Gemini está funcionando.
    """
    api_key = get_gemini_credentials()
    if not api_key:
        return False
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Teste simples
        response = model.generate_content("Teste de conectividade")
        return response is not None and response.text is not None
        
    except Exception as e:
        print(f"Erro ao verificar status do Gemini: {e}")
        return False
