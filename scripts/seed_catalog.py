"""Seed do catálogo de materiais no Supabase."""
from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

load_dotenv(override=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed do catálogo materials no Supabase")
    parser.add_argument(
        "--overwrite-prices",
        action="store_true",
        help="Sobrescreve unit_price no upsert",
    )
    args = parser.parse_args()

    from app.domain.catalog_service import seed_catalog_to_supabase

    try:
        count = seed_catalog_to_supabase(overwrite_prices=args.overwrite_prices)
        print(f"Seed concluido: {count} materiais processados")
        return 0
    except Exception as exc:
        print(f"Falha no seed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
