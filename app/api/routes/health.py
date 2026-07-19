from fastapi import APIRouter

from app.core.config import get_settings
from app.infrastructure.store import get_state_store

router = APIRouter(tags=["health"])


def _redis_ping(settings) -> dict:
    if not settings.use_redis:
        return {"configured": False, "ok": None}
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        ok = bool(client.ping())
        return {"configured": True, "ok": ok}
    except Exception as exc:
        return {"configured": True, "ok": False, "error": str(exc)[:120]}


@router.get("/health")
def health():
    settings = get_settings()
    store = get_state_store(settings)
    catalog_size = 0
    try:
        from app.domain.catalog_service import get_catalog_bundle

        catalog, _, _ = get_catalog_bundle()
        catalog_size = len(catalog)
    except Exception:
        catalog_size = 0

    redis_info = _redis_ping(settings)
    return {
        "status": "ok",
        "store": store.__class__.__name__,
        "catalog_size": catalog_size,
        "transcription_service": settings.transcription_service_normalized,
        "message_service": settings.message_service_normalized,
        "use_redis": settings.use_redis,
        "redis": redis_info,
    }
