# CLAUDE.md — 报告核对工具

## 项目概述

这是一个 **Electron 桌面应用**，用于医疗检验报告的自动化核对。用户上传 PDF/DOCX 格式的检验报告，系统自动解析文档结构、OCR 识别中文标签、调用 VLM 提取结构化数据，并逐字段比对生成核对报告。

## 技术栈

| 层               | 技术                                                                       |
| ---------------- | -------------------------------------------------------------------------- |
| **桌面壳** | Electron 28 (主进程 `src/main/main.js` + 预加载 `src/main/preload.js`) |
| **前端**   | React 18 + Ant Design 5 + Vite (`src/renderer/`)                         |
| **后端**   | Python 3.9+ / FastAPI / Uvicorn (`python_backend/`)                      |
| **AI/OCR** | PaddleOCR、PyMuPDF、VLM (GPT-4o / Gemini)                                  |
| **打包**   | electron-builder (macOS DMG / Windows NSIS)                                |

## 项目结构

```
report-checker/
├── CLAUDE.md                    ← 本文件
├── package.json                 ← Electron + 主项目配置
├── SPEC.md                      ← 核对规则规格说明（冻结）
├── REPORT_CHECKER_SPEC.md       ← 检验项目核对规格
├── src/
│   ├── main/                    ← Electron 主进程
│   │   ├── main.js              ← 窗口管理、IPC、Python 子进程启动
│   │   └── preload.js           ← contextBridge 安全 API
│   └── renderer/                ← React 前端应用
│       ├── package.json
│       ├── vite.config.js
│       └── src/                 ← React 组件和页面
├── python_backend/              ← Python FastAPI 后端
│   ├── main.py                  ← FastAPI 入口（端口 8000）
│   ├── config.py                ← 配置管理（含 LLM 模式配置）
│   ├── .env                     ← 环境变量（API Key 等）
│   ├── models/                  ← Pydantic 数据模型
│   ├── services/                ← 核心业务服务
│   │   ├── pdf_parser.py        ← PDF 解析与页面提取
│   │   ├── ocr_service.py       ← PaddleOCR 集成
│   │   ├── llm_service.py       ← LLM 文本增强
│   │   ├── llm_vision_service.py← VLM 视觉提取
│   │   ├── report_checker.py    ← 核对主逻辑
│   │   ├── inspection_item_checker.py ← 检验项目核对
│   │   ├── report_export_service.py   ← 报告导出（PDF/Excel）
│   │   └── docx_parser.py       ← DOCX 解析
│   └── utils/                   ← 工具函数
└── .claude/                     ← Agent Team 定义
    ├── team-manifest.json       ← 团队清单（角色、工作流、约束）
    └── agent/                   ← 各角色详细定义
        ├── team-lead.md
        ├── researcher.md
        ├── prompt-engineer.md
        ├── backend-dev.md
        ├── frontend-dev.md
        └── qa-engineer.md
```

## 代码规范

### Python 后端

- 使用 **FastAPI** + **Pydantic** 定义 API 和数据模型
- 使用 `async def` 异步端点
- 文件命名：`snake_case.py`
- 配置通过 `.env` + `config.py` 管理
- 测试文件放在 `python_backend/` 根目录，命名为 `test_*.py`，使用 **pytest**

### 前端

- React 组件使用 **JSX**，函数式组件 + Hooks
- UI 组件基于 **Ant Design 5**
- 构建工具为 **Vite**

### Electron

- 主进程和预加载脚本使用 **CommonJS**（`require/module.exports`）
- 渲染进程通过 `window.electronAPI`（由 preload 暴露）与主进程通信

## 模块边界

### 后端核心模块（修改时需注意影响范围）

1. **`report_checker.py`** — 核对主流程编排，调用其他服务
2. **`inspection_item_checker.py`** — 检验项目逐项核对，规则密集
3. **`ocr_service.py`** — OCR 引擎集成，是数据准确性的关键
4. **`llm_vision_service.py`** — VLM 视觉提取，与 Prompt 模板紧密耦合

> [!IMPORTANT]
> 修改 `report_checker.py` 或 `inspection_item_checker.py` 时，务必运行相关测试：
>
> ```bash
> cd python_backend && python -m pytest test_inspection_item_checker.py test_fixes_regression.py -v
> ```

### 前端模块

- `src/renderer/` — React 应用，独立的 `package.json` 和 Vite 构建
- `src/main/` — Electron 主进程，管理窗口和 Python 子进程

## 启动方式

```bash
# 安装所有依赖
npm run install:all

# 开发模式（同时启动 Electron + Python 后端）
npm run dev

# 单独启动后端（调试用）
cd python_backend && uvicorn main:app --reload --port 8000
```

## LLM 降级策略

系统支持三种 LLM 模式（通过 `.env` 配置）：

| 模式         | 行为                     | 适用场景                 |
| ------------ | ------------------------ | ------------------------ |
| `enhance`  | VLM 优先，OCR 辅助验证   | 网络可用，追求最高准确率 |
| `fallback` | OCR 优先，失败时调用 VLM | 节省 API 成本            |
| `disabled` | 纯 OCR/规则引擎          | 离线环境，无网络         |

## Agent Team — 团队协作指令

> [!IMPORTANT]
> **本项目采用团队模式开发。** 收到任务后，你（Lead Agent）必须：
>
> 1. 先阅读对应角色定义文件，理解该角色的职责和能力
> 2. 根据任务性质选择合适的工作流，将任务分解并分配给子 Agent
> 3. 每个子 Agent 在执行前必须先阅读自己的角色定义文件

### 角色定义文件

执行任务时，请根据任务类型 **读取对应的角色文件** 并按其中的要求行事：

| 角色 ID             | 角色名称          | 定义文件（必读）                     | 职责范围                                       |
| ------------------- | ----------------- | ------------------------------------ | ---------------------------------------------- |
| `tech-lead`       | 项目负责人/架构师 | `.claude/agent/team-lead.md`       | 架构决策、任务分解、技术选型、进度把控         |
| `researcher`      | 技术研究员        | `.claude/agent/researcher.md`      | 技术调研、POC 验证、方案对比                   |
| `prompt-engineer` | Prompt 工程师     | `.claude/agent/prompt-engineer.md` | VLM Prompt 设计与优化、模板管理                |
| `backend-dev`     | 后端开发工程师    | `.claude/agent/backend-dev.md`     | FastAPI 开发、PDF 解析、VLM/OCR 集成、降级策略 |
| `frontend-dev`    | 前端开发工程师    | `.claude/agent/frontend-dev.md`    | Electron 主进程、React UI、打包发布            |
| `qa-engineer`     | 验证/测试工程师   | `.claude/agent/qa-engineer.md`     | 自动化测试、数据一致性校验、AI 提取准确性验证  |

### 工作流选择规则

根据任务类型自动选择工作流：

| 任务类型                | 关键词识别                          | 工作流                                                                       |
| ----------------------- | ----------------------------------- | ---------------------------------------------------------------------------- |
| **AI 功能开发**   | VLM、Prompt、模型、提取、识别       | `tech-lead` → `prompt-engineer` → `backend-dev` → `qa-engineer`   |
| **全栈功能迭代**  | UI、页面、界面、新功能、组件        | `tech-lead` → `frontend-dev` + `backend-dev` → `qa-engineer`       |
| **Prompt 优化**   | 准确率、Bad Case、幻觉、优化 Prompt | `qa-engineer` → `prompt-engineer` → `backend-dev` → `qa-engineer` |
| **Bug 修复/回归** | bug、报错、修复、回归               | `tech-lead` → `backend-dev` → `qa-engineer`                          |
| **技术选型**      | 选型、对比、调研、评估              | `tech-lead` → `researcher` → `backend-dev`                           |

### 任务分配规则

1. **所有任务默认经过 `tech-lead`**：先读取 `.claude/agent/team-lead.md`，按其中的任务分解模板输出子任务
2. **子 Agent 执行前**：必须读取自己的角色定义文件，按文件中的「工作方式」和「输出格式」执行
3. **涉及核对规则变更**：必须同时分配给 `backend-dev`（实现）和 `qa-engineer`（验证）
4. **涉及 Prompt 变更**：必须经过 `prompt-engineer` → `backend-dev` → `qa-engineer` 闭环

### 关键约束

- **部署形态**：桌面应用，非云服务
- **离线支持**：`disabled` 模式下需保证基本功能可用
- **目标平台**：macOS、Windows
- **团队清单参考**：`.claude/team-manifest.json`（完整的角色、工作流和约束定义）

## 关键业务规则（速查）

> 详细规则见 `SPEC.md`，以下为高频引用的核心规则：

- **严格一致**：字段比对采用字符级完全一致（大小写、全/半角、空格、标点敏感）
- **`/` 与空白等价**：表格值为空白视为 `/`
- **不做模糊匹配**：宁可报错由人工复核
- **降级仍以严格一致为准**：即使引入 VLM，最终判定仍为严格一致
