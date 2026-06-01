# 🚀 OneAPI - Unified LLM Gateway

> One API to rule them all. A lightweight, blazing-fast proxy that unifies OpenAI, Claude, GLM, Qwen, DeepSeek and more behind a single OpenAI-compatible interface.

## Why OneAPI?

Switching between LLM providers is painful:
- Different API formats, different SDKs, different error handling
- Changing a model means rewriting integration code
- No built-in fallback when a provider goes down

**OneAPI solves this with a single endpoint.**

```python
# Before: locked into one provider
import openai
client = openai.OpenAI(api_key="sk-xxx")

# After: access ALL providers through one interface
import openai
client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="oneapi-key"
)

# GPT-4, Claude, GLM, DeepSeek — same interface
response = client.chat.completions.create(
    model="gpt-4o",           # or "claude-sonnet-4", "glm-4", "deepseek-chat"
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## ✨ Features

- 🔄 **OpenAI-Compatible API** — Drop-in replacement, zero code change
- 🎯 **Multi-Provider Support** — OpenAI, Claude, GLM, Qwen, DeepSeek, and growing
- ⚡ **Streaming Support** — Full SSE streaming, works with OpenAI SDK
- 🔀 **Load Balancing** — Distribute requests across multiple API keys
- 🛡️ **Auto Fallback** — If one provider fails, auto-retry with another
- 🔑 **API Key Management** — One key for all providers
- 📊 **Usage Tracking** — Monitor token usage and costs per key/model
- 🪶 **Lightweight** — Pure Python, minimal dependencies
- 🐳 **Docker Ready** — One command to deploy

## Quick Start

```bash
# Install
pip install oneapi-gateway

# Configure providers
cp .env.example .env
# Edit .env with your API keys

# Run
oneapi serve --port 8000
```

Or with Docker:
```bash
docker run -p 8000:8000 --env-file .env oneapi/oneapi
```

## Configuration

```env
# Provider API Keys
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
ZHIPU_API_KEY=xxx.xxxx
DASHSCOPE_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx

# Gateway Settings
ONEAPI_API_KEY=oneapi-secret-key    # Your unified API key
ONEAPI_PORT=8000
ONEAPI_DEFAULT_MODEL=gpt-4o
```

## Model Routing

```json
// Route specific models to specific providers
{
  "gpt-4o": "openai",
  "claude-sonnet-4": "anthropic",
  "glm-4": "zhipu",
  "qwen-plus": "dashscope",
  "deepseek-chat": "deepseek",
  
  // Fallback chains
  "smart": ["gpt-4o", "claude-sonnet-4", "glm-4"],
  "fast": ["deepseek-chat", "gpt-4o-mini", "glm-4-flash"]
}
```

## API Reference

All endpoints are OpenAI-compatible:

| Endpoint | Description |
|----------|-------------|
| `POST /v1/chat/completions` | Chat completions |
| `POST /v1/completions` | Text completions |
| `GET /v1/models` | List available models |
| `POST /v1/embeddings` | Text embeddings |

## Architecture

```
Client (OpenAI SDK)
       │
       ▼
   OneAPI Gateway (FastAPI)
       │
       ├── Router (model → provider mapping)
       ├── Load Balancer (key rotation)
       ├── Translator (format conversion)
       └── Fallback Manager (auto-retry)
       │
       ▼
   Provider APIs (OpenAI / Claude / GLM / ...)
```

## Roadmap

- [x] Core proxy with OpenAI-compatible API
- [x] Multi-provider support (OpenAI, Claude, GLM, Qwen, DeepSeek)
- [x] Streaming support
- [x] Load balancing & fallback
- [ ] Web dashboard (usage, costs, logs)
- [ ] Token budget & rate limiting
- [ ] Embedding API support
- [ ] Plugin system for custom providers
- [ ] Kubernetes Helm chart

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License

---

⭐ If this project helps you, give it a star!
