"""Simple token-bucket rate limiter for external API calls."""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """Token-bucket rate limiter with minute-based capacity.

    The limiter is intentionally blocking and conservative so we can stay
    within free-tier quotas for external services (e.g., LLM or embedding
    endpoints). A ``requests_per_minute`` value of ``None`` or ``<=0``
    disables limiting.
    """

    def __init__(self, requests_per_minute: int | None) -> None:
        self.capacity = requests_per_minute if requests_per_minute and requests_per_minute > 0 else None
        self.tokens = float(self.capacity) if self.capacity else None
        self.refill_interval = 60.0 / self.capacity if self.capacity else None
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        if self.capacity is None or self.refill_interval is None or self.tokens is None:
            return

        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = int(elapsed // self.refill_interval)
        if tokens_to_add > 0:
            self.tokens = min(float(self.capacity), self.tokens + tokens_to_add)
            self.last_refill += tokens_to_add * self.refill_interval

    def acquire(self) -> None:
        """Block until a token is available or limiting is disabled."""
        if self.capacity is None or self.refill_interval is None or self.tokens is None:
            return

        while True:
            with self._lock:
                self._refill()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait_time = max(self.refill_interval - (time.monotonic() - self.last_refill), 0.0)

            # Sleep outside the lock to allow other threads to progress
            time.sleep(wait_time if wait_time > 0 else self.refill_interval)
