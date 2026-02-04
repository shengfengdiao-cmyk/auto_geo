# AutoGeo 项目信息记录

> 本文件记录AutoGeo项目的核心信息，用于全局记忆和团队成员快速了解项目概况

## 📋 项目基本信息

- **项目名称**: AutoGeo AI搜索引擎优化自动化平台
- **GitHub仓库**: https://github.com/Architecture-Matrix/auto_geo
- **项目负责人**: 小a
- **项目类型**: 桌面应用 + Web服务
- **创建日期**: 2025-01-13
- **当前版本**: v2.3.0

---

## 🎯 项目简介

AutoGeo是一个基于Electron + Vue3 + FastAPI + n8n + Playwright的智能平台，主要功能包括：

1. **多平台发布**: 支持知乎、百家号、搜狐、头条号
2. **账号管理**: 安全的Cookie存储和授权
3. **文章编辑**: WangEditor 5富文本编辑器
4. **GEO优化**: 关键词管理、收录检测、GEO文章生成
5. **数据报表**: 收录趋势、平台分布、关键词排名
6. **预警通知**: 命中率下降、零收录、持续低迷预警
7. **候选人管理**: HR候选人信息管理与跟踪
8. **知识库管理**: RAGflow知识库接入与管理
9. **定时任务调度**: 可视化定时任务配置与管理
10. **数据仪表盘**: 实时数据概览与可视化分析

---

## 🛠️ 技术栈

| 层级 | 技术选型 | 版本 |
|------|---------|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia | - |
| 后端 | FastAPI + SQLAlchemy + Playwright + APScheduler | - |
| AI中台 | n8n 工作流引擎 | latest |
| 桌面 | Electron | - |
| 数据库 | SQLite | - |
| AI服务 | DeepSeek API | - |

---

## 👥 团队信息

### 项目负责人
- **姓名**: 小a
- **GitHub**: @Architecture-Matrix
- **联系方式**: 通过GitHub Issues联系

### 团队规范文档
- [团队协作指南](./TEAM_COLLABORATION_GUIDE.md) - 完整的开发规范
- [贡献者指南](../CONTRIBUTING.md) - 新人快速上手
- [行为准则](../CODE_OF_CONDUCT.md) - 社区行为规范

---

## 📂 项目结构

```
auto_geo/
├── backend/              # 后端服务 (FastAPI)
│   ├── api/              # API 路由
│   ├── database/         # 数据库
│   ├── services/         # 业务服务
│   └── scripts/          # 测试脚本
├── fronted/              # 前端应用 (Electron + Vue3)
│   ├── electron/         # Electron 主进程
│   └── src/              # Vue 源码
├── n8n/                  # n8n AI工作流
│   └── workflows/        # 工作流JSON文件
├── docs/                 # 项目文档
│   ├── TEAM_COLLABORATION_GUIDE.md  # 团队协作规范
│   ├── architecture/     # 架构文档
│   ├── features/         # 功能设计文档
│   ├── testing/          # 测试文档
│   └── PROJECT_INFO.md   # 本文件
├── .github/              # GitHub配置
│   ├── pull_request_template.md     # PR模板
│   └── ISSUE_TEMPLATE/   # Issue模板
├── CONTRIBUTING.md       # 贡献者指南
├── CODE_OF_CONDUCT.md    # 行为准则
└── README.md             # 项目说明
```

---

## 🔑 重要约定

### 分支命名规范
- `feature/功能名称-简短描述` - 功能开发
- `fix/问题描述-简短描述` - Bug修复
- `hotfix/紧急问题描述` - 紧急修复
- `refactor/模块名称-重构内容` - 重构

### 提交规范
```
<type>(<scope>): <subject>

type类型:
- feat: 新功能
- fix: Bug修复
- docs: 文档更新
- style: 代码格式调整
- refactor: 重构
- perf: 性能优化
- test: 测试相关
- chore: 构建/工具相关
```

### 核心原则
1. **KISS原则**: 保持简单，拒绝过度设计
2. **DRY原则**: 避免重复代码
3. **SOLID原则**: 遵循面向对象设计原则
4. **YAGNI原则**: 只实现当前需要的功能

---

## 🌿 Git分支情况

### 当前分支状态

| 分支名称 | 类型 | 说明 | 状态 |
|---------|------|------|------|
| `master` | 主分支 | 生产环境代码 | ✅ 默认分支 |
| `RAGflow作为知识库接入GEO` | 功能分支 | RAGflow知识库集成功能 | ⚠️ 待合并 |
| `关键词蒸馏` | 功能分支 | 关键词蒸馏功能 | ⚠️ 待合并 |
| `批量账号管理` | 功能分支 | 批量账号管理功能 | ⚠️ 待合并 |
| `收录查询` | 功能分支 | 收录查询功能 | ⚠️ 待合并 |
| `数据报表` | 功能分支 | 数据报表功能 | ⚠️ 待合并 |
| `用户管理` | 功能分支 | 用户管理功能 | ⚠️ 待合并 |

### 分支管理建议

1. **待合并分支**: 上述6个功能分支已开发完成，建议尽快合并到主分支
2. **合并顺序建议**:
   - 先合并 `关键词蒸馏`（基础功能）
   - 再合并 `收录查询`（依赖关键词蒸馏）
   - 然后合并 `数据报表`（依赖收录查询）
   - 接着合并 `RAGflow作为知识库接入GEO`（独立功能）
   - 最后合并 `批量账号管理` 和 `用户管理`（管理功能）

3. **合并后清理**: 合并完成后删除远程分支，保持分支列表简洁

---

## 📅 重要日期

- **2025-01-13**: v1.0.0发布（基础多平台发布功能）
- **2025-01-17**: v2.0.0发布（完成预警通知、定时任务、数据报表）
- **2025-01-22**: v2.1.0发布（新增n8n AI中台架构）
- **2025-01-26**: v2.2.0发布（更换WangEditor 5编辑器）
- **2026-02-03**: v2.3.0发布（创建GitHub团队开发规范）

### 最近提交记录

```
114e19b Merge pull request #1 from shengfengdiao-cmyk/feature/dashboard-monitor
b5b7835 chore: 同步最新依赖和配置文件
ee82924 feat: 彻底打通今日头条全流程发布(标题/正文/图片/封面)，完成V2.0代码合并
d97ef67 merge: 完成上游收录监控功能合并，保留本地知乎/头条发布优化
6278da1 fix: 最终修复知乎发布逻辑 v4.1
7f0ab68 feat: AutoGeo V2.0 完整核心链路 - AI生成+多平台发布+收录监控
```

---

## 📝 更新日志

### 2026-02-03 (v2.3.0)
- ✅ 创建完整的GitHub团队开发规范
- ✅ 更新所有项目文档的负责人信息为"小a"
- ✅ 建立Issue和PR模板系统（4种Issue模板 + 1种PR模板）
- ✅ 创建项目信息记录文档（PROJECT_INFO.md）
- ✅ 更新n8n工作流（GEOv0.0.2.json）
- ✅ 更新README.md以反映当前项目状态（添加新功能、完整API列表、git分支情况）

### 待办事项
- ⚠️ 合并6个待合并的功能分支到主分支
- ⚠️ 清理已合并的分支
- ⚠️ 更CHANGELOG.md记录详细变更

---

**最后更新**: 2026-02-03
**维护者**: 小a
**文档版本**: v1.1
