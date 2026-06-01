"""FastAPI application — OpenAI-compatible gateway."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings
from .router import Router

router_instance: Router | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global router_instance
    router_instance = Router()
    yield


app = FastAPI(
    title="OneAPI Gateway",
    description="Unified LLM Gateway — OpenAI-compatible API for all providers",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Auth middleware ─────────────────────────────────────────────────────────

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip health check
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    settings = get_settings()
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {settings.oneapi_api_key}":
        return JSONResponse(status_code=401, content={"error": {"message": "Invalid API key"}})
    return await call_next(request)


# ── Chat completions ────────────────────────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", get_settings().oneapi_default_model)
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    kwargs: dict[str, Any] = {
        "messages": messages,
        "temperature": body.get("temperature", 1.0),
        "max_tokens": body.get("max_tokens"),
    }
    # Pass extra params
    for key in ("top_p", "frequency_penalty", "presence_penalty", "stop"):
        if key in body:
            kwargs[key] = body[key]

    if router_instance is None:
        raise HTTPException(500, "Router not initialized")

    if stream:
        return StreamingResponse(
            _wrap_stream(model, **kwargs),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    result = await router_instance.dispatch(model, **kwargs)

    return JSONResponse({
        "id": result.id or str(uuid.uuid4()),
        "object": "chat.completion",
        "created": result.created or int(time.time()),
        "model": result.model or model,
        "choices": [
            {
                "index": c.index,
                "message": c.message,
                "finish_reason": c.finish_reason,
            }
            for c in result.choices
        ],
        "usage": {
            "prompt_tokens": result.usage.prompt_tokens,
            "completion_tokens": result.usage.completion_tokens,
            "total_tokens": result.usage.total_tokens,
        },
    })


async def _wrap_stream(model: str, **kwargs: Any):
    """Wrap provider stream into OpenAI SSE format."""
    async for chunk in router_instance.dispatch_stream(model, **kwargs):
        yield chunk


# ── Models ──────────────────────────────────────────────────────────────────

@app.get("/v1/models")
async def list_models():
    if router_instance is None:
        raise HTTPException(500, "Router not initialized")
    models = router_instance.list_models()
    return {"object": "list", "data": models}


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
