# Report Checker Pro 开发团队 — 使用指南

## 团队组成

| 角色 | 文件名 | 核心职责 | 负责阶段 |
|------|--------|----------|---------|
| 🏗️ 架构师 Lead | `architect-lead.md` | 任务拆解、代码审查、集成验证 | 全局统筹 |
| 🔧 后端工程师 | `backend-engineer.md` | 报告自检引擎 C01-C11 + API | Phase 4 |
| 🎨 前端工程师 | `frontend-engineer.md` | PTR 核对 + 报告自检页面 UI | Phase 3 + 5 |
| 🧪 测试工程师 | `test-engineer.md` | pytest + Playwright MCP + Golden File | 贯穿全程 |
| 📦 集成工程师 | `integration-engineer.md` | PDF 导出 + 端到端集成 + 交付 | Phase 6 |

## 快速开始

### 1. 启用 Agent Team

确保 Claude Code 已启用 Agent Team 实验功能：

```json
// settings.json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```

### 2. 启动团队

在 Claude Code 中输入：

```
请创建一个 Agent Team 来继续开发 Report Checker Pro 项目。

团队需要 5 个成员：
1. 架构师 Lead — 总协调，参考 .claude/agents/architect-lead.md
2. 后端工程师 — 负责 Phase 4（报告自检后端引擎），参考 .claude/agents/backend-engineer.md
3. 前端工程师 — 负责 Phase 3（PTR 核对前端页面），参考 .claude/agents/frontend-engineer.md
4. 测试工程师 — 负责持续测试验证，参考 .claude/agents/test-engineer.md
5. 集成工程师 — 待 Phase 3-5 完成后负责 Phase 6，参考 .claude/agents/integration-engineer.md

当前项目状态：Phase 0-2 已完成，从 Phase 3 开始。
首先让后端工程师和前端工程师并行开发 Phase 4 和 Phase 3。
```

## 并行开发协作流程

```
┌──────────────────────────────────────────────────────────┐
│                    架构师 Lead（总协调）                    │
│                   分配任务 + 审查 + 集成                   │
└─────────────┬──────────────┬──────────────┬──────────────┘
              │              │              │
    ┌─────────▼──────┐ ┌────▼─────────┐ ┌──▼────────────┐
    │  后端工程师      │ │  前端工程师   │ │  测试工程师    │
    │  Phase 4       │ │  Phase 3     │ │  持续验证      │
    │  (Task 4.1~4.7)│ │  (Task 3.1~  │ │  pytest +     │
    │  报告自检引擎   │ │   3.2)       │ │  Playwright   │
    │  C01-C11       │ │  PTR核对页面  │ │  Golden File  │
    └───────┬────────┘ └──────┬───────┘ └───────────────┘
            │                 │
            ▼                 │
    ┌────────────────┐        │
    │  Phase 4 API   │◄───────┘ (Phase 3 完成)
    │  完成通知       │
    └───────┬────────┘
            │
    ┌───────▼────────┐
    │  前端工程师      │
    │  Phase 5        │
    │  (Task 5.1~5.2) │
    │  报告自检页面    │
    └───────┬────────┘
            │
    ┌───────▼────────┐
    │  集成工程师      │
    │  Phase 6        │
    │  (Task 6.1~6.4) │
    │  导出+集成+交付  │
    └────────────────┘
```

### 可并行的任务组合

| 组合 | 说明 | 无文件冲突 |
|------|------|:---------:|
| Phase 3 + Phase 4 | 前端 PTR 页面 + 后端自检引擎 | ✅ |
| Task 4.1 + Task 4.3 | OCR 服务 + 第三页核对器 | ✅ |
| Task 4.5 + Task 4.6 | 检验项目核对 + 页码核对 | ✅ |

### 不可并行的任务

| 依赖关系 | 原因 |
|---------|------|
| Phase 5 依赖 Phase 4 | 前端报告自检页面需要后端 API |
| Phase 6 依赖 Phase 3-5 | 集成测试需要前后端都完成 |
| Task 4.7 依赖 Task 4.1-4.6 | API 路由需要所有 service 就绪 |

## 文件所有权矩阵

> ⚠️ **并行开发时，严格遵守文件所有权，避免冲突。**

| 目录/文件 | 架构师 | 后端 | 前端 | 测试 | 集成 |
|----------|:------:|:----:|:----:|:----:|:----:|
| `docs/tasks.md` | ✏️ | 🔍 | 🔍 | 🔍 | 🔍 |
| `backend/app/services/` (Phase 4) | 🔍 | ✏️ | ❌ | 🔍 | ❌ |
| `backend/app/routers/report_check.py` | 🔍 | ✏️ | ❌ | 🔍 | ❌ |
| `backend/tests/` | 🔍 | ✏️ | ❌ | ✏️ | ❌ |
| `frontend/src/pages/ptr-compare/` | 🔍 | ❌ | ✏️ | 🔍 | ❌ |
| `frontend/src/pages/report-check/` | 🔍 | ❌ | ✏️ | 🔍 | ❌ |
| `frontend/src/components/ptr/` | 🔍 | ❌ | ✏️ | 🔍 | ❌ |
| `frontend/src/components/report/` | 🔍 | ❌ | ✏️ | 🔍 | ❌ |
| `backend/app/services/report_export_service.py` | 🔍 | ❌ | ❌ | 🔍 | ✏️ |
| `frontend/src/components/shared/ExportButton.tsx` | 🔍 | ❌ | ❌ | 🔍 | ✏️ |
| `start.sh` / `README.md` | 🔍 | ❌ | ❌ | ❌ | ✏️ |

✏️ = 可编辑 | 🔍 = 只读 | ❌ = 禁止访问

## 质量门禁

每个 Task 标记 `[x]` 前，**必须**通过以下检查：

### 后端任务
```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
# 所有测试 PASSED
```

### 前端任务
```bash
cd frontend && npm run build
# 零编译错误
# + Playwright MCP 浏览器实测通过
```

### 集成任务
```bash
# 后端全量回归
cd backend && source .venv/bin/activate && pytest tests/ -v

# 端到端：1539 + 2795 样本走通全流程
# Golden File 断言通过
```

## 注意事项

1. **测试不可跳过**：本项目有严格的测试铁律，任何测试工具不可用时必须停止并告知用户
2. **PRD 是权威来源**：业务规则以 `docs/prd.md` 为准，`CLAUDE.md` 为辅助参考
3. **UI 规范不可妥协**：玻璃拟态 + 弹簧物理动效 + 莫兰迪色系是设计基准
4. **Golden File 策略**：`素材/` 中的真实样本必须用于生成和验证 `.expected.json` 基准
