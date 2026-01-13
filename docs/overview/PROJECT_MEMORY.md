# 项目记忆

## 项目概述

**项目名称：** auto_geo - 智能多平台文章发布助手

**项目描述：** 一个自动化文章发布助手，帮助用户在多个自媒体平台上自动发布文章内容

**当前状态：** 🚀 框架搭建完成，进入实测阶段！

**完成度：** 后端 75% | 前端 80%

---

## 技术架构

> 📘 **详细架构文档：** [`.claude/docs/ARCHITECTURE.md`](.claude/docs/ARCHITECTURE.md)
>
> 老王备注：里面有完整的 Vite + Electron + Python 通信关系说明！

### 整体架构
```
┌─────────────────────────────────────────┐
│          前端 (Electron + Vue 3)          │
│     账号管理 | 文章编辑 | 批量发布        │
├─────────────────────────────────────────┤
│         IPC / HTTP / WebSocket           │
├─────────────────────────────────────────┤
│          后端 (Python + FastAPI)         │
│    Playwright 自动化发布                 │
└─────────────────────────────────────────┘
```

### 通信通道
| 通道 | 涉及方 | 协议 | 用途 |
|-----|-------|------|------|
| **通道 1** | Vue ↔ Python 后端 | HTTP/WebSocket | API 调用、实时进度 |
| **通道 2** | Vue ↔ Electron 主进程 | IPC | 窗口控制、文件对话框、授权窗口 |
| **通道 3** | Electron ↔ Python | spawn + HTTP | 进程管理、健康检查 |

### 技术栈
| 层级 | 技术 | 说明 |
|-----|------|------|
| 前端框架 | Electron 28 + Vue 3 + TypeScript | 桌面应用 |
| 构建工具 | Vite | 快速开发 |
| 状态管理 | Pinia | Vue 官方推荐 |
| UI组件 | Element Plus | 中后台组件库 |
| 后端框架 | FastAPI | 异步高性能 |
| 自动化 | Playwright | 浏览器自动化 |
| 数据库 | SQLite | 本地存储 |
| 加密 | AES-256 | 安全存储 |

### 支持的平台
- ✅ 知乎 (zhihu.com) - #0084FF
- ✅ 百家号 (baijiahao.baidu.com) - #E53935
- ✅ 搜狐号 (mp.sohu.com) - #FF6B00
- ✅ 头条号 (mp.toutiao.com) - #333333
- 🔄 公众号 (mp.weixin.qq.com) - 待实现

---

## 核心功能

### 1. 账号管理 ✅
- [x] 添加账号（平台、账号名称、备注）
- [x] 手动授权登录（打开浏览器让用户登录）
- [x] Cookies 加密存储
- [x] 账号状态检测
- [x] 账号 CRUD 操作

### 2. 文章管理 ✅
- [x] 创建/编辑文章
- [x] 文章列表（搜索、筛选、分页）
- [x] 草稿保存
- [x] 文章状态管理

### 3. 批量发布 ✅
- [x] 选择文章和目标账号
- [x] 四步发布流程（选择文章→选择账号→确认→进度）
- [x] 自动化发布适配器
- [x] 实时进度反馈（WebSocket）
- [x] 发布记录查询

---

## 目录结构

```
auto_geo/
├── backend/               # Python 后端服务 ✅
│   ├── api/              # API 路由
│   │   ├── account.py    # 账号管理 API ✅
│   │   ├── article.py    # 文章管理 API ✅
│   │   └── publish.py    # 发布管理 API ✅
│   ├── services/         # 业务逻辑
│   │   ├── crypto.py     # AES-256 加密服务 ✅
│   │   ├── playwright_mgr.py  # Playwright 管理器 ✅
│   │   └── publisher.py  # 自动发布服务 ✅
│   ├── database/         # 数据库
│   │   ├── models.py     # ORM 模型 ✅
│   │   └── __init__.py   # 数据库连接 ✅
│   ├── schemas/          # Pydantic 模型 ✅
│   ├── config.py         # 配置文件 ✅
│   └── main.py           # FastAPI 入口 ✅
│
├── fronted/              # Electron 前端 ✅
│   ├── electron/         # Electron 主进程
│   │   ├── main/         # 主进程代码
│   │   │   ├── index.ts        # 主入口 ✅
│   │   │   ├── window-manager.ts   # 窗口管理 ✅
│   │   │   ├── ipc-handlers.ts     # IPC 处理器 ✅
│   │   │   └── tray-manager.ts     # 托盘管理 ✅
│   │   ├── preload/       # 预加载脚本
│   │   │   └── index.ts  # API 暴露 ✅
│   │   └── tsconfig.json
│   ├── src/              # Vue 渲染进程
│   │   ├── main.ts       # 应用入口 ✅
│   │   ├── App.vue       # 根组件 ✅
│   │   ├── core/         # 核心层
│   │   │   ├── config/   # 平台配置 ✅
│   │   │   └── platform/ # 平台适配器 ✅
│   │   ├── stores/       # Pinia 状态管理 ✅
│   │   │   ├── account.ts
│   │   │   ├── article.ts
│   │   │   └── platform.ts
│   │   ├── router/       # 路由配置 ✅
│   │   ├── views/        # 页面组件 ✅
│   │   │   ├── layout/   # 主布局
│   │   │   ├── dashboard/# 概览页
│   │   │   ├── account/  # 账号管理
│   │   │   ├── article/  # 文章管理
│   │   │   ├── publish/  # 批量发布
│   │   │   └── settings/ # 设置
│   │   └── assets/       # 资源文件
│   ├── index.html        # HTML 入口 ✅
│   ├── package.json      # 前端依赖 ✅
│   ├── vite.config.ts    # Vite 配置 ✅
│   └── tsconfig.json     # TS 配置 ✅
│
├── .cookies/             # Cookie 存储目录
├── .claude/              # Claude 配置
│   ├── skills/           # Agent 技能定义
│   └── docs/             # 需求文档
│       ├── PRD-001-架构迁移至Playwright.md
│       ├── FRONTEND-ARCHITECTURE.md
│       └── UI-DESIGN.md
│
├── PROJECT_MEMORY.md     # 本文件 ✅
└── DEV_SUMMARY.md        # 开发总结 ✅
```

---

## 开发进度

### Phase 1: 后端基础架构 ✅
- [x] 搭建 FastAPI 项目结构
- [x] 数据库设计和初始化
- [x] 基础 API 接口定义

### Phase 2: 账号授权模块 ✅
- [x] Playwright 浏览器管理
- [x] 各平台登录页面处理
- [x] Cookies 提取和加密存储

### Phase 3: 文章发布模块 ✅
- [x] 知乎自动发布适配器
- [x] 百家号自动发布适配器
- [x] 搜狐号自动发布适配器
- [x] 头条号自动发布适配器
- [ ] 公众号自动发布适配器

### Phase 4: Electron 前端 ✅
- [x] Electron 项目搭建
- [x] 主进程和预加载脚本
- [x] Vue 3 页面组件
- [x] 与后端通信（HTTP + WebSocket）

### Phase 5: 测试与优化 🔄
- [ ] 各平台功能实测
- [ ] 选择器验证和调整
- [ ] 异常处理优化
- [ ] 应用打包

---

## API 接口

### 账号管理
| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/accounts` | 获取账号列表 |
| POST | `/api/accounts` | 创建账号 |
| PUT | `/api/accounts/{id}` | 更新账号 |
| DELETE | `/api/accounts/{id}` | 删除账号 |
| POST | `/api/accounts/auth/start` | 开始授权 |
| GET | `/api/accounts/auth/status/{task_id}` | 查询授权状态 |
| POST | `/api/accounts/auth/save/{task_id}` | 保存授权结果 |

### 文章管理
| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/articles` | 获取文章列表 |
| GET | `/api/articles/{id}` | 获取文章详情 |
| POST | `/api/articles` | 创建文章 |
| PUT | `/api/articles/{id}` | 更新文章 |
| DELETE | `/api/articles/{id}` | 删除文章 |

### 发布管理
| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/publish/create` | 创建发布任务 |
| GET | `/api/publish/progress/{task_id}` | 获取发布进度 |
| GET | `/api/publish/records` | 获取发布记录 |
| GET | `/api/publish/platforms` | 获取支持的平台 |

### WebSocket
| 路径 | 说明 |
|-----|------|
| `/ws` | 实时进度推送 |

---

## 平台适配器设计

### 开闭原则（OCP）
老王我用适配器模式实现了开闭原则！新增平台只需：

1. **添加平台配置** (`src/core/config/platform.ts`)
```typescript
export const PLATFORMS = {
  newplatform: {
    id: 'newplatform',
    name: '新平台',
    color: '#xxxxxx',
    // ...
  }
}
```

2. **实现发布适配器** (`services/publisher.py`)
```python
class NewPlatformPublisher(BasePlatformPublisher):
    async def publish(self, page, article, account):
        # 实现发布逻辑
        pass
```

3. **注册到发布器** (`PUBLISHERS`)
```python
PUBLISHERS['newplatform'] = NewPlatformPublisher()
```

**无需修改核心代码！**

---

## 启动方式

> **重要**：后端和前端需要**分别手动启动**，Electron 不再自动启动后端！

### 1️⃣ 启动后端（第一个终端）
```bash
cd E:\CodingPlace\AI\auto_geo\backend
python main.py
# 服务地址: http://127.0.0.1:8001
# API 文档: http://127.0.0.1:8001/docs
```

### 2️⃣ 启动前端（第二个终端）
```bash
cd E:\CodingPlace\AI\auto_geo\fronted
npm run dev
```

### 3️⃣ 退出顺序
1. 先 Ctrl+C 停止前端（Electron 会自动退出）
2. 再 Ctrl+C 停止后端

**⚠️ 注意**：如果后端启动报错 "端口已占用"，可能是残留进程，运行：
```powershell
# 查找占用 8001 端口的进程
netstat -ano | findstr ":8001"

# 杀掉所有 Python 进程（谨慎使用）
Stop-Process -Name python -Force
```

---

## 安全配置

> **重要**：Cookies 使用 AES-256 加密存储！详见 [SECURITY.md](SECURITY.md)

### 加密机制
- **算法**: AES-256 (Fernet)
- **密钥派生**: PBKDF2HMAC + SHA256
- **加密内容**: Cookies、localStorage

### 环境变量设置
```bash
# 1. 复制模板
cp .env.example .env

# 2. 生成密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. 编辑 .env 填入密钥
AUTO_GEO_ENCRYPTION_KEY=你的32字节密钥
```

---

## 更新记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2025-01-10 | v1.1.2 | 新增 `.env.example` 环境变量模板和 `SECURITY.md` 安全文档 |
| 2025-01-10 | v1.1.1 | 新增架构文档 `ARCHITECTURE.md`，详细说明 Vite/Electron/Python 通信关系 |
| 2025-01-08 | v2.0 | 框架搭建完成，前后端基本功能实现 |
| 2025-01-08 | v1.0 | 项目初始化 |

---

## 下一步计划

1. **实测验证** - 在各平台实测登录和发布流程
2. **选择器调整** - 根据实测结果调整页面选择器
3. **异常处理** - 完善各种异常情况的处理
4. **应用打包** - 使用 electron-builder 打包应用

---

**老王备注：** 项目框架完全按照架构设计文档搭建！
## 当前进度 @ 2025-01-09

### ✅ 已完成 (v1.1)
1. **后端框架** - FastAPI + SQLAlchemy + SQLite
2. **数据模型** - Account, Article, PublishRecord三张表
3. **加密服务** - AES-256 Cookies加密存储
4. **账号API** - 创建、查询、列表、详情接口
5. **文章API** - 创建、查询、列表接口
6. **基础测试** - 8个接口测试通过，通过率100%
7. **UI设计** - 暗色主题完整实现
8. **Playwright发布功能** - 完整的发布系统实现
9. **平台发布适配器** - 知乎、百家号、搜狐、头条四个平台
10. **发布API接口** - 创建任务、进度查询、记录查询、重试发布
11. **WebSocket实时进度** - 发布进度实时推送
12. **集成测试** - 所有模块导入测试通过
13. **API验证测试** - 发布接口验证通过
14. **前后端API联调** - 所有接口匹配验证通过
15. **retry接口** - 添加重试发布接口
16. **前端依赖安装** - 445个npm包安装成功
17. **前端开发服务器** - Vite服务器正常运行 (http://127.0.0.1:5173)
18. **前端样式修复** - 修复index.scss背景色和字体颜色
19. **article.ts语法修复** - 修复selectedArticleIds缺少const关键字
20. **前端页面测试** - 所有页面通过Playwright测试
21. **Playwright浏览器安装** - Chromium浏览器安装完成
22. **手动授权确认功能** - v1.1新增，用户点击按钮确认登录完成
23. **后端服务运行** - http://127.0.0.1:8000 正常运行
24. **前端服务运行** - http://127.0.0.1:5173 正常运行

### 🔄 v1.1 新功能 - 手动授权确认

**问题**：原有自动登录检测依赖平台选择器，平台改版容易失效

**解决方案**：
- 在浏览器页面中注入 "✓ 授权完成" 悬浮按钮
- 用户完成登录后手动点击按钮确认
- 支持验证码、二维码等各种复杂登录场景

**新增 API**：
- `POST /api/accounts/auth/confirm/{task_id}` - 手动确认授权

### 🐛 Bug修复记录 (2025-01-09)

| 文件 | 问题 | 修复 |
|-----|------|-----|
| `playwright_mgr.py` | 缺少 `import os` | 添加导入语句 |
| `account.py` | 更新账号分支缺少 `db.commit()` | 第315行添加提交 |
| `api/index.ts` | startAuth类型定义缺少account_name | 添加参数类型 |

### 📋 待实现
1. **后端实测**
   - 各平台发布适配器实测验证（需真实账号）
   - 图片上传功能
   - 发布失败重试逻辑优化

2. **前端优化**
   - 文章编辑器富文本功能
   - WebSocket 实时进度连接优化

3. **打包发布**
   - Electron 应用打包配置
   - 安装程序制作

