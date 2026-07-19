"""Extração de materiais (Gemini JSON + fallback NLP)."""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from app.core.config import Settings
from app.services.gemini_correction import (
    correct_transcription_with_gemini,
    extract_materials_json_with_gemini,
)
from app.services.nlp_obras import extract_construction_context

logger = logging.getLogger(__name__)


def resolve_materials_from_text(
    transcribed_text: str,
    settings: Settings,
) -> Tuple[str, List[Dict[str, str]], str]:
    final_text = transcribed_text
    materials: List[Dict[str, str]] = []
    obra_type = "obra"

    if settings.enable_gemini_correction:
        logger.info("Extraindo materiais com Gemini JSON...")
        gemini_result = extract_materials_json_with_gemini(transcribed_text)
        if gemini_result and gemini_result.get("materiais"):
            materials = gemini_result["materiais"]
            obra_type = gemini_result.get("tipo_obra") or "obra"
            if gemini_result.get("texto_corrigido"):
                final_text = gemini_result["texto_corrigido"]
            logger.info("Materiais via Gemini JSON: %s", materials)
            return final_text, materials, obra_type

        logger.info("Gemini JSON sem materiais válidos; tentando correção + NLP...")
        corrected = correct_transcription_with_gemini(transcribed_text, "obras")
        if corrected:
            final_text = corrected

    construction_context = extract_construction_context(final_text)
    materials = construction_context["materiais"]
    obra_type = construction_context["tipo_obra"]
    logger.info("Materiais via NLP: %s", materials)
    return final_text, materials, obra_type
