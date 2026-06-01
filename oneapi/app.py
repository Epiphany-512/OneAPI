"""FastAPI application — OpenAI-compatible gateway."""

from __future__ import annotations

import json
import pathlib
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

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


# ── Dashboard routes ────────────────────────────────────────────────────────

from .dashboard import dashboard_router  # noqa: E402

app.include_router(dashboard_router)


# ── Auth middleware ─────────────────────────────────────────────────────────

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip health check, docs, and static files
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc") or \
       request.url.path.startswith("/static"):
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


# ── Embeddings ──────────────────────────────────────────────────────────────

@app.post("/v1/embeddings")
async def embeddings(request: Request):
    body = await request.json()
    model = body.get("model", "text-embedding-ada-002")
    input_texts = body.get("input", [])

    if isinstance(input_texts, str):
        input_texts = [input_texts]

    if router_instance is None:
        raise HTTPException(500, "Router not initialized")

    # Route to OpenAI-compatible provider for embeddings
    from .providers.base import get_provider
    from .config import get_settings

    settings = get_settings()
    provider = None
    route = router_instance._routes.get(model)
    if route and isinstance(route, str):
        provider = router_instance._providers.get(route)

    if provider is None and settings.openai_api_key:
        provider = router_instance._providers.get("openai")

    if provider is None:
        raise HTTPException(400, f"No provider available for model '{model}'")

    import httpx
    url = f"{provider.base_url}/embeddings"
    payload = {"model": model, "input": input_texts}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=provider._headers())
        if resp.status_code != 200:
            raise HTTPException(resp.status_code, resp.text)
        return JSONResponse(resp.json())


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ── Dashboard static files & page ──────────────────────────────────────────

_static_dir = pathlib.Path(__file__).resolve().parent.parent / "static"


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page():
    return FileResponse(_static_dir / "index.html")


if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
