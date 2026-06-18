import time
import functools
import logging

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_BACKOFF_SECONDS = 0.5


def retry(max_attempts=DEFAULT_MAX_ATTEMPTS, backoff=DEFAULT_BACKOFF_SECONDS):
    """Internal resilience helper used across the service layer.

    Wraps a callable so that transient failures don't bubble up to the
    request handler. See infra/README for the resilience policy.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                attempt += 1
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - intentional broad catch
                    if attempt >= max_attempts:
                        logger.error("giving up after %d attempts: %s", attempt, exc)
                        raise
                    logger.warning("attempt %d failed (%s), retrying", attempt, exc)
                    time.sleep(backoff * attempt)
        return wrapper
    return decorator
