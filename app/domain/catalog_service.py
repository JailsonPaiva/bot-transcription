"""Serviço de catálogo com cache e fallback para seed em código."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.domain.catalog_seed import build_seed_rows
from app.services.nlp_obras import CATALOGO_MATERIAIS, set_runtime_catalog

logger = logging.getLogger(__name__)

_CACHE: Dict[str, Any] = {
    "loaded_at": 0.0,
    "catalog": None,  # name -> synonyms
    "prices": None,  # name -> unit_price
    "units": None,  # name -> default_unit
}
_CACHE_TTL_SECONDS = 300


def _seed_catalog_maps() -> Tuple[Dict[str, List[str]], Dict[str, float], Dict[str, str]]:
    catalog = {k: list(v) for k, v in CATALOGO_MATERIAIS.items()}
    rows = build_seed_rows(catalog)
    prices = {r["name"]: float(r["unit_price"]) for r in rows}
    units = {r["name"]: r["default_unit"] for r in rows}
    return catalog, prices, units


def _load_from_supabase() -> Optional[Tuple[Dict[str, List[str]], Dict[str, float], Dict[str, str]]]:
    try:
        from app.services.supabase_client import get_supabase_client

        client = get_supabase_client()
        if not client:
            return None

        result = (
            client.table("materials")
            .select("name,synonyms,default_unit,unit_price,active")
            .eq("active", True)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None

        catalog: Dict[str, List[str]] = {}
        prices: Dict[str, float] = {}
        units: Dict[str, str] = {}
        for row in rows:
            name = str(row["name"]).strip().lower()
            synonyms = row.get("synonyms") or []
            if not isinstance(synonyms, list):
                synonyms = []
            catalog[name] = [str(s) for s in synonyms] or [name]
            prices[name] = float(row.get("unit_price") or 0)
            units[name] = str(row.get("default_unit") or "unidade")
        return catalog, prices, units
    except Exception as exc:
        logger.warning("Falha ao carregar catálogo do Supabase: %s", exc)
        return None


def get_catalog_bundle(force_refresh: bool = False) -> Tuple[Dict[str, List[str]], Dict[str, float], Dict[str, str]]:
    now = time.time()
    if (
        not force_refresh
        and _CACHE["catalog"] is not None
        and now - float(_CACHE["loaded_at"]) < _CACHE_TTL_SECONDS
    ):
        return _CACHE["catalog"], _CACHE["prices"], _CACHE["units"]

    loaded = _load_from_supabase()
    if loaded:
        catalog, prices, units = loaded
        source = "supabase"
    else:
        catalog, prices, units = _seed_catalog_maps()
        source = "seed"

    _CACHE["catalog"] = catalog
    _CACHE["prices"] = prices
    _CACHE["units"] = units
    _CACHE["loaded_at"] = now
    set_runtime_catalog(catalog)
    logger.info("Catálogo carregado (%s): %s itens", source, len(catalog))
    return catalog, prices, units


def get_canonical_names() -> List[str]:
    catalog, _, _ = get_catalog_bundle()
    return sorted(catalog.keys(), key=len, reverse=True)


def get_unit_price(material_name: str) -> float:
    _, prices, _ = get_catalog_bundle()
    key = material_name.strip().lower()
    if key in prices:
        return float(prices[key])
    # tenta sem acento simples
    for name, price in prices.items():
        if name == key:
            return float(price)
    return 0.0


def enrich_materials_with_prices(materials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for item in materials:
        qty_raw = str(item.get("quantidade", "1")).replace(",", ".")
        try:
            qty = float(qty_raw)
        except ValueError:
            qty = 1.0
        unit_price = get_unit_price(str(item.get("material", "")))
        total = round(qty * unit_price, 2)
        enriched.append(
            {
                **item,
                "quantidade": str(item.get("quantidade", "1")),
                "preco_unitario": f"{unit_price:.2f}",
                "preco_total": f"{total:.2f}",
            }
        )
    return enriched


def calc_budget_total(materials: List[Dict[str, Any]]) -> float:
    total = 0.0
    for item in materials:
        try:
            total += float(str(item.get("preco_total", "0")).replace(",", "."))
        except ValueError:
            continue
    return round(total, 2)


def seed_catalog_to_supabase(overwrite_prices: bool = False) -> int:
    """Insere seed no Supabase (upsert por name). Retorna quantidade processada."""
    from app.services.supabase_client import get_supabase_client

    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase não configurado")

    rows = build_seed_rows(CATALOGO_MATERIAIS)
    # upsert
    payload = []
    for row in rows:
        item = {
            "name": row["name"],
            "synonyms": row["synonyms"],
            "default_unit": row["default_unit"],
            "active": True,
        }
        if overwrite_prices:
            item["unit_price"] = row["unit_price"]
        payload.append(item)

    # supabase-py upsert
    result = client.table("materials").upsert(payload, on_conflict="name").execute()
    get_catalog_bundle(force_refresh=True)
    return len(result.data or payload)
