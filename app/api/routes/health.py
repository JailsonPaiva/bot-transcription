from fastapi import APIRouter

from app.core.config import get_settings
from app.infrastructure.store import get_state_store

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    store = get_state_store(settings)
    return {
        "status": "ok",
        "store": store.__class__.__name__,
        "transcription_service": settings.transcription_service_normalized,
        "message_service": settings.message_service_normalized,
        "use_redis": settings.use_redis,
    }
