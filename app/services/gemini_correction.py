import json
import os
import re
from typing import Dict, List, Optional

import google.generativeai as genai

from app.domain.catalog_service import get_canonical_names
from app.services.nlp_obras import validate_materials_against_catalog

# Modelo padrão atual (gemini-2.5-flash não está disponível para novas contas)
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


def get_gemini_credentials():
    """
    Obtém as credenciais do Gemini das variáveis de ambiente.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[Erro] GEMINI_API_KEY não encontrada nas variáveis de ambiente.")
        return None

    return api_key


def get_gemini_model_name() -> str:
    """Nome do modelo Gemini (sobrescrevível via GEMINI_MODEL)."""
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL


def get_gemini_model():
    """Instancia o modelo GenerativeModel configurado."""
    model_name = get_gemini_model_name()
    print(f"Usando modelo Gemini: {model_name}")
    return genai.GenerativeModel(model_name)


def _extract_json_object(text: str) -> Optional[dict]:
    """Extrai o primeiro objeto JSON da resposta do modelo."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def correct_transcription_with_gemini(transcribed_text: str, context: str = "obras") -> Optional[str]:
    """
    Corrige e melhora o texto transcrito usando o Gemini.
    Mantido como fallback/legibilidade; a extração principal usa JSON.
    """
    api_key = get_gemini_credentials()
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        model = get_gemini_model()

        prompt = f"""
Você é um especialista em construção civil e análise de transcrições de áudio.
Corrija o texto abaixo preservando materiais e quantidades.

TEXTO ORIGINAL: "{transcribed_text}"

INSTRUÇÕES:
1. Corrija erros óbvios de transcrição
2. Padronize termos técnicos de construção
3. Preserve números e quantidades
4. Retorne APENAS o texto corrigido
"""

        print("Enviando texto para correção com Gemini...")
        print(f"Texto original: {transcribed_text}")
        response = model.generate_content(prompt)

        if response and response.text:
            corrected_text = response.text.strip()
            print(f"Texto corrigido pelo Gemini: {corrected_text}")
            return corrected_text

        print("Erro: Gemini não retornou texto corrigido")
        return None
    except Exception as e:
        print(f"Erro durante correção com Gemini: {e}")
        return None


def extract_materials_json_with_gemini(transcribed_text: str) -> Optional[Dict]:
    """
    Extrai materiais em JSON estruturado e valida contra o catálogo oficial.

    Retorna:
      {
        "tipo_obra": str,
        "materiais": [{"material", "quantidade", "unidade"}, ...],
        "texto_corrigido": str | None,
        "raw": dict | None
      }
    """
    api_key = get_gemini_credentials()
    if not api_key:
        return None

    catalog = get_canonical_names()
    catalog_str = ", ".join(catalog)

    try:
        genai.configure(api_key=api_key)
        model = get_gemini_model()

        prompt = f"""
Você extrai materiais de construção de transcrições de áudio de pedreiros.

TEXTO: "{transcribed_text}"

CATÁLOGO OFICIAL (use estes nomes canônicos sempre que possível):
{catalog_str}

Regras:
1. Retorne APENAS JSON válido, sem markdown e sem comentários
2. quantidade deve ser número (ex.: 3, não "três")
3. unidade em minúsculas (saco, sacos, m, m2, unidade, etc.)
4. Se o material não estiver no catálogo, omita-o
5. Não invente materiais que não estejam no texto

Formato:
{{
  "tipo_obra": "obra|casa|reforma|apartamento|comercial|construção",
  "texto_corrigido": "versão limpa do texto",
  "materiais": [
    {{"material": "cimento", "quantidade": 3, "unidade": "sacos"}}
  ]
}}
"""

        print("Extraindo materiais em JSON com Gemini...")
        response = model.generate_content(prompt)
        if not response or not response.text:
            print("Erro: Gemini não retornou JSON de materiais")
            return None

        raw_text = response.text.strip()
        print(f"Resposta JSON Gemini: {raw_text}")
        data = _extract_json_object(raw_text)
        if not data:
            print("Erro: não foi possível parsear JSON do Gemini")
            return None

        validated = validate_materials_against_catalog(data.get("materiais") or [])
        tipo_obra = str(data.get("tipo_obra") or "obra").strip().lower() or "obra"

        return {
            "tipo_obra": tipo_obra,
            "materiais": validated,
            "texto_corrigido": data.get("texto_corrigido"),
            "raw": data,
        }
    except Exception as e:
        print(f"Erro durante extração JSON com Gemini: {e}")
        return None


def analyze_transcription_context(transcribed_text: str) -> Dict[str, any]:
    """Compatibilidade legada — o fluxo atual é apenas obras."""
    return {"context": "obras", "confidence": 1.0, "reasoning": "Fluxo exclusivo de obras"}


def get_gemini_status():
    """
    Verifica se a API do Gemini está funcionando.
    """
    api_key = get_gemini_credentials()
    if not api_key:
        return False

    try:
        genai.configure(api_key=api_key)
        model = get_gemini_model()
        response = model.generate_content("Teste de conectividade")
        return response is not None and response.text is not None
    except Exception as e:
        print(f"Erro ao verificar status do Gemini: {e}")
        return False
