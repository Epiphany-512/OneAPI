"""Dashboard API — management panel backend for OneAPI."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import DEFAULT_ROUTES, get_settings, load_routes
from .providers.base import list_providers
from .router import Router

logger = logging.getLogger("oneapi.dashboard")

# ── In-memory stores ────────────────────────────────────────────────────────

_request_log: deque[dict[str, Any]] = deque(maxlen=500)
_start_time: float = time.time()

# Managed API keys: {key_id: {"key": "sk-...", "name": "...", "created": float, "active": bool}}
_api_keys: dict[str, dict[str, Any]] = {}

# ── Router ──────────────────────────────────────────────────────────────────

dashboard_router = APIRouter(prefix="/dashboard/api")


def _get_router_instance(request: Request) -> Router:
    """Retrieve the global Router from app state (via lifespan)."""
    from .app import router_instance
    if router_instance is None:
        raise HTTPException(500, "Router not initialized")
    return router_instance


# ── Status ──────────────────────────────────────────────────────────────────

@dashboard_router.get("/status")
async def get_status(request: Request):
    from . import __version__
    router = _get_router_instance(request)

    uptime = time.time() - _start_time
    days, rem = divmod(int(uptime), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = f"{days}天 {hours}时 {minutes}分 {seconds}秒"

    registered_providers = []
    for name in sorted(router._providers.keys()):
        provider = router._providers[name]
        registered_providers.append({
            "name": name,
            "base_url": provider.base_url,
            "has_key": bool(provider.api_key),
        })

    # Known providers without keys
    all_known = ["openai", "anthropic", "zhipu", "dashscope", "deepseek", "moonshot"]
    available_providers = []
    for name in all_known:
        if name in router._providers:
            available_providers.append({"name": name, "status": "active"})
        else:
            available_providers.append({"name": name, "status": "no_key"})

    settings = get_settings()
    return {
        "version": __version__,
        "uptime": uptime_str,
        "uptime_seconds": uptime,
        "default_model": settings.oneapi_default_model,
        "registered_providers": registered_providers,
        "all_providers": available_providers,
        "total_models": len(router._routes),
        "total_providers": len(router._providers),
    }


# ── Models ──────────────────────────────────────────────────────────────────

@dashboard_router.get("/models")
async def get_models(request: Request):
    router = _get_router_instance(request)
    models = []
    for model_id, route in router._routes.items():
        if isinstance(route, str):
            provider = route
            fallback = []
        elif isinstance(route, list):
            provider = route[0] if route else "unknown"
            fallback = route[1:] if len(route) > 1 else []
        else:
            provider = "unknown"
            fallback = []

        provider_active = provider in router._providers
        models.append({
            "id": model_id,
            "provider": provider,
            "fallback": fallback,
            "active": provider_active,
        })
    return {"models": models}


# ── Usage ───────────────────────────────────────────────────────────────────

@dashboard_router.get("/usage")
async def get_usage(request: Request):
    """Usage statistics — returns recent log aggregates."""
    now = time.time()
    # Aggregate from request log
    total_requests = len(_request_log)
    success_count = sum(1 for r in _request_log if r.get("status") == "success")
    error_count = total_requests - success_count

    # Per-model stats
    model_stats: dict[str, dict[str, int]] = {}
    for r in _request_log:
        m = r.get("model", "unknown")
        if m not in model_stats:
            model_stats[m] = {"requests": 0, "tokens": 0}
        model_stats[m]["requests"] += 1
        model_stats[m]["tokens"] += r.get("total_tokens", 0)

    # Per-provider stats
    provider_stats: dict[str, dict[str, int]] = {}
    for r in _request_log:
        p = r.get("provider", "unknown")
        if p not in provider_stats:
            provider_stats[p] = {"requests": 0}
        provider_stats[p]["requests"] += 1

    # Recent hourly buckets (last 24h)
    hourly: dict[str, int] = {}
    for r in _request_log:
        ts = r.get("timestamp", now)
        hour_key = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:00")
        hourly[hour_key] = hourly.get(hour_key, 0) + 1

    return {
        "total_requests": total_requests,
        "success_count": success_count,
        "error_count": error_count,
        "model_stats": model_stats,
        "provider_stats": provider_stats,
        "hourly": hourly,
    }


# ── Routes ──────────────────────────────────────────────────────────────────

@dashboard_router.get("/routes")
async def get_routes(request: Request):
    router = _get_router_instance(request)
    routes = {}
    for model_id, route in router._routes.items():
        if isinstance(route, str):
            routes[model_id] = {"provider": route, "fallback": []}
        elif isinstance(route, list):
            routes[model_id] = {"provider": route[0] if route else "", "fallback": route[1:]}
        else:
            routes[model_id] = {"provider": str(route), "fallback": []}
    return {"routes": routes}


@dashboard_router.post("/routes")
async def update_routes(request: Request):
    """Update route configuration — body: {"routes": {"model": "provider"}}"""
    body = await request.json()
    new_routes = body.get("routes")
    if not isinstance(new_routes, dict):
        raise HTTPException(400, "Expected {'routes': {...}}")

    router = _get_router_instance(request)

    # Validate providers exist
    for model_id, route in new_routes.items():
        if isinstance(route, str):
            if route not in router._providers:
                raise HTTPException(400, f"Unknown provider: {route}")
        elif isinstance(route, list):
            for r in route:
                if isinstance(r, str) and r not in router._providers:
                    raise HTTPException(400, f"Unknown provider: {r}")

    # Merge with defaults
    merged = {**DEFAULT_ROUTES, **new_routes}
    router._routes = merged

    # Persist to file if configured
    settings = get_settings()
    if settings.oneapi_routes_file:
        path = Path(settings.oneapi_routes_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_routes, f, ensure_ascii=False, indent=2)
        logger.info("Routes persisted to %s", settings.oneapi_routes_file)

    return {"status": "ok", "routes_count": len(merged)}


# ── Logs ────────────────────────────────────────────────────────────────────

@dashboard_router.get("/logs")
async def get_logs(request: Request):
    limit = min(int(request.query_params.get("limit", 100)), 500)
    logs = list(_request_log)[-limit:]
    return {"logs": logs, "total": len(_request_log)}


# ── API Keys ────────────────────────────────────────────────────────────────

@dashboard_router.get("/keys")
async def list_keys(request: Request):
    keys = []
    for kid, info in _api_keys.items():
        keys.append({
            "id": kid,
            "name": info["name"],
            "key": info["key"][:8] + "..." + info["key"][-4:],
            "created": info["created"],
            "active": info["active"],
        })
    return {"keys": keys}


@dashboard_router.post("/keys")
async def manage_keys(request: Request):
    """Create, revoke, or delete API keys.

    Body:
      {"action": "create", "name": "my-key"}
      {"action": "revoke", "id": "..."}
      {"action": "delete", "id": "..."}
    """
    body = await request.json()
    action = body.get("action")

    if action == "create":
        name = body.get("name", "unnamed")
        kid = str(uuid.uuid4())[:8]
        raw_key = f"sk-oneapi-{uuid.uuid4().hex[:32]}"
        _api_keys[kid] = {
            "key": raw_key,
            "name": name,
            "created": time.time(),
            "active": True,
        }
        logger.info("API key created: %s (%s)", name, kid)
        return {"status": "ok", "id": kid, "key": raw_key, "name": name}

    elif action == "revoke":
        kid = body.get("id")
        if kid not in _api_keys:
            raise HTTPException(404, "Key not found")
        _api_keys[kid]["active"] = False
        return {"status": "ok", "id": kid}

    elif action == "delete":
        kid = body.get("id")
        if kid not in _api_keys:
            raise HTTPException(404, "Key not found")
        del _api_keys[kid]
        return {"status": "ok", "id": kid}

    else:
        raise HTTPException(400, f"Unknown action: {action}")


# ── Helpers (called by app middleware) ──────────────────────────────────────

def log_request(model: str, provider: str, status: str,
                total_tokens: int = 0, latency_ms: float = 0.0,
                error: str = "") -> None:
    """Record a request into the in-memory log."""
    _request_log.append({
        "timestamp": time.time(),
        "time_str": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "provider": provider,
        "status": status,
        "total_tokens": total_tokens,
        "latency_ms": round(latency_ms, 1),
        "error": error,
    })
