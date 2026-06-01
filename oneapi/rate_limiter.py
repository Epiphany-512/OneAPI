"""Rate limiter for API requests."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class TokenBucket:
    """Simple token bucket rate limiter."""

    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """Return seconds until tokens are available."""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            available = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            if available >= tokens:
                return 0.0
            needed = tokens - available
            return needed / self.refill_rate


class RateLimiter:
    """Per-key rate limiter with configurable limits."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_day: int = 10000,
        tokens_per_day: int = 1_000_000,
    ) -> None:
        self.rpm = requests_per_minute
        self.rpd = requests_per_day
        self.tpd = tokens_per_day

        self._minute_buckets: dict[str, TokenBucket] = {}
        self._day_buckets: dict[str, TokenBucket] = {}
        self._token_usage: dict[str, int] = defaultdict(int)
        self._last_reset: float = time.time()
        self._lock = Lock()

    def _get_bucket(self, storage: dict[str, TokenBucket], key: str, capacity: int, rate: float) -> TokenBucket:
        if key not in storage:
            storage[key] = TokenBucket(capacity=capacity, refill_rate=rate)
        return storage[key]

    def check(self, api_key: str, tokens: int = 0) -> tuple[bool, str]:
        """Check if request is allowed. Returns (allowed, reason)."""
        # Daily reset
        now = time.time()
        if now - self._last_reset > 86400:
            self._token_usage.clear()
            self._day_buckets.clear()
            self._last_reset = now

        # Per-minute limit
        minute_bucket = self._get_bucket(self._minute_buckets, api_key, self.rpm, self.rpm / 60.0)
        if not minute_bucket.consume():
            wait = minute_bucket.wait_time()
            return False, f"Rate limit: {self.rpm} requests/minute. Retry after {wait:.1f}s"

        # Per-day limit
        day_bucket = self._get_bucket(self._day_buckets, api_key, self.rpd, self.rpd / 86400.0)
        if not day_bucket.consume():
            return False, f"Rate limit: {self.rpd} requests/day exceeded"

        # Token usage
        if tokens > 0:
            current = self._token_usage[api_key]
            if current + tokens > self.tpd:
                return False, f"Token limit: {self.tpd} tokens/day exceeded"
            self._token_usage[api_key] = current + tokens

        return True, ""

    def get_usage(self, api_key: str) -> dict:
        """Get usage stats for a key."""
        return {
            "tokens_used_today": self._token_usage.get(api_key, 0),
            "tokens_limit": self.tpd,
            "rpm_limit": self.rpm,
            "rpd_limit": self.rpd,
        }


# Global instance
rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    return rate_limiter
