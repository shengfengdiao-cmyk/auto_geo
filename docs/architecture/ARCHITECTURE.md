# AutoGeo 架构设计文档

> 老王备注：这个文档专门讲清楚 Vite、Electron 和 Python 后端的关系！别tm搞混了！

---

## 一、整体架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AutoGeo 应用架构                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────┐         ┌──────────────────────┐             │
│  │   Electron 主进程    │         │    Python 后端       │             │
│  │  (Node.js 运行时)    │◄───────►│   (FastAPI 服务)     │             │
│  │                      │  spawn  │                      │             │
│  │  - 窗口管理          │         │  - 账号管理 API      │             │
│  │  - IPC 通信          │         │  - 文章管理 API      │             │
│  │  - 后端进程管理      │         │  - 发布管理 API      │             │
│  │  - 系统托盘          │         │  - Playwright 自动化 │             │
│  └──────────┬───────────┘         └──────────┬───────────┘             │
│             │                                │                          │
│             │ IPC                            │ HTTP/WebSocket          │
│             │                                │                          │
│  ┌──────────▼───────────┐         ┌──────────▼───────────┐             │
│  │   Preload 脚本       │         │                      │             │
│  │  (安全隔离层)        │         │   http://127.0.0.1   │             │
│  │                      │         │      :8001           │             │
│  │  contextBridge       │         │                      │             │
│  └──────────┬───────────┘         └──────────────────────┘             │
│             │                                                          │
│             │ contextBridge API                                        │
│             │                                                          │
│  ┌──────────▼─────────────────────────────────────────────────────┐    │
│  │                    渲染进程 (Renderer Process)                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐  │    │
│  │  │                        Vite Dev Server                   │  │    │
│  │  │  (开发环境: http://127.0.0.1:5173)                       │  │    │
│  │  │                                                          │  │    │
│  │  │  ┌────────────────────────────────────────────────────┐ │  │    │
│  │  │  │              Vue 3 应用                            │ │  │    │
│  │  │  │                                                    │ │  │    │
│  │  │  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │ │  │    │
│  │  │  │  │  Vue 组件 │  │ Pinia    │  │   API 服务       │ │ │  │    │
│  │  │  │  │  (Views)  │  │ Stores   │  │  (axios)         │ │ │  │    │
│  │  │  │  └──────────┘  └──────────┘  └──────────────────┘ │ │  │    │
│  │  │  │                                                    │ │  │    │
│  │  │  │  ┌──────────────────────────────────────────────┐ │ │  │    │
│  │  │  │  │         WebSocket 服务                       │ │ │  │    │
│  │  │  │  └──────────────────────────────────────────────┘ │ │  │    │
│  │  │  └────────────────────────────────────────────────────┘ │  │    │
│  │  └──────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 二、Vite 与 Electron 的关系

### 2.1 开发环境

```
用户双击 启动应用.bat
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Electron 主进程启动                                      │
│     - 启动 Python 后端 (spawn)                               │
│     - 创建主窗口                                              │
│     - 加载 Vite 开发服务器地址                               │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Vite 开发服务器                                          │
│     - 运行在 http://127.0.0.1:5173                          │
│     - HMR 热更新（开发超爽）                                 │
│     - 代理 /api 到 Python 后端                              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Electron 窗口加载                                        │
│     - mainWindow.loadURL('http://127.0.0.1:5173')          │
│     - Preload 脚本注入                                       │
│     - Vue 应用在渲染进程中运行                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 生产环境（打包后）

```
┌─────────────────────────────────────────────────────────────┐
│  npm run build                                              │
│     │                                                        │
│     ├─► build:renderer  (Vite 构建 Vue 代码)               │
│     │      输出: out/renderer/                              │
│     │                                                        │
│     └─► build:electron    (TypeScript 编译主进程)          │
│            输出: out/electron/                              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  electron-builder 打包                                       │
│     - 将前端静态文件打包进 asar                              │
│     - 主进程加载 file:// 协议的 HTML                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 关键配置

**vite.config.ts** (`fronted/vite.config.ts`):
```typescript
server: {
  host: '127.0.0.1',        // 必须用 IPv4，Electron 才能连上
  port: 5173,
  strictPort: true,         // 端口被占用时报错，不跳
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8001',  // 代理到 Python 后端
      changeOrigin: true,
    },
    '/ws': {
      target: 'ws://127.0.0.1:8001',    // WebSocket 代理
      ws: true,
    },
  },
}
```

**window-manager.ts** (`fronted/electron/main/window-manager.ts`):
```typescript
const isDev = process.env.NODE_ENV === 'development'
const URL = isDev
  ? 'http://127.0.0.1:5173'      // 开发: Vite 服务器
  : formatFileUrl('index.html')  // 生产: 打包后的文件
```

---

## 三、通信通道详解

### 3.1 通道 1：Vue 渲染进程 ↔ Python 后端 (HTTP/WebSocket)

```
┌──────────────────────┐          ┌──────────────────────┐
│   Vue 渲染进程       │          │    Python 后端       │
│                      │          │   (FastAPI)          │
│  ┌────────────────┐  │          │                      │
│  │  API Service   │  │          │  ┌────────────────┐  │
│  │  (axios)       │◄─┼──────────┼─►│   /api/*       │  │
│  └────────────────┘  │   HTTP   │  └────────────────┘  │
│                      │          │                      │
│  ┌────────────────┐  │          │  ┌────────────────┐  │
│  │  WebSocket     │◄─┼──────────┼─►│   /ws          │  │
│  │  Service       │  │   WS     │  └────────────────┘  │
│  └────────────────┘  │          │                      │
└──────────────────────┘          └──────────────────────┘

实际路径（开发环境）：
  Vue: http://127.0.0.1:5173
    │
    │ Vite Proxy 代理
    ▼
  Python: http://127.0.0.1:8001
```

**API 调用示例**：
```typescript
// fronted/src/services/api/index.ts
export const accountApi = {
  getList: () => get('/accounts'),           // → http://127.0.0.1:8001/api/accounts
  create: (data) => post('/accounts', data), // → POST /api/accounts
}
```

**WebSocket 连接**：
```typescript
// 连接到 ws://127.0.0.1:5173/ws (Vite 代理到 Python)
wsService.connect('ws://127.0.0.1:5173/ws')
```

### 3.2 通道 2：渲染进程 ↔ Electron 主进程 (IPC)

```
┌──────────────────────┐          ┌──────────────────────┐
│   Vue 渲染进程       │          │  Electron 主进程     │
│                      │          │                      │
│  ┌────────────────┐  │          │  ┌────────────────┐  │
│  │  electronAPI   │◄─┼──────────┼─►│  ipcMain       │  │
│  │  (暴露的API)   │  │  IPC     │  │  handlers       │  │
│  └────────────────┘  │          │  └────────────────┘  │
│       ▲              │          │                      │
│       │ contextBridge│          │                      │
│  ┌────┴─────────────┤          │                      │
│  │ Preload 脚本     │          │                      │
│  └──────────────────┘          └──────────────────────┘

可用的 IPC 通道（白名单）：
  - window:minimize/maximize/close
  - dialog:open-file/save-file
  - auth:start
  - backend:get-status/restart
  - shell:open-external
```

**使用示例**：
```typescript
// Vue 组件中
window.electronAPI.minimizeWindow()  // 调用主进程 API
window.electronAPI.onAuthWindowClosed((data) => {
  // 监听主进程消息
})
```

### 3.3 通道 3：Electron 主进程 ↔ Python 后端 (进程管理)

```
┌──────────────────────┐          ┌──────────────────────┐
│  Electron 主进程     │          │    Python 后端       │
│                      │          │                      │
│  ┌────────────────┐  │          │  ┌────────────────┐  │
│  │ BackendManager │◄─┼──────────┼─►│  FastAPI       │  │
│  │                │  │  spawn   │  │  Uvicorn       │  │
│  └────────────────┘  │          │  └────────────────┘  │
│         │            │          │         │              │
│         │ health     │  HTTP    │         │              │
│         └───────────►│ check    │◄────────┘              │
└──────────────────────┘          └──────────────────────┘

后端管理器职责：
  - 启动: spawn('python', ['main.py'])
  - 健康检查: GET http://127.0.0.1:8001/api/health
  - 停止: taskkill /F /T /PID xxx (Windows)
  - 重启: stop() → start()
```

---

## 四、通信流程示例

### 4.1 用户点击"添加账号"按钮

```
1. 用户点击按钮
   └─► Vue 组件 @click 事件

2. 调用 API 服务
   accountApi.create({ platform: 'zhihu', account_name: '测试' })
   └─► axios.post('/api/accounts', data)
       └─► http://127.0.0.1:5173/api/accounts (Vite)
           └─► http://127.0.0.1:8001/api/accounts (Python 后端)

3. Python 后端处理
   └─► account.py router 处理请求
       └─► SQLAlchemy 写入数据库
           └─► 返回 JSON 响应

4. Vue 更新状态
   └─► accountStore 刷新列表
       └─► Pinia 触发响应式更新
           └─► 页面显示新账号
```

### 4.2 用户点击"开始授权"按钮

```
1. Vue 调用后端 API 开始授权
   accountApi.startAuth({ platform: 'zhihu' })
   └─► Python 返回 auth_url

2. Vue 调用 Electron IPC 打开授权窗口
   window.electronAPI.startAuth('zhihu', auth_url)
   └─► 主进程创建新的 BrowserWindow
       └─► 加载平台登录页面

3. 用户在授权窗口登录
   └─► 手动点击"我已完成登录"

4. Vue 确认授权
   accountApi.saveAuth(taskId)
   └─► Python 获取 Cookies 并加密保存
```

### 4.3 批量发布文章（实时进度）

```
1. Vue 创建发布任务
   publishApi.createTask({ article_ids: [1], account_ids: [1] })

2. 后端开始发布，同时建立 WebSocket 连接
   └─► wsService.connect('ws://127.0.0.1:5173/ws')

3. Python 后端推送进度
   WebSocket.send({ type: 'publish:progress', data: { ... } })

4. Vue 实时更新 UI
   on('publish:progress', (data) => {
     progress.value = data.progress
   })
```

---

## 五、关键端口一览

| 服务 | 地址 | 说明 |
|------|------|------|
| **Vite Dev Server** | http://127.0.0.1:5173 | 前端开发服务器（仅开发环境） |
| **Python FastAPI** | http://127.0.0.1:8001 | 后端 API 服务 |
| **WebSocket** | ws://127.0.0.1:8001/ws | 实时通信（开发时通过 Vite 代理） |

---

## 六、文件路径速查

### Electron 主进程
- 入口：`fronted/electron/main/index.ts`
- 窗口管理：`fronted/electron/main/window-manager.ts`
- IPC 处理：`fronted/electron/main/ipc-handlers.ts`
- 后端管理：`fronted/electron/main/backend-manager.ts`
- Preload：`fronted/electron/preload/index.ts`

### Vue 渲染进程
- 入口：`fronted/src/main.ts`
- API 服务：`fronted/src/services/api/index.ts`
- WebSocket：`fronted/src/services/websocket/index.ts`
- 状态管理：`fronted/src/stores/modules/`

### Python 后端
- 入口：`backend/main.py`
- 路由：`backend/api/`
- 服务：`backend/services/`

---

## 七、安全机制

### 1. contextBridge 隔离
Preload 脚本使用 `contextBridge.exposeInMainWorld` 安全暴露 API，渲染进程无法直接访问 Node.js API。

### 2. IPC 白名单
所有 IPC 通道都经过白名单验证，未注册的通道会被拒绝。

### 3. 发送者验证
```typescript
function validateSender(frame: any): boolean {
  const allowedProtocols = ['http:', 'https:', 'file:']
  return allowedProtocols.includes(url.protocol)
}
```

### 4. AES-256 加密
Cookies 使用 AES-256 加密存储在本地数据库。

---

**文档更新时间：** 2025-01-10
**维护者：** 老王
