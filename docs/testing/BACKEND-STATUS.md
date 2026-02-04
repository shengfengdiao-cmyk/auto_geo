# AutoGeo 后端实现状态

**更新日期**: 2026-01-20
**版本**: v2.0.0
**状态**: 开发完成，可正常运行

---

## 📊 总体进度

| 模块 | 状态 | 完成度 |
|------|------|--------|
| 项目基础架构 | ✅ | 100% |
| 数据库层 | ✅ | 100% |
| 账号授权 | ✅ | 100% |
| 文章管理 | ✅ | 100% |
| 发布模块 | ✅ | 100% |
| GEO功能 | ✅ | 100% |
| 收录检测 | ✅ | 100% |
| 报表统计 | ✅ | 100% |
| 预警通知 | ✅ | 100% |
| 定时任务 | ✅ | 100% |

---

## ✅ 已完成模块

### 1. 项目基础架构

- [x] FastAPI项目结构
- [x] 配置管理 (config.py) - 支持9个AI平台配置
- [x] 依赖清单 (requirements.txt)
- [x] CORS中间件配置
- [x] WebSocket支持 - 实时进度推送
- [x] 生命周期管理 - 优雅关闭机制
- [x] 日志配置 (loguru)

### 2. 数据库层 (8张表)

- [x] SQLite数据库初始化
- [x] SQLAlchemy ORM配置
- [x] 数据模型定义:
  - `Account` - 账号表（加密存储Cookie/StorageState）
  - `Article` - 文章表
  - `PublishRecord` - 发布记录表
  - `Project` - GEO项目表
  - `Keyword` - 关键词表
  - `QuestionVariant` - 问题变体表
  - `IndexCheckRecord` - 收录检测记录表
  - `GeoArticle` - GEO文章表（含质检字段）
- [x] 数据库会话管理 (get_db依赖注入)
- [x] 级联删除配置

### 3. API层 (9个模块)

#### 3.1 账号管理API (`api/account.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/accounts` | 获取账号列表（支持平台/状态筛选） |
| GET | `/api/accounts/{id}` | 获取账号详情 |
| POST | `/api/accounts` | 创建账号 |
| PUT | `/api/accounts/{id}` | 更新账号 |
| DELETE | `/api/accounts/{id}` | 删除账号 |
| POST | `/api/accounts/auth/start` | 开始授权（打开浏览器） |
| GET | `/api/accounts/auth/status/{task_id}` | 查询授权状态 |
| POST | `/api/accounts/auth/confirm/{task_id}` | 手动确认授权完成 |
| DELETE | `/api/accounts/auth/task/{task_id}` | 取消授权任务 |

**支持平台**：知乎、百家号、搜狐号、头条号

#### 3.2 文章管理API (`api/article.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/articles` | 获取文章列表（分页、搜索） |
| GET | `/api/articles/{id}` | 获取文章详情 |
| POST | `/api/articles` | 创建文章 |
| PUT | `/api/articles/{id}` | 更新文章 |
| DELETE | `/api/articles/{id}` | 删除文章 |
| POST | `/api/articles/{id}/publish` | 标记已发布 |

#### 3.3 发布管理API (`api/publish.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/publish/platforms` | 获取支持的发布平台 |
| POST | `/api/publish/create` | 创建批量发布任务 |
| GET | `/api/publish/progress/{task_id}` | 获取发布进度 |
| GET | `/api/publish/records` | 获取发布记录 |
| POST | `/api/publish/retry/{record_id}` | 重试发布 |

**功能**：
- 支持多文章、多账号批量发布
- WebSocket实时进度推送
- 发布失败自动重试机制
- 发布状态持久化

#### 3.4 关键词管理API (`api/keywords.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/keywords/projects` | 获取项目列表 |
| POST | `/api/keywords/projects` | 创建项目 |
| GET | `/api/keywords/projects/{id}` | 获取项目详情 |
| GET | `/api/keywords/projects/{id}/keywords` | 获取项目的关键词 |
| POST | `/api/keywords/distill` | **AI蒸馏关键词**（调用n8n） |
| POST | `/api/keywords/generate-questions` | **生成问题变体** |
| GET | `/api/keywords/keywords/{id}/questions` | 获取问题变体列表 |
| DELETE | `/api/keywords/keywords/{id}` | 停用关键词 |

#### 3.5 GEO文章API (`api/geo.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/geo/generate` | **AI生成文章**（调用n8n） |
| POST | `/api/geo/articles/{id}/check-quality` | **质检文章**（AI味检测） |
| GET | `/api/geo/articles/{id}` | 获取文章详情 |
| GET | `/api/geo/keywords/{keyword_id}/articles` | 获取关键词的文章列表 |
| PUT | `/api/geo/articles/{id}` | 更新文章 |
| DELETE | `/api/geo/articles/{id}` | 删除文章 |
| GET | `/api/geo/articles` | 获取文章列表（支持筛选） |

**质检字段**：
- `quality_score` - 质量评分（0-100）
- `ai_score` - AI味检测分数（0-100，越高越像AI）
- `readability_score` - 可读性评分（0-100）
- `quality_status` - 质检状态（pending/passed/failed）

#### 3.6 收录检测API (`api/index_check.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/index-check/check` | **执行AI平台收录检测** |
| GET | `/api/index-check/records` | 获取检测记录 |
| GET | `/api/index-check/keywords/{id}/hit-rate` | 获取命中率统计 |
| GET | `/api/index-check/records/{id}` | 获取记录详情 |
| DELETE | `/api/index-check/records/{id}` | 删除记录 |

**检测平台**：豆包、通义千问、DeepSeek

#### 3.7 数据报表API (`api/reports.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/reports/projects` | 项目统计数据 |
| GET | `/api/reports/platforms` | 平台收录统计 |
| GET | `/api/reports/trends` | 收录趋势数据 |
| GET | `/api/reports/overview` | 总体概览数据 |

#### 3.8 预警通知API (`api/notifications.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/notifications/check` | 执行预警检查 |
| GET | `/api/notifications/summary` | 获取预警摘要 |
| GET | `/api/notifications/rules` | 获取预警规则列表 |
| POST | `/api/notifications/trigger-test` | 发送测试预警 |
| GET | `/api/notifications/health` | 健康检查 |

#### 3.9 定时任务API (`api/scheduler.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/scheduler/jobs` | 获取所有定时任务 |
| POST | `/api/scheduler/trigger-check` | 手动触发收录检测 |
| POST | `/api/scheduler/trigger-alert` | 手动触发预警检查 |
| GET | `/api/scheduler/status` | 获取服务状态 |
| POST | `/api/scheduler/start` | 启动定时服务 |
| POST | `/api/scheduler/stop` | 停止定时服务 |

**定时任务**：
- 收录检测：每天凌晨2点执行
- 预警检查：可配置周期

---

### 4. 业务服务层 (`services/`)

| 模块 | 功能 |
|------|------|
| `crypto.py` | AES-256加密/解密（Cookie/StorageState） |
| `playwright_mgr.py` | Playwright浏览器管理、授权任务、发布任务 |
| `keyword_service.py` | 关键词蒸馏（n8n）、生成问题变体 |
| `geo_article_service.py` | GEO文章生成（n8n）、质检 |
| `index_check_service.py` | AI平台收录检测（豆包/千问/DeepSeek） |
| `notification_service.py` | 预警通知服务（WebSocket/Log） |
| `scheduler_service.py` | 定时任务管理（APScheduler） |
| `n8n_client.py` | n8n工作流HTTP客户端 |

**Playwright发布适配器** (`services/playwright/publishers/`)：
- `base.py` - 基础发布适配器（抽象类）
- `zhihu.py` - 知乎发布
- `baijiahao.py` - 百家号发布
- `sohu.py` - 搜狐号发布
- `toutiao.py` - 头条号发布

**AI平台检测器** (`services/playwright/ai_platforms/`)：
- `base.py` - 基础检测器（抽象类）
- `doubao.py` - 豆包收录检测
- `qianwen.py` - 通义千问收录检测
- `deepseek.py` - DeepSeek收录检测

---

### 5. 数据模型层 (`schemas/`)

- [x] 通用响应格式 (`ApiResponse`, `ErrorResponse`)
- [x] 账号相关 (`AccountCreate`, `AccountUpdate`, `AccountResponse`, `AccountDetailResponse`)
- [x] 授权相关 (`AuthStartRequest`, `AuthStartResponse`, `AuthStatusResponse`)
- [x] 文章相关 (`ArticleCreate`, `ArticleUpdate`, `ArticleResponse`, `ArticleListResponse`)
- [x] 发布相关 (`PublishTaskCreate`, `PublishTaskResponse`, `PublishProgressResponse`, `PublishStatus`)

---

## 🔧 技术栈

| 组件 | 技术 | 版本 |
|-----|------|------|
| Web框架 | FastAPI | 0.109.0 |
| ASGI服务器 | Uvicorn | 0.27.0 |
| ORM | SQLAlchemy | 2.0.25 |
| 数据验证 | Pydantic | 2.5.3 |
| 浏览器自动化 | Playwright | 1.40.0 |
| 加密 | cryptography | 41.0.7 |
| 日志 | loguru | 0.7.2 |
| 定时任务 | APScheduler | 3.10.4 |
| 异步HTTP | httpx | 0.26.0 |
| WebSocket | websockets | 12.0 |

---

## 📝 运行命令

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium

# 启动服务
python main.py

# 服务地址: http://127.0.0.1:8001
# API文档: http://127.0.0.1:8001/docs
```

---

## 🔌 外部集成

| 服务 | 用途 | 状态 |
|------|------|------|
| n8n | AI关键词蒸馏、文章生成、质检 | ✅ |
| 豆包 | AI平台收录检测 | ✅ |
| 通义千问 | AI平台收录检测 | ✅ |
| DeepSeek | AI平台收录检测 | ✅ |

---

## 🐛 已修复问题 (2026-01-20)

| 问题 | 文件 | 修复内容 |
|------|------|----------|
| 拼写错误 | `main.py:64` | `@asynccontexanager` → `@asynccontextmanager` |
| 拼写错误 | `services/playwright/publishers/base.py:7` | `abstracethod` → `abstractmethod` |
| 拼写错误 | `services/playwright/publishers/base.py:25` | `@abstracethod` → `@abstractmethod` |
| 拼写错误 | `services/playwright/ai_platforms/base.py:35` | `@abstracethod` → `@abstractmethod` |

---

## 📌 配置参数

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 服务地址 | `127.0.0.1:8001` | 后端监听地址 |
| 数据库 | SQLite | `backend/database/auto_geo_v3.db` |
| CORS | `localhost:5173, 5179` | 前端跨域白名单 |
| 发布超时 | 300秒 | 单个发布任务超时 |
| 最大并发 | 3个 | 同时发布的最大数量 |
| 重试次数 | 2次 | 发布失败重试 |
| 定时检测 | 每天凌晨2点 | 收录检测定时任务 |

---

**维护者**: 小a
