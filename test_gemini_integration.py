#!/usr/bin/env python3
"""
Script de teste para verificar a integração com Gemini.
Este script testa as funções de correção de transcrição sem precisar do webhook completo.
"""

import os
import sys
from dotenv import load_dotenv

# Adicionar o diretório app ao path para importar os módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Carregar variáveis de ambiente
load_dotenv()

def test_gemini_integration():
    """
    Testa a integração com Gemini usando textos de exemplo.
    """
    try:
        from services.gemini_correction import (
            correct_transcription_with_gemini, 
            analyze_transcription_context,
            get_gemini_status
        )
        
        print("=== TESTE DE INTEGRAÇÃO COM GEMINI ===\n")
        
        # Verificar se a API key está configurada
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("ERRO: GEMINI_API_KEY nao encontrada nas variaveis de ambiente")
            print("   Configure a chave no arquivo .env antes de testar")
            return False
        
        print(f"OK: API Key encontrada: {api_key[:10]}...")
        
        # Teste 1: Verificar status da API
        print("\n1. Testando conectividade com Gemini...")
        status = get_gemini_status()
        if status:
            print("OK: Conectividade com Gemini OK")
        else:
            print("ERRO: Falha na conectividade com Gemini")
            return False
        
        # Teste 2: Análise de contexto
        print("\n2. Testando análise de contexto...")
        test_text_obras = "preciso de cimento tijolos telhas e ferramentas para construir uma casa"
        context_result = analyze_transcription_context(test_text_obras)
        print(f"   Texto: '{test_text_obras}'")
        print(f"   Contexto detectado: {context_result}")
        
        # Teste 3: Correção de transcrição para obras
        print("\n3. Testando correção de transcrição (contexto: obras)...")
        test_text_mal_transcrito = "preciso de simento tijolos telhas e ferramentas para construir uma casa"
        corrected_text = correct_transcription_with_gemini(test_text_mal_transcrito, "obras")
        print(f"   Texto original: '{test_text_mal_transcrito}'")
        print(f"   Texto corrigido: '{corrected_text}'")
        
        # Teste 4: Correção de transcrição para compras
        print("\n4. Testando correção de transcrição (contexto: compras)...")
        test_text_compras = "preciso comprar arroz feijão carne e verduras para o almoço"
        corrected_text_compras = correct_transcription_with_gemini(test_text_compras, "compras")
        print(f"   Texto original: '{test_text_compras}'")
        print(f"   Texto corrigido: '{corrected_text_compras}'")
        
        print("\nOK: Todos os testes passaram com sucesso!")
        return True
        
    except ImportError as e:
        print(f"ERRO DE IMPORTACAO: {e}")
        print("   Execute: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"ERRO GERAL: {e}")
        return False

def test_nlp_integration():
    """
    Testa a integração com os módulos NLP existentes.
    """
    try:
        from services.nlp_obras import extract_construction_context
        from services.nlp import extract_products_from_text
        
        print("\n=== TESTE DE INTEGRAÇÃO COM NLP ===\n")
        
        # Teste com texto de obras
        print("1. Testando extração de materiais de construção...")
        test_text_obras = "preciso de 10 sacos de cimento, 500 tijolos, 100 telhas cerâmicas e ferramentas básicas"
        construction_context = extract_construction_context(test_text_obras)
        print(f"   Texto: '{test_text_obras}'")
        print(f"   Materiais encontrados: {construction_context['materiais']}")
        print(f"   Tipo de obra: {construction_context['tipo_obra']}")
        
        # Teste com texto de compras
        print("\n2. Testando extração de produtos...")
        test_text_compras = "preciso comprar arroz, feijão, carne e verduras"
        products = extract_products_from_text(test_text_compras)
        print(f"   Texto: '{test_text_compras}'")
        print(f"   Produtos encontrados: {products}")
        
        print("\nOK: Testes NLP passaram com sucesso!")
        return True
        
    except Exception as e:
        print(f"ERRO NO TESTE NLP: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando testes de integração...\n")
    
    # Testar integração com Gemini
    gemini_ok = test_gemini_integration()
    
    # Testar integração com NLP
    nlp_ok = test_nlp_integration()
    
    print("\n" + "="*50)
    if gemini_ok and nlp_ok:
        print("SUCESSO: TODOS OS TESTES PASSARAM!")
        print("   A integracao esta pronta para uso.")
    else:
        print("ATENCAO: ALGUNS TESTES FALHARAM")
        print("   Verifique as configuracoes e dependencias.")
    
    print("="*50)
