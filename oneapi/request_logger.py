"""Request logger — in-memory request log for dashboard."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class RequestLog:
    timestamp: float
    method: str
    path: str
    model: str
    provider: str
    status: int
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    api_key_suffix: str = ""  # last 4 chars
    error: str = ""


class RequestLogger:
    """Thread-safe in-memory request log with max retention."""

    def __init__(self, max_entries: int = 1000) -> None:
        self._logs: deque[RequestLog] = deque(maxlen=max_entries)
        self._lock = Lock()

    def log(self, entry: RequestLog) -> None:
        with self._lock:
            self._logs.append(entry)

    def get_recent(self, limit: int = 100, offset: int = 0) -> list[dict]:
        with self._lock:
            logs = list(self._logs)
        logs.reverse()
        page = logs[offset : offset + limit]
        return [
            {
                "timestamp": l.timestamp,
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(l.timestamp)),
                "method": l.method,
                "path": l.path,
                "model": l.model,
                "provider": l.provider,
                "status": l.status,
                "latency_ms": round(l.latency_ms, 1),
                "tokens_in": l.tokens_in,
                "tokens_out": l.tokens_out,
                "api_key_suffix": l.api_key_suffix,
                "error": l.error,
            }
            for l in page
        ]

    def get_stats(self) -> dict:
        with self._lock:
            logs = list(self._logs)

        if not logs:
            return {
                "total_requests": 0,
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "avg_latency_ms": 0,
                "error_rate": 0,
                "by_model": {},
                "by_provider": {},
            }

        total = len(logs)
        errors = sum(1 for l in logs if l.status >= 400)
        total_in = sum(l.tokens_in for l in logs)
        total_out = sum(l.tokens_out for l in logs)
        avg_latency = sum(l.latency_ms for l in logs) / total

        by_model: dict[str, int] = {}
        by_provider: dict[str, int] = {}
        for l in logs:
            by_model[l.model] = by_model.get(l.model, 0) + 1
            by_provider[l.provider] = by_provider.get(l.provider, 0) + 1

        return {
            "total_requests": total,
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "avg_latency_ms": round(avg_latency, 1),
            "error_rate": round(errors / total * 100, 1),
            "by_model": by_model,
            "by_provider": by_provider,
        }

    def clear(self) -> None:
        with self._lock:
            self._logs.clear()


# Global instance
request_logger = RequestLogger()
