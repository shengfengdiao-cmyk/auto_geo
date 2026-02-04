# AutoGeo AI搜索引擎优化自动化平台

> 开发者备注：一个用 Electron + Vue3 + FastAPI + n8n + Playwright 搞的智能平台，自动发布文章、检测收录、生成GEO内容！AI能力全部通过n8n工作流调度，解耦设计，想换AI服务商只需改个配置！

## 功能特性

### 核心功能
- ✅ **多平台发布**：知乎、百家号、搜狐、头条号
- ✅ **账号管理**：安全的 Cookie 存储和授权
- ✅ **文章编辑**：WangEditor 5 富文本编辑器，所见即所得，支持图片上传
- ✅ **批量发布**：一键发布到多个平台
- ✅ **发布进度**：实时查看发布状态

### GEO/AI优化功能 ✨
- ✅ **关键词管理**：项目与关键词管理、关键词蒸馏
- ✅ **收录检测**：自动检测AI搜索引擎收录情况(豆包/千问/DeepSeek)
- ✅ **GEO文章生成**：基于关键词自动生成SEO优化文章
- ✅ **数据报表**：收录趋势、平台分布、关键词排名
- ✅ **预警通知**：命中率下降、零收录、持续低迷预警
- ✅ **定时任务**：每日自动检测、失败重试
- ✅ **WebSocket推送**：实时进度通知

### 管理功能 📊
- ✅ **候选人管理**：HR候选人信息管理与跟踪
- ✅ **知识库管理**：RAGflow知识库接入与管理
- ✅ **定时任务调度**：可视化定时任务配置与管理
- ✅ **数据仪表盘**：实时数据概览与可视化分析

## 技术栈

| 层级 | 技术选型 |
|------|---------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia + ECharts + WangEditor 5 |
| 后端 | FastAPI + SQLAlchemy + Playwright + APScheduler |
| AI中台 | n8n 工作流引擎 + DeepSeek API |
| 桌面 | Electron |
| 数据库 | SQLite |

## 快速开始

### 环境要求

- **Node.js**: 18+
- **Python**: 3.10+
- **Docker** (可选，用于运行 n8n)
- **操作系统**: Windows / macOS / Linux

### 1. 安装依赖

**后端依赖**：

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

**前端依赖**：

```bash
cd ../fronted
npm install
```

### 2. 启动 n8n (AI工作流引擎)

```bash
# 方式1: Docker (推荐)
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# 方式2: npm
npm install -g n8n
n8n start
```

然后访问 http://localhost:5678，导入 `n8n/workflows/` 下的工作流文件。

详细配置请查看 [n8n 集成文档](./n8n/README.md)

### 3. 启动后端

```bash
cd backend
python main.py
```

后端服务运行在 `http://127.0.0.1:8001`

### 4. 启动前端

```bash
cd fronted
npm run dev
```

---

## 🛠️ 项目工具

AutoGeo 提供了便捷的工具脚本，帮助你快速启动和清理项目：

### 快速启动工具

**`quickstart.bat` / `quickstart.cmd`** ⭐ 推荐

一键管理项目的所有操作：启动服务、重启服务、清理缓存

```bash
# 双击运行或在命令行执行
quickstart.bat
```

**主菜单**：
- [1] 启动后端服务（新窗口）
- [2] 启动前端 Electron 应用（新窗口）
- [3] 重启后端服务
- [4] 重启前端服务
- [5] 清理项目缓存
- [6] 退出（关闭所有服务）

**清理子菜单**（选项 5）：
- [1] 快速清理（安全）- Python缓存、Vite缓存、数据库临时文件、日志
- [2] 完全清理（激进）- 包括 node_modules（需重新安装）
- [3] 返回主菜单

**特性**：
- ✅ 自动检查依赖文件
- ✅ 端口占用检测
- ✅ 窗口管理（自动关闭）
- ✅ **集成清理功能**（v2.7.0 新增）

### 独立清理工具

**`cleanup.bat`**

单独的清理工具，功能与 quickstart 的选项 [5] 相同：

```bash
# 双击运行或在命令行执行
cleanup.bat
```

提供更多自定义清理选项（8个选项 + 预览功能）

**清理选项**：

| 选项 | 说明 | 可恢复 |
|------|------|--------|
| **[1] 快速清理** | Python缓存、Vite缓存、数据库临时文件、日志 | 自动恢复 |
| **[2] 完全清理** | 包括 node_modules（需重新安装） | `npm install` |
| **[3] 自定义清理** | 选择性清理特定项目 | 按需恢复 |
| **[4] 预览大小** | 查看可清理的文件大小 | - |

**清理内容**：
- 🗑️ Python缓存：`__pycache__/`, `*.pyc`
- 🗑️ Node.js缓存：`.vite/`
- 🗑️ 数据库临时文件：`*.wal`, `*.shm`
- 🗑️ 日志文件：`*.log`
- 🗑️ 系统临时文件：`.DS_Store`, `Thumbs.db`
- 🗑️ 测试缓存：`.pytest_cache/`
- 🗑️ IDE缓存：`.idea/`

**注意**：
- 快速清理是安全的，不影响开发
- 完全清理后需要重新安装依赖
- 数据库文件（`.db`）不会被删除

---

## API 端点

### 基础 API
- `GET /` - 健康检查
- `GET /api/health` - 服务状态
- `GET /api/platforms` - 获取支持的平台列表

### 账号管理 API
- `GET /api/accounts` - 获取账号列表
- `POST /api/accounts` - 创建账号
- `GET /api/accounts/{account_id}` - 获取账号详情
- `PUT /api/accounts/{account_id}` - 更新账号信息
- `DELETE /api/accounts/{account_id}` - 删除账号
- `POST /api/accounts/{account_id}/authorize` - 账号授权

### 文章管理 API
- `GET /api/articles` - 获取文章列表
- `POST /api/articles` - 创建文章
- `GET /api/articles/{article_id}` - 获取文章详情
- `PUT /api/articles/{article_id}` - 更新文章
- `DELETE /api/articles/{article_id}` - 删除文章

### 发布管理 API
- `POST /api/publish/{article_id}` - 发布文章到指定平台
- `GET /api/publish/tasks` - 获取发布任务列表
- `GET /api/publish/tasks/{task_id}` - 获取发布任务详情
- `POST /api/publish/tasks/{task_id}/retry` - 重试发布

### GEO/关键词 API
- `GET /api/geo/projects` - 获取项目列表
- `POST /api/geo/projects` - 创建项目
- `GET /api/geo/projects/{id}/keywords` - 获取项目关键词
- `POST /api/geo/distill` - 关键词蒸馏
- `POST /api/geo/generate-article` - 生成GEO文章

### 收录检测 API
- `POST /api/index-check/check` - 执行收录检测
- `GET /api/index-check/records` - 获取检测记录
- `GET /api/index-check/trend/{keyword_id}` - 获取关键词趋势

### 候选人管理 API
- `GET /api/candidates` - 获取候选人列表
- `POST /api/candidates` - 创建候选人
- `GET /api/candidates/{candidate_id}` - 获取候选人详情
- `PUT /api/candidates/{candidate_id}` - 更新候选人信息
- `DELETE /api/candidates/{candidate_id}` - 删除候选人

### 知识库管理 API
- `GET /api/knowledge` - 获取知识库列表
- `POST /api/knowledge` - 创建知识库
- `POST /api/knowledge/{kb_id}/upload` - 上传知识库文档
- `DELETE /api/knowledge/{kb_id}` - 删除知识库

### 报表 API
- `GET /api/reports/overview` - 数据总览
- `GET /api/reports/trend/index` - 收录趋势
- `GET /api/reports/ranking/keywords` - 关键词排名

### 预警通知 API
- `POST /api/notifications/check` - 检查预警
- `GET /api/notifications/summary` - 预警汇总
- `GET /api/notifications/rules` - 预警规则

### 定时任务 API
- `GET /api/scheduler/jobs` - 定时任务列表
- `POST /api/scheduler/jobs` - 创建定时任务
- `PUT /api/scheduler/jobs/{job_id}` - 更新定时任务
- `DELETE /api/scheduler/jobs/{job_id}` - 删除定时任务
- `POST /api/scheduler/start` - 启动定时任务服务
- `POST /api/scheduler/stop` - 停止定时任务服务

### 文件上传 API
- `POST /api/upload/image` - 上传图片

## 目录结构

```
auto_geo/
├── backend/              # 后端服务 (FastAPI)
│   ├── api/              # API 路由
│   │   ├── account.py       # 账号管理API
│   │   ├── article.py       # 文章管理API
│   │   ├── candidate.py     # 候选人管理API
│   │   ├── geo.py           # GEO/关键词API
│   │   ├── index_check.py   # 收录检测API
│   │   ├── keywords.py      # 关键词管理API
│   │   ├── knowledge.py     # 知识库管理API
│   │   ├── notifications.py # 预警通知API
│   │   ├── publish.py       # 发布管理API
│   │   ├── reports.py       # 数据报表API
│   │   ├── scheduler.py     # 定时任务API
│   │   └── upload.py        # 文件上传API
│   ├── database/         # 数据库
│   │   ├── models.py       # 数据模型
│   │   └── __init__.py     # 数据库初始化
│   ├── services/         # 业务服务
│   │   ├── crypto.py              # 加密服务
│   │   ├── geo_article_service.py # GEO文章生成
│   │   ├── index_check_service.py # 收录检测服务
│   │   ├── keyword_service.py     # 关键词服务
│   │   ├── n8n_service.py         # n8n webhook封装
│   │   ├── notification_service.py # 预警通知服务
│   │   ├── playwright_mgr.py      # Playwright管理器
│   │   ├── publisher.py           # 发布器
│   │   ├── scheduler_service.py   # 定时任务服务
│   │   └── websocket_manager.py   # WebSocket管理
│   ├── main.py           # 入口文件
│   └── requirements.txt  # Python 依赖
│
├── fronted/              # 前端应用 (Electron + Vue3)
│   ├── electron/         # Electron 主进程
│   ├── src/              # Vue 源码
│   │   ├── views/        # 页面视图
│   │   │   ├── account/    # 账号管理页面
│   │   │   ├── article/    # 文章编辑页面
│   │   │   ├── candidate/  # 候选人管理页面
│   │   │   ├── dashboard/  # 数据仪表盘
│   │   │   ├── geo/        # GEO功能页面
│   │   │   ├── knowledge/  # 知识库管理页面
│   │   │   ├── publish/    # 发布管理页面
│   │   │   ├── scheduler/  # 定时任务页面
│   │   │   └── settings/   # 设置页面
│   │   └── services/api/  # API封装
│   ├── package.json      # Node 依赖
│   └── vite.config.ts    # Vite 配置
│
├── n8n/                  # n8n AI工作流
│   ├── workflows/        # 工作流JSON文件
│   │   ├── geov0.0.1.json     # GEO工作流 v0.0.1
│   │   └── GEOv0.0.2.json     # GEO工作流 v0.0.2
│   └── README.md         # n8n集成文档
│
├── docs/                 # 项目文档
│   ├── TEAM_COLLABORATION_GUIDE.md  # 团队协作规范
│   ├── PROJECT_INFO.md             # 项目信息记录
│   ├── PRD-GEO-Automation.md       # GEO自动化PRD
│   ├── architecture/               # 架构文档
│   ├── features/                   # 功能设计文档
│   ├── testing/                    # 测试文档
│   ├── overview/                   # 概览文档
│   ├── plans/                      # 开发计划
│   ├── changelog/                  # 变更日志
│   └── security/                   # 安全文档
│
├── .github/              # GitHub配置
│   ├── pull_request_template.md    # PR模板
│   └── ISSUE_TEMPLATE/             # Issue模板
│
├── CONTRIBUTING.md       # 贡献者指南
├── CODE_OF_CONDUCT.md    # 行为准则
└── README.md             # 本文件
```

## 开发说明

### 端口配置

| 服务 | 地址 |
|------|------|
| 前端开发服务器 | http://127.0.0.1:5173 |
| 后端 API | http://127.0.0.1:8001 |
| API 文档 | http://127.0.0.1:8001/docs |
| WebSocket | ws://127.0.0.1:8001/ws |
| n8n 工作流引擎 | http://127.0.0.1:5678 |
| n8n Webhook | http://127.0.0.1:5678/webhook/* |

### 数据存储

- **数据库**: `backend/database/auto_geo_v3.db`
- **Cookies**: `.cookies/` 目录
- **日志**: `logs/` 目录

### Git分支情况

当前项目有以下远程分支：

| 分支名称 | 说明 | 状态 |
|---------|------|------|
| `master` | 主分支（生产环境） | ✅ 默认分支 |
| `RAGflow作为知识库接入GEO` | RAGflow知识库集成功能 | ⚠️ 待合并 |
| `关键词蒸馏` | 关键词蒸馏功能 | ⚠️ 待合并 |
| `批量账号管理` | 批量账号管理功能 | ⚠️ 待合并 |
| `收录查询` | 收录查询功能 | ⚠️ 待合并 |
| `数据报表` | 数据报表功能 | ⚠️ 待合并 |
| `用户管理` | 用户管理功能 | ⚠️ 待合并 |

## 团队协作规范

> 📖 参与项目开发前，请先阅读以下规范文档，这会让我们的协作更高效！

### 核心文档

| 文档 | 说明 | 链接 |
|------|------|------|
| 📖 **贡献指南** | 如何参与项目开发、提交代码、创建PR | [CONTRIBUTING.md](./CONTRIBUTING.md) |
| 🤝 **行为准则** | 社区行为规范，营造友好的开发环境 | [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) |
| 📋 **协作规范** | 分支管理、提交规范、PR流程等详细规范 | [团队协作指南](./docs/TEAM_COLLABORATION_GUIDE.md) |

### 快速链接

- [🐛 报告Bug](https://github.com/Architecture-Matrix/auto_geo/issues/new?template=bug_report.md)
- [✨ 提交功能建议](https://github.com/Architecture-Matrix/auto_geo/issues/new?template=feature_request.md)
- [💡 技术改进建议](https://github.com/Architecture-Matrix/auto_geo/issues/new?template=improvement.md)
- [📖 报告文档问题](https://github.com/Architecture-Matrix/auto_geo/issues/new?template=documentation.md)

### 开发流程概览

```bash
# 1. Fork并克隆项目
git clone https://github.com/你的用户名/auto_geo.git

# 2. 创建功能分支
git checkout -b feature/your-feature-name

# 3. 开发并提交
git add .
git commit -m "feat: 添加功能描述"

# 4. 推送并创建PR
git push origin feature/your-feature-name
# 然后在GitHub上创建Pull Request

# 5. 等待Code Review，根据意见修改
# 6. 合并后删除分支
```

### 提交规范

```bash
# 提交格式: <type>(<scope>): <subject>

type类型:
- feat: 新功能
- fix: Bug修复
- docs: 文档更新
- style: 代码格式调整
- refactor: 重构
- perf: 性能优化
- test: 测试相关
- chore: 构建/工具相关

# 示例
git commit -m "feat: 添加关键词蒸馏API端点"
git commit -m "fix: 修复知乎发布失败问题"
```

---

## 常见问题

### Q: 前端启动后提示无法连接后端？

A: 需要先启动后端服务。开两个终端，分别运行：
- 终端1: `cd backend && python main.py`
- 终端2: `cd fronted && npm run dev`

### Q: n8n webhook 调用失败？

A: 检查以下几点：
1. n8n 是否正常运行：访问 http://localhost:5678
2. workflow 是否已激活：在 n8n 界面点击 "Save and activate workflow"
3. DeepSeek API 凭证是否配置正确

### Q: Windows下构建内存不足？

A: 这是大项目构建的常见问题，使用开发模式即可：`npm run dev`

### Q: 如何启动定时任务？

A: 后端启动后调用 `POST /api/scheduler/start` 即可启动定时检测

### Q: 如何更换 AI 服务商？

A: 只需在 n8n 中修改 AI 节点的凭证配置，无需修改业务代码！

## 更新日志

### v2.8.0 (2026-02-03)
- ✅ **简化依赖管理**：删除多余的 `requirements-dev.txt`，只保留一个 `requirements.txt`
- ✅ **移除冗余文档**：删除 `backend/DEPENDENCIES.md`，简化项目结构
- ✅ **精简依赖说明**：更新 README，只保留开发环境需要的依赖

### v2.7.0 (2026-02-03)
- ✅ **集成清理功能**：将清理工具集成到 `quickstart.bat` 主菜单
- ✅ **统一管理界面**：一个脚本搞定启动、重启、清理所有操作
- ✅ **清理子菜单**：快速清理/完全清理可选，返回主菜单更方便
- ✅ **版本同步**：`quickstart.bat` 和 `quickstart.cmd` 保持同步

### v2.4.0 (2026-02-03)
- ✅ **后端依赖大清理**：移除 torch 等冗余包，节省 ~5GB 空间
- ✅ **快速启动工具**：优化 `quickstart.bat`，增加依赖检查和窗口管理
- ✅ **项目清理工具**：新增 `cleanup.bat`，一键清理缓存和临时文件

### v2.3.0 (2026-02-03)
- ✅ 创建完整的GitHub团队开发规范
- ✅ 更新所有项目文档的负责人信息
- ✅ 建立Issue和PR模板系统
- ✅ 创建项目信息记录文档
- ✅ 更新n8n工作流（GEOv0.0.2）

### v2.2.0 (2025-01-26)
- ✅ 更换富文本编辑器：ByteMD → WangEditor 5
- ✅ WangEditor 支持所见即所得编辑
- ✅ 完善图片上传功能，支持拖拽上传
- ✅ 代码高亮支持 17 种编程语言
- ✅ 深色模式样式优化
- ✅ 创建前端技术文档 `fronted/FRONTEND.md`

### v2.1.0 (2025-01-22)
- ✅ 新增 n8n AI 中台架构
- ✅ AI 能力与业务代码解耦
- ✅ 创建 n8n 工作流（关键词蒸馏、文章生成、收录分析）
- ✅ 后端新增 n8n_service.py 封装
- ✅ 换 AI 服务商只需改 n8n 配置，不动代码

### v2.0.0 (2025-01-17)
- ✅ 完成预警通知系统
- ✅ 完成定时任务系统(集成预警检查)
- ✅ 完成数据统计报表
- ✅ 完成GEO文章生成
- ✅ 完成收录检测功能
- ✅ 前后端对接测试通过
- ✅ 所有API正常工作

### v1.0.0 (2025-01-13)
- ✅ 基础多平台发布功能
- ✅ 账号管理与授权
- ✅ 文章编辑与发布

## 许可证

MIT License

---

**维护者**: 小a
**更新日期**: 2026-02-03
**版本**: v2.8.0 (简化依赖管理 - 删除冗余文件)
