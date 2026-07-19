"""Application factory FastAPI."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    settings = get_settings()
    app = FastAPI(
        title="Bot Orçamento Obras",
        version="1.1.0",
        description="WhatsApp bot para orçamento de materiais de construção",
    )
    app.state.settings = settings
    app.include_router(api_router)
    return app


app = create_app()
