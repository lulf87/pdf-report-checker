# 软件开发团队 (Software Dev Team) - 使用指南

## 团队组成

本团队由 6 个核心角色组成，覆盖软件开发的完整生命周期：

| 角色 | 文件名 | 核心职责 |
|------|--------|----------|
| 项目负责人/架构师 | `team-lead.md` | 架构设计、技术决策、进度把控 |
| UI/UX 设计师 | `ui-designer.md` | 视觉系统、组件美学、交互动效 |
| 技术研究员 | `researcher.md` | 技术选型调研、POC 验证、方案对比 |
| Prompt 工程师 | `prompt-engineer.md` | Prompt 设计、模板管理、VLM 调优 |
| 前端开发工程师 | `frontend-dev.md` | UI实现、组件开发、用户体验 |
| 后端开发工程师 | `backend-dev.md` | API开发、数据库设计、系统稳定性 |
| 验证/测试工程师 | `qa-engineer.md` | 测试策略、自动化测试、质量保障 |

## 快速开始

### 1. 创建团队

```bash
# 在 Claude Code 中执行
Create team "software-dev-team" for <项目名称>
```

### 2. 启动任务

告诉团队你的需求，例如：

> "我需要开发一个用户管理系统，包含注册、登录、个人资料管理功能。请技术负责人先进行架构设计。"

### 3. 团队会自动协作

- **Tech Lead** 会先进行需求分析和技术选型
- 分解任务并分配给 Frontend、Backend 和 QA
- 各角色并行开发，定期同步进度
- QA 同步编写测试用例，确保质量

## 协作流程

### 标准开发流程

```
需求输入
   ↓
Tech Lead (架构设计 + 任务分解)
   ↓
Researcher (技术调研/选型，如涉及新技术)
   ↓
Frontend ←→ Backend (并行开发，API 契约对齐)
   ↓              ↓
QA (同步测试设计)
   ↓
集成测试 ← 代码审查
   ↓
交付验收
```

### UI/UX 设计优化流程

```
Tech Lead/Product 提出设计需求
   ↓
UI Designer 设计视觉方案 (Tokens/Mockups)
   ↓
Frontend 对接实现 (Tailwind/React)
   ↓
UI Designer 视觉走查 (Design Review)
   ↓
QA 功能验证
```

### 技术调研专项流程

当项目涉及新技术选型时，Researcher 先行：

```
Tech Lead/Backend 提出调研需求
   ↓
Researcher 执行调研 (广度扫描 → 深度验证 → POC)
   ↓
输出技术报告 (推荐方案 + 集成指南)
   ↓
Backend 基于报告进行实现
   ↓
Researcher 协助解决集成问题
```

### AI 功能开发流程（Prompt Engineer 主导）

当项目涉及 LLM/VLM 功能时：

```
Tech Lead/Backend 定义提取需求
   ↓
Prompt Engineer 设计 Prompt 和输出 Schema
   ↓
Backend 集成模型调用和结果解析
   ↓
QA 验证提取准确性（数据一致性校验）
   ↓
Prompt Engineer 基于 Bad Case 持续优化
```

## 最佳实践

### 任务粒度
- 每个功能点拆分为独立的 Task
- 前后端依赖的接口先行定义（契约优先）
- QA 的测试用例在开发完成前准备好

### 沟通模式
- **Tech Lead**: 主持每日站会，同步整体进度
- **Researcher ↔ Backend**: 技术选型报告直接交付，协作解决集成问题
- **Frontend ↔ Backend**: API 接口变更即时通知
- **QA ↔ All**: 发现阻塞性问题立即升级

### Researcher 特殊协作模式
- **输入**: 来自 Tech Lead 或 Backend 的具体技术问题（如"医疗 PDF 解析最佳方案"）
- **输出**: 结构化调研报告，包含可直接落地的推荐方案
- **交付物格式**: 对比矩阵、PoC 代码、集成指南、风险提示
- **时间盒**: 调研任务通常限制在 1-3 天内，避免过度研究

### Prompt Engineer 特殊协作模式
- **输入**: 来自 Backend 的提取需求、Schema 定义、性能约束
- **输出**: 标准化 Prompt 模板、模型配置、版本管理
- **交付物格式**: YAML/JSON 配置、Few-shot 示例库、调优指南
- **迭代机制**: 基于 QA 反馈的 Bad Case 持续优化

### 质量标准
- 代码必须经过 Code Review
- 单元测试覆盖率不低于 80%
- 关键路径必须有集成测试覆盖
- 性能指标符合预设目标

## 角色能力对标

每个角色都按照行业顶尖水平设计：

- **Tech Lead**: Martin Fowler 级别的架构思维
- **UI Designer**: Adam Wathan (Tailwind) / Rauno Freiberg (Vercel) 级别的视觉设计
- **Researcher**: Jeremy Howard 级别的技术选型与实验设计
- **Prompt Engineer**: Riley Goodside 级别的 Prompt 工程专家
- **Frontend**: Dan Abramov 级别的 React 专家
- **Backend**: Rob Pike 级别的系统设计
- **QA**: Kent C. Dodd 级别的自动化测试

## 使用示例

### 场景 1: 新功能开发

```
用户: 我需要添加一个订单管理模块

Tech Lead: 分析需求，设计订单状态机，分解任务
├── Frontend: 订单列表页、详情页、状态流转 UI
├── Backend: 订单 API、状态管理、与支付服务集成
└── QA: 订单流程测试、边界情况测试、并发测试
```

### 场景 2: 性能优化

```
用户: 系统响应太慢，需要优化

Tech Lead: 定位瓶颈，制定优化方案
├── Frontend: 首屏加载优化、代码分割、资源压缩
├── Backend: 数据库查询优化、缓存策略调整、连接池调优
└── QA: 基准测试、负载测试、回归测试
```

### 场景 3: 技术债务偿还

```
用户: 重构现有的单体应用为微服务

Tech Lead: 制定迁移策略，识别服务边界
├── Frontend: 适配新的 API Gateway，更新调用方式
├── Backend: 服务拆分、数据迁移、事件总线搭建
└── QA: 全量回归测试、契约测试、混沌测试
```

### 场景 4: 技术选型调研（Researcher 主导）

```
用户: 需要解析医疗 PDF 文件，提取表格和文本

Tech Lead: 识别需求，指派调研任务
├── Researcher: 评估 pdfplumber vs Marker vs Unstructured
│   ├── 准备 50 份真实医疗 PDF 测试样本
│   ├── 设计评估指标（准确率、速度、资源占用）
│   └── 输出：推荐方案 + PoC 代码 + 集成注意事项
└── Backend: 基于 Researcher 报告进行集成开发
```

### 场景 5: AI 功能集成（Prompt Engineer 主导）

```
用户: 接入视觉大模型解析医疗检验报告

Tech Lead: 定义功能边界和集成方式
├── Prompt Engineer: 设计 VLM Prompt 和提取模板
│   ├── 设计 JSON Schema 定义输出结构
│   ├── 构建 Few-shot 示例库
│   ├── 添加输出约束和校验规则
│   └── 输出：标准化 Prompt 模板 + 版本配置
├── Backend: 集成 VLM API 和结果解析逻辑
│   ├── 调用 Prompt Engineer 提供的模板
│   ├── 实现输出解析和错误处理
│   └── 与 Prompt Engineer 协作优化迭代
├── Frontend: 实现报告上传和结果展示界面
└── QA: 验证提取准确性（字段级比对）
```

### 场景 6: Prompt 优化迭代

```
用户: 提升医疗报告识别的准确率

Prompt Engineer: 分析 QA 反馈的 Bad Case
├── 归类错误类型（格式错误/字段缺失/幻觉内容）
├── 针对性优化 Prompt（添加示例/增强约束）
├── 设计 A/B 测试验证效果
└── 输出：新版本 Prompt + 效果对比报告
    ↓
Backend: 更新 Prompt 版本
QA: 回归测试验证提升
```

## 自定义扩展

如需增加特定领域专家，可基于模板创建新角色：

- **DevOps 工程师**: 基础设施、CI/CD、监控
- **安全工程师**: 安全审计、渗透测试、合规
- **数据工程师**: 数据管道、ETL、数据分析

## 注意事项

1. **避免微观管理**: 给团队明确目标，让成员自主决定实现细节
2. **及时反馈**: 对团队的输出及时给出反馈，调整方向
3. **资源平衡**: 根据项目复杂度调整各角色的任务分配
4. **质量保证**: 不要跳过测试环节，质量是团队共同的责任

---

*团队定义文件位置: .claude/agent/*
