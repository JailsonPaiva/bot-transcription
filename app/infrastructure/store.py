"""Persistência de estado (dedupe + sessão de conversa)."""
from __future__ import annotations

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional

from app.core.config import Settings
from app.domain.conversation import ConversationSession

logger = logging.getLogger(__name__)


class StateStore(ABC):
    @abstractmethod
    def claim_message(self, message_id: str, from_number: str) -> bool:
        """True se a mensagem foi reivindicada agora; False se já processada."""

    @abstractmethod
    def get_session(self, wa_id: str) -> ConversationSession:
        ...

    @abstractmethod
    def save_session(self, wa_id: str, session: ConversationSession) -> None:
        ...

    @abstractmethod
    def clear_session(self, wa_id: str) -> None:
        ...

    @abstractmethod
    def check_audio_rate_limit(self, wa_id: str, max_per_hour: int) -> bool:
        """True se ainda pode enviar áudio."""


class InMemoryStateStore(StateStore):
    """Fallback local. Não use em produção multi-instância."""

    def __init__(self, dedupe_ttl: int, session_ttl: int):
        self.dedupe_ttl = dedupe_ttl
        self.session_ttl = session_ttl
        self._dedupe: Dict[str, float] = {}
        self._sessions: Dict[str, tuple[float, dict]] = {}
        self._audio_hits: Dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def claim_message(self, message_id: str, from_number: str) -> bool:
        key = f"{message_id}:{from_number}"
        now = time.time()
        with self._lock:
            self._purge_dedupe(now)
            if key in self._dedupe:
                return False
            self._dedupe[key] = now
            return True

    def get_session(self, wa_id: str) -> ConversationSession:
        now = time.time()
        with self._lock:
            item = self._sessions.get(wa_id)
            if not item:
                return ConversationSession()
            created, payload = item
            if now - created >= self.session_ttl:
                self._sessions.pop(wa_id, None)
                return ConversationSession()
            return ConversationSession.from_dict(payload)

    def save_session(self, wa_id: str, session: ConversationSession) -> None:
        with self._lock:
            self._sessions[wa_id] = (time.time(), session.to_dict())

    def clear_session(self, wa_id: str) -> None:
        with self._lock:
            self._sessions.pop(wa_id, None)

    def check_audio_rate_limit(self, wa_id: str, max_per_hour: int) -> bool:
        now = time.time()
        window = 3600
        with self._lock:
            hits = [t for t in self._audio_hits.get(wa_id, []) if now - t < window]
            if len(hits) >= max_per_hour:
                self._audio_hits[wa_id] = hits
                return False
            hits.append(now)
            self._audio_hits[wa_id] = hits
            return True

    def _purge_dedupe(self, now: float) -> None:
        expired = [k for k, ts in self._dedupe.items() if now - ts >= self.dedupe_ttl]
        for k in expired:
            del self._dedupe[k]


class RedisStateStore(StateStore):
    def __init__(self, redis_client, dedupe_ttl: int, session_ttl: int):
        self.redis = redis_client
        self.dedupe_ttl = dedupe_ttl
        self.session_ttl = session_ttl

    def _dedupe_key(self, message_id: str, from_number: str) -> str:
        return f"bot:dedupe:{message_id}:{from_number}"

    def _session_key(self, wa_id: str) -> str:
        return f"bot:session:{wa_id}"

    def _rate_key(self, wa_id: str) -> str:
        return f"bot:rate:audio:{wa_id}"

    def claim_message(self, message_id: str, from_number: str) -> bool:
        key = self._dedupe_key(message_id, from_number)
        # SET NX EX — atômico
        return bool(self.redis.set(key, "1", nx=True, ex=self.dedupe_ttl))

    def get_session(self, wa_id: str) -> ConversationSession:
        raw = self.redis.get(self._session_key(wa_id))
        if not raw:
            return ConversationSession()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return ConversationSession()
        return ConversationSession.from_dict(payload)

    def save_session(self, wa_id: str, session: ConversationSession) -> None:
        self.redis.set(
            self._session_key(wa_id),
            json.dumps(session.to_dict(), ensure_ascii=False),
            ex=self.session_ttl,
        )

    def clear_session(self, wa_id: str) -> None:
        self.redis.delete(self._session_key(wa_id))

    def check_audio_rate_limit(self, wa_id: str, max_per_hour: int) -> bool:
        key = self._rate_key(wa_id)
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 3600)
        return count <= max_per_hour


_store: Optional[StateStore] = None


def get_state_store(settings: Optional[Settings] = None) -> StateStore:
    global _store
    if _store is not None:
        return _store

    if settings is None:
        from app.core.config import get_settings

        settings = get_settings()

    if settings.use_redis:
        try:
            import redis

            client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            _store = RedisStateStore(
                client,
                dedupe_ttl=settings.dedupe_ttl_seconds,
                session_ttl=settings.session_ttl_seconds,
            )
            logger.info("StateStore: Redis (%s)", settings.redis_url)
            return _store
        except Exception as exc:
            logger.warning(
                "Redis indisponível (%s). Usando InMemoryStateStore (não escalável).",
                exc,
            )

    _store = InMemoryStateStore(
        dedupe_ttl=settings.dedupe_ttl_seconds,
        session_ttl=settings.session_ttl_seconds,
    )
    logger.info("StateStore: InMemory")
    return _store


def reset_state_store() -> None:
    global _store
    _store = None
