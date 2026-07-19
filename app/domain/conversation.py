"""Domínio de conversa / máquina de estados."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ConversationState(str, Enum):
    AWAITING_AUDIO = "awaiting_audio"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EDITING = "editing"
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


def _normalize_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    normalized = re.sub(r"[!?.]", "", normalized)
    return (
        normalized.replace("á", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def is_confirmation_message(text: str) -> bool:
    normalized = _normalize_text(text)
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
    normalized = _normalize_text(text)
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


def is_last_budget_request(text: str) -> bool:
    normalized = _normalize_text(text)
    triggers = {
        "ultimo orcamento",
        "manda de novo",
        "reenviar orcamento",
        "ultimo pdf",
        "me manda o ultimo",
        "enviar ultimo orcamento",
    }
    if normalized in triggers:
        return True
    return (
        "ultimo orcamento" in normalized
        or "reenviar orcamento" in normalized
        or "manda de novo o orcamento" in normalized
    )


def is_privacy_policy_request(text: str) -> bool:
    normalized = _normalize_text(text)
    return normalized in {
        "privacidade",
        "politica de privacidade",
        "lgpd",
        "meus dados",
        "dados pessoais",
    } or "politica de privacidade" in normalized


def is_delete_data_request(text: str) -> bool:
    normalized = _normalize_text(text)
    triggers = {
        "apagar meus dados",
        "excluir meus dados",
        "deletar meus dados",
        "apagar dados",
        "excluir dados",
        "remover meus dados",
        "quero apagar meus dados",
    }
    if normalized in triggers:
        return True
    return (
        ("apagar" in normalized or "excluir" in normalized or "deletar" in normalized)
        and "dado" in normalized
    )


def is_show_list_request(text: str) -> bool:
    normalized = _normalize_text(text)
    return normalized in {
        "lista",
        "mostrar",
        "mostrar lista",
        "ver lista",
        "lista atual",
        "materiais",
    }


def parse_remove_item(text: str) -> Optional[Tuple[str, Any]]:
    """
    Retorna ('index', int 1-based) ou ('name', str) ou None.
    Ex.: 'remove 2', 'remover item 3', 'tira cimento'
    """
    normalized = _normalize_text(text)

    m = re.match(r"^(?:remover?|tira[r]?|excluir|apaga[r]?)\s+(?:item\s+)?(\d+)$", normalized)
    if m:
        return ("index", int(m.group(1)))

    m = re.match(r"^(?:remover?|tira[r]?|excluir|apaga[r]?)\s+(.+)$", normalized)
    if m:
        name = m.group(1).strip()
        if name and name not in {"item", "dado", "dados", "meus dados"}:
            return ("name", name)
    return None


def parse_quantity_change(text: str) -> Optional[Tuple[int, str]]:
    """
    Retorna (index 1-based, nova_quantidade_str) ou None.
    Ex.: 'qtd 2=10', 'quantidade 1 para 5', 'muda 3 para 2,5'
    """
    normalized = _normalize_text(text)
    patterns = [
        r"^(?:qtd|quantidade)\s+(\d+)\s*(?:=|para|:)\s*(\d+(?:[.,]\d+)?)$",
        r"^(?:muda[r]?)\s+(\d+)\s+para\s+(\d+(?:[.,]\d+)?)$",
        r"^item\s+(\d+)\s+(?:qtd|quantidade)\s+(\d+(?:[.,]\d+)?)$",
    ]
    for pat in patterns:
        m = re.match(pat, normalized)
        if m:
            qty = m.group(2).replace(",", ".")
            return int(m.group(1)), qty
    return None


def parse_add_material(text: str) -> Optional[str]:
    """Retorna o trecho a extrair após 'adiciona ...' ou None."""
    m = re.match(
        r"^(?:adiciona[r]?|add|inclui[r]?)\s+(.+)$",
        text.strip(),
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return None


def apply_remove_material(
    materials: List[Dict[str, Any]],
    target: Tuple[str, Any],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    kind, value = target
    if not materials:
        return materials, "A lista já está vazia."

    if kind == "index":
        idx = int(value) - 1
        if idx < 0 or idx >= len(materials):
            return materials, f"Não encontrei o item {value}. Use um número da lista."
        removed = materials[idx]
        updated = [m for i, m in enumerate(materials) if i != idx]
        return updated, f"Removi: {removed.get('material', 'item')}."

    name = str(value).lower()
    updated = []
    removed_name = None
    for item in materials:
        mat = str(item.get("material", "")).lower()
        if removed_name is None and (name in mat or mat in name):
            removed_name = item.get("material")
            continue
        updated.append(item)
    if removed_name is None:
        return materials, f"Não encontrei material parecido com '{value}'."
    return updated, f"Removi: {removed_name}."


def apply_quantity_change(
    materials: List[Dict[str, Any]],
    index_1based: int,
    quantity: str,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    idx = index_1based - 1
    if idx < 0 or idx >= len(materials):
        return materials, f"Não encontrei o item {index_1based}."
    updated = [dict(m) for m in materials]
    updated[idx]["quantidade"] = quantity
    return updated, f"Atualizei a quantidade do item {index_1based}."


def build_processing_started_message(msg_type: Optional[str]) -> str:
    if msg_type == "audio":
        return (
            "Recebi seu áudio! Já comecei o processamento "
            "(transcrição e montagem do orçamento). Aguarde um instante…"
        )
    if msg_type == "text":
        return "Recebi sua mensagem! Já estou processando…"
    return "Recebi sua mensagem! Processamento iniciado…"


def build_privacy_policy_message() -> str:
    return (
        "*Privacidade (LGPD)*\n\n"
        "Usamos seu número e o conteúdo das mensagens apenas para gerar "
        "orçamentos de materiais. Áudios e PDFs temporários são descartados "
        "após o processamento.\n\n"
        "Para apagar sessão e histórico deste número, envie: "
        "*apagar meus dados*."
    )


def build_confirmation_message(materials: List[Dict[str, str]], obra_type: str) -> str:
    from app.services.nlp_obras import format_materials_for_message

    lista = format_materials_for_message(materials)
    total = 0.0
    for item in materials:
        try:
            total += float(str(item.get("preco_total", "0")).replace(",", "."))
        except ValueError:
            pass
    total_txt = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return (
        f"Identifiquei estes materiais para *{obra_type}*:\n\n"
        f"{lista}\n\n"
        f"*Total estimado:* {total_txt}\n\n"
        "Responda *SIM* para gerar o PDF ou *NÃO* para cancelar.\n\n"
        "*Editar lista:*\n"
        "• `remove 2` — remove o item 2\n"
        "• `qtd 2=10` — muda a quantidade do item 2\n"
        "• `adiciona 5 saco cimento` — inclui material\n"
        "• `lista` — mostra a lista atual\n\n"
        "Também pode pedir: *último orçamento* ou *privacidade*."
    )
