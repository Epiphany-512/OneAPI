# 🚀 OneAPI - 统一大模型网关

> 一个 API 搞定所有大模型。轻量级、高性能的代理网关，将 OpenAI、Claude、GLM、通义千问、DeepSeek 等统一为 OpenAI 兼容接口。

[English](./README.md)

## 为什么需要 OneAPI？

切换大模型厂商太痛苦了：
- 不同的 API 格式、不同的 SDK、不同的错误处理
- 换一个模型就得重写对接代码
- 某个厂商挂了，服务也跟着挂

**OneAPI 用一个端点解决所有问题。**

```python
# 之前：被单个厂商绑定
import openai
client = openai.OpenAI(api_key="sk-xxx")

# 之后：通过 OneAPI 访问所有厂商
import openai
client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key=***
)

# GPT-4、Claude、GLM、DeepSeek — 同一个接口
response = client.chat.completions.create(
    model="gpt-4o",           # 或 "claude-sonnet-4"、"glm-4"、"deepseek-chat"
    messages=[{"role": "user", "content": "你好！"}]
)
```

## ✨ 特性

- 🔄 **OpenAI 兼容 API** — 零代码改造，直接替换 base_url 即可
- 🎯 **多厂商支持** — OpenAI、Claude、GLM、通义千问、DeepSeek，持续增加中
- ⚡ **流式输出** — 完整 SSE 支持，和原生体验一致
- 🔀 **负载均衡** — 多个 API Key 自动轮询
- 🛡️ **自动降级** — 某个厂商挂了，自动切换到备选模型
- 🔑 **统一 Key 管理** — 一个 Key 访问所有模型
- 📊 **用量追踪** — 按 Key/模型统计 Token 用量
- 🪶 **轻量级** — 纯 Python，依赖少，启动快
- 🐳 **Docker 就绪** — 一行命令部署

## 快速开始

```bash
# 安装
pip install oneapi-gateway

# 配置
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 启动
oneapi serve --port 8000
```

Docker 部署：
```bash
docker run -p 8000:8000 --env-file .env oneapi/oneapi
```

## 配置说明

```env
# 各厂商 API Key
OPENAI_API_KEY=***
ANTHROPIC_API_KEY=***
ZHIPU_API_KEY=***
DASHSCOPE_API_KEY=***
DEEPSEEK_API_KEY=***

# 网关设置
ONEAPI_API_KEY=***    # 你的统一 API Key
ONEAPI_PORT=8000
ONEAPI_DEFAULT_MODEL=gpt-4o
```

## 模型路由

```json
{
  "gpt-4o": "openai",
  "claude-sonnet-4": "anthropic",
  "glm-4": "zhipu",
  "qwen-plus": "dashscope",
  "deepseek-chat": "deepseek",

  "smart": ["gpt-4o", "claude-sonnet-4", "glm-4"],
  "fast": ["deepseek-chat", "gpt-4o-mini", "glm-4-flash"]
}
```

## API 接口

所有接口兼容 OpenAI 格式：

| 接口 | 说明 |
|------|------|
| `POST /v1/chat/completions` | 对话补全 |
| `POST /v1/completions` | 文本补全 |
| `GET /v1/models` | 获取可用模型列表 |
| `POST /v1/embeddings` | 文本向量（开发中） |

## 路线图

- [x] 核心 OpenAI 兼容 API
- [x] 多厂商支持（OpenAI / Claude / GLM / 通义 / DeepSeek）
- [x] 流式输出
- [x] 负载均衡 & 自动降级
- [ ] Web 管理面板（用量、费用、日志）
- [ ] Token 预算 & 限速
- [ ] Embedding API
- [ ] 自定义 Provider 插件
- [ ] Kubernetes Helm Chart

## 贡献

欢迎贡献！查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT License

---

⭐ 觉得有用就点个 Star 吧！
