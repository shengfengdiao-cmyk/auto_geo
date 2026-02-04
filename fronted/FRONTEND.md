# AutoGeo 前端文档

> **Electron + Vue3 + TypeScript + Element Plus + WangEditor**

---

## 目录

1. [技术栈](#技术栈)
2. [项目结构](#项目结构)
3. [组件说明](#组件说明)
4. [状态管理](#状态管理)
5. [富文本编辑器](#富文本编辑器)
6. [开发指南](#开发指南)
7. [构建部署](#构建部署)

---

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4+ | 渐进式框架 |
| TypeScript | 5.0+ | 类型安全 |
| Vite | 5.4+ | 构建工具 |
| Element Plus | 最新 | UI 组件库 |
| Pinia | 最新 | 状态管理 |
| Vue Router | 4.x | 路由管理 |
| WangEditor | 5.x | 富文本编辑器 |
| ECharts | 5.x | 数据可视化 |
| Axios | 最新 | HTTP 请求 |
| Electron | 最新 | 桌面应用 |

---

## 项目结构

```
fronted/
├── electron/              # Electron 主进程
│   ├── main.ts           # 主进程入口
│   └── preload.ts        # 预加载脚本
├── src/
│   ├── assets/           # 静态资源
│   ├── components/       # 组件
│   │   ├── business/     # 业务组件
│   │   │   └── editor/   # 富文本编辑器
│   │   │       └── WangEditor.vue
│   │   └── common/       # 通用组件
│   ├── views/            # 页面视图
│   │   ├── layout/       # 布局页面
│   │   ├── dashboard/    # 概览页
│   │   ├── account/      # 账号管理
│   │   ├── article/      # 文章管理
│   │   ├── publish/      # 发布管理
│   │   ├── geo/          # GEO系统
│   │   ├── candidate/    # 候选人管理
│   │   ├── knowledge/    # 知识库管理
│   │   └── scheduler/    # 定时任务
│   ├── stores/           # Pinia 状态管理
│   │   └── modules/      # Store 模块
│   ├── router/           # 路由配置
│   ├── api/              # API 封装
│   └── styles/           # 全局样式
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

## 组件说明

### 业务组件

#### WangEditor.vue
富文本编辑器组件，基于 WangEditor 5。

**Props:**
```typescript
{
  modelValue: string    // 编辑器内容（HTML）
  height?: string       // 编辑器高度，默认 '500px'
  readonly?: boolean    // 是否只读
}
```

**Events:**
```typescript
@update:modelValue  // 内容更新
@change            // 内容变化
```

**功能特性:**
- 所见即所得编辑
- 图片上传（调用 `/api/upload/image`）
- 代码块高亮（支持 17 种语言）
- 表格插入/编辑
- 全屏模式
- 深色模式适配

**使用示例:**
```vue
<WangEditor
  v-model="article.content"
  height="100%"
  @change="handleContentChange"
/>
```

---

## 状态管理

### Pinia Stores

#### article.ts
文章管理状态，包含文章列表、创建、更新、删除等操作。

#### candidate.ts
候选人管理状态，与 n8n AI 招聘工作流集成。

#### platform.ts
平台管理状态，支持的平台列表和状态。

#### auth.ts
账号授权状态，管理登录授权流程。

---

## 富文本编辑器

### WangEditor 5 集成

**安装依赖:**
```bash
npm install @wangeditor/editor @wangeditor/editor-for-vue@next
```

**工具栏配置:**
- 标题选择（H1-H6）
- 文字格式（加粗/斜体/下划线/删除线）
- 字体/字号/行高/颜色
- 列表（无序/有序/待办）
- 对齐方式
- 链接插入
- 图片上传
- 代码块
- 表情
- 撤销/重做
- 全屏模式

**图片上传配置:**
- 自动调用后端 `/api/upload/image` 接口
- 支持拖拽上传
- 最大 5MB
- 支持 jpg/png/gif/webp 格式

---

## 开发指南

### 启动开发服务器

```bash
cd fronted
npm run dev
```

开发服务器运行在 `http://127.0.0.1:5173`

### 路由配置

路由定义在 `src/router/index.ts`：

```typescript
{
  path: 'articles/edit/:id',
  name: 'ArticleEdit',
  component: () => import('@/views/article/ArticleEdit.vue'),
  meta: { title: '编辑文章', hidden: true }
}
```

### API 调用示例

```typescript
// 使用原生 fetch
const response = await fetch('/api/articles')
const data = await response.json()

// 使用 axios
import axios from 'axios'
const { data } = await axios.get('/api/articles')
```

### 添加新页面

1. 在 `src/views/` 下创建页面组件
2. 在 `src/router/index.ts` 添加路由
3. 在 `src/views/layout/MainLayout.vue` 添加侧边栏菜单（如需要）

---

## 构建部署

### 开发模式构建
```bash
npm run build:renderer
```

### 完整构建（包含 Electron）
```bash
npm run build
```

### 打包 Electron 应用
```bash
npm run build:electron
npm run dist
```

构建产物位于 `out/` 目录。

---

## 样式规范

### CSS 变量
```scss
--el-bg-color           // 背景色
--el-text-color-primary // 主文字颜色
--el-border-color       // 边框颜色
--el-color-primary      // 主题色
```

### 命名规范
- 组件文件：PascalCase（如 `WangEditor.vue`）
- 页面文件：PascalCase + Page 后缀（如 `ArticleEdit.vue`）
- Store 文件：camelCase（如 `article.ts`）

---

## 更新日志

### v2.2.0 (2025-01-26)
- ✅ 替换富文本编辑器：ByteMD → WangEditor 5
- ✅ WangEditor 支持所见即所得编辑
- ✅ 图片上传功能完善
- ✅ 代码高亮支持 17 种语言
- ✅ 深色模式样式优化

### v2.1.0 (2025-01-22)
- ✅ 新增候选人管理页面
- ✅ 新增知识库管理页面
- ✅ 新增定时任务管理页面
- ✅ n8n AI 中台集成

---

**维护者**: 小a
**更新日期**: 2025-01-26
