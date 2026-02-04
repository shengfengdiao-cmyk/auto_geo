# n8n AI 集成架构

> 把所有 AI 能力抽离到 n8n，以后不用在那堆 AI API 里折腾了！

---

## 一、架构设计

### 1.1 新架构对比

```
旧架构（直接调用AI）:
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  后端服务   │─────►│  AI API直连  │─────►│  AI服务商   │
│  (FastAPI)  │      │  (硬编码)    │      │ (DeepSeek)  │
└─────────────┘      └──────────────┘      └─────────────┘

新架构（通过n8n）:
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  后端服务   │─────►│  n8n Webhook │─────►│  AI服务商   │
│  (FastAPI)  │      │  (统一调度)  │      │ (可插拔)     │
└─────────────┘      └──────────────┘      └─────────────┘
```

### 1.2 优势

| 优势 | 说明 |
|------|------|
| **解耦** | AI 逻辑与业务代码分离，换 AI 服务商不用改代码 |
| **可视化** | n8n 图形化编辑，简单直观 |
| **复用** | 工作流可复用，一处修改全局生效 |
| **监控** | n8n 自带执行日志和监控 |
| **扩展** | 新增 AI 功能只需拖拖节点 |

---

## 二、工作流清单

| 工作流 | Webhook路径 | 功能描述 | 状态 |
|--------|-------------|----------|------|
| `keyword-distill.json` | `/webhook/keyword-distill` | 关键词蒸馏 | ✅ |
| `geo-article-generate.json` | `/webhook/geo-article-generate` | GEO文章生成 | ✅ |
| `index-check-analysis.json` | `/webhook/index-check-analysis` | 收录检测分析 | ✅ |
| `generate-questions.json` | `/webhook/generate-questions` | 生成问题变体 | ✅ |

---

## 三、部署步骤

### 3.1 启动 n8n

```bash
# Docker 方式（推荐）
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# 或 npm 方式
npm install n8n -g
n8n start
```

访问 http://localhost:5678

### 3.2 导入工作流

1. 打开 n8n 界面
2. 点击右上角 `...` → `Import from File`
3. 选择 `n8n/workflows/` 下的 JSON 文件
4. 点击 "Import"

### 3.3 配置 AI 凭证

1. n8n 界面 → `Credentials` → `Add Credential`
2. 选择 `OpenAi API`（兼容 DeepSeek）
3. 配置：
   - **API Key**: 你的 DeepSeek API Key
   - **Base URL**: `https://api.deepseek.com/v1`
   - **Model ID**: `deepseek-chat`

### 3.4 激活 Webhook

导入后点击 "Save and activate workflow"，webhook 就开始监听了！

---

## 四、后端调用示例

### 4.1 配置 n8n 地址

```python
# backend/config/n8n_config.py
N8N_WEBHOOK_BASE = "http://localhost:5678/webhook"
```

### 4.2 调用关键词蒸馏

```python
import httpx

async def distill_keywords(keywords: list[str]) -> dict:
    """通过 n8n 调用关键词蒸馏"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{N8N_WEBHOOK_BASE}/keyword-distill",
            json={"keywords": ",".join(keywords)},
            timeout=30.0
        )
        return resp.json()
```

### 4.3 调用文章生成

```python
async def generate_geo_article(keyword: str, platform: str) -> dict:
    """通过 n8n 生成 GEO 文章"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{N8N_WEBHOOK_BASE}/geo-article-generate",
            json={
                "keyword": keyword,
                "platform": platform,
                "requirements": "原创度高，SEO优化"
            },
            timeout=60.0
        )
        return resp.json()
```

---

## 五、API 映射表

| 原后端API | n8n Webhook | 迁移状态 |
|-----------|-------------|----------|
| `POST /api/geo/distill` | `/webhook/keyword-distill` | 待迁移 |
| `POST /api/geo/generate-questions` | `/webhook/generate-questions` | 待迁移 |
| `POST /api/geo/generate-article` | `/webhook/geo-article-generate` | 待迁移 |
| `POST /api/index-check/analyze` | `/webhook/index-check-analysis` | 待迁移 |

---

## 六、故障排查

### Q: Webhook 调用超时？

A: 检查 n8n 是否正常运行，workflow 是否已激活

```bash
curl -X POST http://localhost:5678/webhook/keyword-distill \
  -H "Content-Type: application/json" \
  -d '{"keywords": "测试"}'
```

### Q: AI 调用失败？

A: 检查 n8n 中的凭证配置，确认 API Key 正确

### Q: 响应格式不对？

A: 检查 n8n workflow 中的 "Respond to Webhook" 节点配置

---

**小a提醒**：这个架构改造后，以后换 AI 服务商（比如从 DeepSeek 换到别的）只需要在 n8n 里改个配置，不用动一行代码，这才是正经的解耦！

---

更新日期：2025-01-22
