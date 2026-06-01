"""CLI entry point."""

import argparse
import uvicorn

from .config import get_settings


def main():
    parser = argparse.ArgumentParser(description="OneAPI - Unified LLM Gateway")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve"], help="Command to run")
    parser.add_argument("--host", default=None, help="Host to bind")
    parser.add_argument("--port", type=int, default=None, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    settings = get_settings()
    host = args.host or settings.oneapi_host
    port = args.port or settings.oneapi_port

    print(f"🚀 OneAPI Gateway starting on http://{host}:{port}")
    uvicorn.run(
        "oneapi.app:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level=settings.oneapi_log_level,
    )


if __name__ == "__main__":
    main()
