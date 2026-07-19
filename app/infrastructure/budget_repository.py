"""Repositório de orçamentos (histórico)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def save_budget(
    *,
    wa_id: str,
    obra_type: str,
    materials: List[Dict[str, Any]],
    total_amount: float,
    status: str = "sent",
) -> Optional[Dict[str, Any]]:
    try:
        from app.services.supabase_client import get_supabase_client

        client = get_supabase_client()
        if not client:
            logger.warning("Supabase indisponível — orçamento não persistido")
            return None

        payload = {
            "wa_id": wa_id,
            "obra_type": obra_type,
            "materials": materials,
            "total_amount": total_amount,
            "status": status,
        }
        result = client.table("budgets").insert(payload).execute()
        rows = result.data or []
        return rows[0] if rows else payload
    except Exception as exc:
        logger.warning("Falha ao salvar orçamento: %s", exc)
        return None


def get_last_budget(wa_id: str) -> Optional[Dict[str, Any]]:
    try:
        from app.services.supabase_client import get_supabase_client

        client = get_supabase_client()
        if not client:
            return None

        result = (
            client.table("budgets")
            .select("*")
            .eq("wa_id", wa_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.warning("Falha ao buscar último orçamento: %s", exc)
        return None
