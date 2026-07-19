"""Utilitário de retry com backoff."""
from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

from app.core.config import Settings

logger = logging.getLogger(__name__)
T = TypeVar("T")


def with_retries(
    operation_name: str,
    fn: Callable[[], T],
    settings: Settings,
    *,
    exceptions: tuple = (Exception,),
) -> T:
    attempts = max(1, settings.http_max_retries)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except exceptions as exc:
            last_error = exc
            if attempt >= attempts:
                break
            delay = settings.http_retry_backoff_seconds * attempt
            logger.warning(
                "%s falhou (tentativa %s/%s): %s. Retry em %.1fs",
                operation_name,
                attempt,
                attempts,
                exc,
                delay,
            )
            time.sleep(delay)

    assert last_error is not None
    raise last_error
