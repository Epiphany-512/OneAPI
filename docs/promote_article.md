# 🔥 用了 OneAPI 之后，我再也不想直接调 LLM 原生接口了

## 一个 API Key 打通所有大模型，不香吗？

你是不是也经历过这种痛苦——

项目里接了 GPT-4，老板说要换成 Claude，产品经理又加了个 DeepSeek，最后还有个通义千问的需求……于是你的代码里塞满了各家 SDK，每个都有不同的调用方式、不同的错误处理、不同的流式格式。改一个模型，改一套代码。某个厂商挂了，你的服务也跟着挂。😡

**痛点很明确：LLM 厂商百花齐放，但 API 格式各搞各的，接入和维护成本爆炸。**

如果有一个网关，让我只写一套 OpenAI 格式的代码，就能无缝切换 GPT-4、Claude、GLM、通义千问、DeepSeek……甚至某个厂商挂了还能自动降级到备选模型呢？

这就是 **OneAPI** 干的事 🎯

> GitHub 地址：[https://github.com/Epiphany-512/OneAPI](https://github.com/Epiphany-512/OneAPI)

---

## 🚀 一分钟看懂 OneAPI 是什么

OneAPI 是一个用 **Python + FastAPI** 实现的统一 LLM 网关。它把 OpenAI、Claude、GLM、通义千问、DeepSeek 等多家大模型统一到 **一个 OpenAI 兼容的 API 接口** 后面。

简单说：**你只需要会调 OpenAI 的接口，就能用所有主流大模型。**

---

## 💻 怎么用？三步搞定

### 第一步：安装 & 配置

```bash
pip install oneapi-gateway

cp .env.example .env
# 编辑 .env，填入你的各家 API Key
```

### 第二步：启动网关

```bash
oneapi serve --port 8000
```

或者用 Docker 一键部署：

```bash
docker run -p 8000:8000 --env-file .env oneapi/oneapi
```

### 第三步：像调 OpenAI 一样调所有模型

```python
import openai

# 唯一要改的：把 base_url 指向 OneAPI
client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="oneapi-key"  # OneAPI 统一的 Key
)

# 🎉 就这样，换个模型名就行
response = client.chat.completions.create(
    model="gpt-4o",  # 或 "claude-sonnet-4" / "glm-4" / "deepseek-chat"
    messages=[{"role": "user", "content": "你好！"}]
)
print(response.choices[0].message.content)
```

**你没看错，零代码改造。** 只需要改 `base_url` 和 `api_key`，剩下的代码一行不动，OpenAI SDK 原生支持。

流式输出也一样丝滑：

```python
stream = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "讲个笑话"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

---

## 🎯 还能玩高级操作：Fallback 链

这个功能我真的吹爆 💯

你可以定义模型别名，配一个 fallback 链。比如你想用 GPT-4，但它挂了就自动切 Claude，再挂就切 GLM：

```json
{
  "smart": ["gpt-4o", "claude-sonnet-4", "glm-4"],
  "fast": ["deepseek-chat", "gpt-4o-mini", "glm-4-flash"]
}
```

```python
# 直接用别名调用
response = client.chat.completions.create(
    model="smart",
    messages=[{"role": "user", "content": "分析一下这段代码"}]
)
# OneAPI 自动按顺序尝试，哪个能用用哪个 ✅
```

再也不怕单点故障了！

---

## ✨ 核心特性一览

| 特性 | 说明 |
|------|------|
| 🔄 **OpenAI 兼容** | 标准 `/v1/chat/completions` 接口，OpenAI SDK 直接用 |
| 🎯 **多厂商支持** | OpenAI、Claude、GLM、通义千问、DeepSeek 等 |
| ⚡ **SSE 流式输出** | 完整支持，体验和原生一样 |
| 🔀 **负载均衡** | 多个 Key 自动轮询，充分利用额度 |
| 🛡️ **自动降级** | Fallback 链，故障自动切换 |
| 🔑 **统一 Key 管理** | 一个 Key 访问所有模型 |
| 📊 **用量追踪** | 按 Key/模型统计 Token 用量和费用 |
| 🪶 **轻量级** | 纯 Python，依赖少，启动快 |
| 🐳 **Docker 就绪** | 一行命令部署，生产环境友好 |

架构也很清晰：

```
你的应用（OpenAI SDK）
       │
       ▼
  OneAPI 网关（FastAPI）
       │
    ┌──┼──────────┬──────────┐
    │  │          │          │
   路由  负载均衡   格式转换   降级管理
    │  │          │          │
    └──┴──────────┴──────────┘
       │
       ▼
  OpenAI / Claude / GLM / 通义 / DeepSeek ...
```

---

## 🤔 适用场景

- **个人开发者**：多个模型轮着用，哪个便宜用哪个
- **创业团队**：不想被单一厂商绑死，灵活切换
- **企业项目**：统一 API 入口，方便监控和管理
- **AI 应用集成**：ChatBot、Agent、RAG……底层模型随意换

---

## 📌 最后

OneAPI 解决的是一个很实际的问题：**大模型越来越多，但接入不应该越来越复杂。**

项目完全开源，MIT 协议，代码简洁，欢迎吐槽和贡献 💪

如果你也在做多模型接入，或者被各家 API 折磨过，不妨试试：

👉 **[GitHub: Epiphany-512/OneAPI](https://github.com/Epiphany-512/OneAPI)**

觉得有用的话，点个 ⭐ Star 支持一下，这对独立开发者来说真的很重要！

有问题欢迎提 Issue，也欢迎 PR 一起完善 🤝
