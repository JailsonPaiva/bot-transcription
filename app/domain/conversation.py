"""Domínio de conversa / máquina de estados (Sprint 1 base)."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConversationState(str, Enum):
    AWAITING_AUDIO = "awaiting_audio"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    PDF_SENT = "pdf_sent"


@dataclass
class ConversationSession:
    state: ConversationState = ConversationState.AWAITING_AUDIO
    materials: List[Dict[str, str]] = field(default_factory=list)
    obra_type: str = "obra"
    texto: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ConversationSession":
        if not data:
            return cls()
        state_raw = data.get("state", ConversationState.AWAITING_AUDIO.value)
        try:
            state = ConversationState(state_raw)
        except ValueError:
            state = ConversationState.AWAITING_AUDIO
        return cls(
            state=state,
            materials=list(data.get("materials") or []),
            obra_type=str(data.get("obra_type") or "obra"),
            texto=str(data.get("texto") or ""),
        )


def digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def format_destination_number(from_number: str, message_service: str) -> str:
    digits = digits_only(from_number.replace("whatsapp:", ""))
    if message_service.lower() == "whatsapp":
        return digits
    return f"whatsapp:+{digits}"


def is_confirmation_message(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    normalized = re.sub(r"[!?.]", "", normalized)
    return normalized in {
        "sim",
        "s",
        "ok",
        "okay",
        "confirmo",
        "confirma",
        "confirmar",
        "pode",
        "pode gerar",
        "gerar",
        "gerar pdf",
        "isso",
        "correto",
        "certo",
        "yes",
        "y",
    }


def is_cancel_message(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    normalized = re.sub(r"[!?.]", "", normalized)
    return normalized in {
        "nao",
        "não",
        "n",
        "cancelar",
        "cancela",
        "corrigir",
        "errado",
        "refazer",
    }


def build_confirmation_message(materials: List[Dict[str, str]], obra_type: str) -> str:
    from app.services.nlp_obras import format_materials_for_message

    lista = format_materials_for_message(materials)
    return (
        f"Identifiquei estes materiais para *{obra_type}*:\n\n"
        f"{lista}\n\n"
        "Responda *SIM* para gerar o PDF do orçamento.\n"
        "Responda *NÃO* para cancelar e enviar outro áudio."
    )
