# Report Checker Pro — 检验报告综合核对工具

## 项目概述

本项目是一个 Web 应用，用于医疗器械检验报告的综合核对。包含两大核心功能模块：

1. **PTR 条款核对**：核对检验报告（PDF）与产品技术要求（PTR，PDF）之间的条款文本一致性
2. **报告自身核对**：核对检验报告内部的字段一致性、照片覆盖性、标签匹配、检验项目结论等

用户通过 Dashboard 入口选择功能模块，上传 PDF 文件后系统自动完成核对并输出可视化结果。

## 业务领域术语

### PTR 条款核对相关

- **PTR**（产品技术要求）：委托方提供的技术文件，**第2章**包含需逐条检验的条款（章节名称不固定，可能为"性能指标""性能要求"等，按编号定位即可）
- **检验报告**：检验机构出具的检验结果文档，表格形式逐条记录检验结果
- **条款**：PTR 第2章中的编号段落，如 `2.1.1 工作频率`
- **标准条款**：报告中引用的国标/行标内容（如 GB、GB/T、YY、YY/T 等），不属于核对范围
- **见表X**：条款中引用 PTR 其他位置（通常第1章或附录）的表格数据

### 报告自身核对相关

- **排版页**：Word/PDF 的实际页码，从第1页开始计数
- **严格一致**：字符级完全一致（大小写、全半角、空格、标点敏感）
- **/ 与空白等价**：表格单元格空白视为 `/`
- **非空字段联合键**：同名多行时，用非空字段组合作为唯一匹配条件
- **Caption**：照片/标签下方的说明文字
- **主体名**：Caption 去除编号、方位词、类别词后的核心名称

## 环境要求

- **Python**：3.12+
- **Node.js**：18+
- **包管理**：pip + venv（Python），npm（Node.js）

## 技术栈

- **后端**：Python 3.12+，FastAPI，Pydantic
- **前端**：React 19 + TypeScript + Vite 7，TailwindCSS v4，**Framer Motion**（物理动效引擎）
- **PDF 解析**：PyMuPDF (fitz) 处理电子版 PDF
- **OCR**：PaddleOCR 处理扫描版 PDF（中文+特殊符号识别，特殊符号可后处理修正但需输出 WARNING 提示用户人工确认）
- **VLM/LLM**：GPT-4o / Gemini（OCR 失败时的增强识别，可选功能）
- **文本比对**：自定义差异算法 + Python difflib
- **报告导出**：PDF 格式（ReportLab 或 WeasyPrint）
- **测试**：pytest（后端）

## 项目结构

```
report-checker-pro/
├── CLAUDE.md                    ← 本文件
├── docs/
│   ├── prd.md                   ← 产品需求文档
│   └── tasks.md                 ← 开发任务清单
├── backend/
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              ← FastAPI 入口
│   │   ├── logging_config.py
│   │   ├── config.py            ← 配置管理（含 LLM 模式配置）
│   │   ├── routers/
│   │   │   ├── ptr_compare.py   ← PTR 条款核对 API
│   │   │   └── report_check.py  ← 报告自身核对 API
│   │   ├── services/
│   │   │   ├── pdf_parser.py         ← 统一 PDF 解析（电子版 + OCR 智能切换）
│   │   │   ├── ocr_parser.py         ← PaddleOCR 扫描版解析
│   │   │   ├── ptr_extractor.py      ← PTR 第2章条款与表格提取
│   │   │   ├── report_extractor.py   ← 报告结构解析（模块一/模块二共用检验表格解析）
│   │   │   ├── text_normalizer.py    ← 文本标准化（全半角等）
│   │   │   ├── comparator.py         ← PTR 条款文本比对引擎
│   │   │   ├── table_comparator.py   ← 表格展开内容比对
│   │   │   ├── report_checker.py     ← 报告自身核对主引擎
│   │   │   ├── inspection_item_checker.py ← 检验项目核对
│   │   │   ├── ocr_service.py        ← OCR 服务（报告自检用）
│   │   │   ├── llm_vision_service.py ← VLM 视觉提取
│   │   │   ├── llm_service.py        ← LLM 文本增强
│   │   │   ├── third_page_checker.py ← 第三页字段核对
│   │   │   ├── page_number_checker.py← 页码连续性核对
│   │   │   └── report_export_service.py ← PDF 报告导出
│   │   └── models/
│   │       ├── ptr_models.py         ← PTR 核对数据模型
│   │       ├── report_models.py      ← 报告核对数据模型
│   │       └── common_models.py      ← 公共模型
│   └── tests/
│       ├── conftest.py
│       ├── test_pdf_parser.py
│       ├── test_ptr_extractor.py
│       ├── test_comparator.py
│       ├── test_report_checker.py
│       └── test_inspection_item_checker.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx            ← 首页 Dashboard
│       │   ├── ptr-compare/
│       │   │   ├── PTRComparePage.tsx    ← PTR 核对主页面
│       │   │   ├── PTRUpload.tsx         ← PTR 文件上传
│       │   │   └── PTRResults.tsx        ← PTR 核对结果
│       │   └── report-check/
│       │       ├── ReportCheckPage.tsx   ← 报告自检主页面
│       │       ├── ReportUpload.tsx      ← 报告文件上传
│       │       └── ReportResults.tsx     ← 报告自检结果
│       ├── components/
│       │   ├── ui/                       ← 基础 UI 原子组件
│       │   │   ├── index.ts
│       │   │   ├── GlassCard.tsx
│       │   │   ├── Button.tsx
│       │   │   ├── Badge.tsx
│       │   │   └── AnimatedCounter.tsx
│       │   ├── layout/                   ← 布局组件
│       │   │   ├── index.ts
│       │   │   ├── Background.tsx
│       │   │   ├── MouseFollower.tsx
│       │   │   └── Header.tsx
│       │   ├── shared/                   ← 两模块共享组件
│       │   │   ├── FileUpload.tsx
│       │   │   ├── ProgressOverlay.tsx
│       │   │   └── ExportButton.tsx
│       │   ├── ptr/                      ← PTR 核对专用组件
│       │   │   ├── ClauseList.tsx
│       │   │   ├── ClauseCard.tsx
│       │   │   └── DiffViewer.tsx
│       │   └── report/                   ← 报告自检专用组件
│       │       ├── FieldComparisonCard.tsx
│       │       ├── ComponentCheckList.tsx
│       │       ├── InspectionItemTable.tsx
│       │       └── PageNumberCheck.tsx
│       ├── constants/
│       │   └── motion.ts
│       ├── hooks/
│       │   ├── index.ts
│       │   ├── useMousePosition.ts
│       │   └── useParallax.ts
│       ├── styles/
│       │   └── design-tokens.css
│       └── types/
│           ├── ptr.ts
│           └── report.ts
└── 素材/                                 ← 样本文件（不提交到版本控制）
```

## 开发环境管理

### 启动前必须检查

每次启动服务前，**必须**先检查并清理残留进程：

```bash
# 检查占用端口的进程
lsof -i :5173,:8000 | grep LISTEN

# 如有残留进程，先 kill 再启动
kill <PID>
```

### 禁止多实例运行

- 前端 dev server 只允许运行 **一个实例**（默认 port 5173）
- 后端 uvicorn 只允许运行 **一个实例**（默认 port 8000）
- 如果端口被占用，**必须先清理而非使用其他端口**

## 前端视觉设计规范（严格遵守）

本项目前端追求"数字孪生"质感和"沉浸式交互"体验。以下规范是前端所有界面的设计基准。

### 1. 视觉系统 (Visual System)

#### 核心风格

玻璃拟态 (Glassmorphism) 结合极简主义。所有容器都应有通透、悬浮、有层次的视觉感受。

#### 色彩方案 — 莫兰迪色系 (Morandi Colors)

```
/* 背景层 */
--bg-deep:       #0f1117;
--bg-gradient:   linear-gradient(135deg, #0f1117 0%, #1a1d2e 50%, #151822 100%);

/* 容器层 — 半透明磨砂 */
--glass-bg:      rgba(255, 255, 255, 0.03);
--glass-bg-hover: rgba(255, 255, 255, 0.06);
--glass-border:  rgba(255, 255, 255, 0.08);
--glass-highlight: rgba(255, 255, 255, 0.12);

/* 文字层 */
--text-primary:   rgba(255, 255, 255, 0.87);
--text-secondary: rgba(255, 255, 255, 0.54);
--text-muted:     rgba(255, 255, 255, 0.32);

/* 语义色 — 低饱和度 */
--color-success:  #6b9e8a;   /* 一致/通过 */
--color-danger:   #c07878;   /* 不一致/错误 */
--color-info:     #7a8fb5;   /* 信息/总数 */
--color-warn:     #c4a76c;   /* 警告/修改 */
--color-accent:   #8b7ec8;   /* 强调/按钮 */
```

#### 容器样式规范

每个卡片/容器必须同时满足以下 4 个视觉属性：

```css
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(1.2);
  -webkit-backdrop-filter: blur(20px) saturate(1.2);
  border: 1px solid var(--glass-border);
  border-top-color: var(--glass-highlight);
  border-left-color: var(--glass-highlight);
  box-shadow:
    0 4px 24px rgba(0, 0, 0, 0.25),
    0 1px 2px rgba(0, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  border-radius: 16px;
}
```

#### 排版

- 标题字体：系统 sans-serif，字重 600，letter-spacing: 0.02em
- 正文字体：系统 sans-serif，字重 400，line-height: 1.7
- 条款编号使用 monospace 字体
- 中文与英文/数字之间自动添加间距

### 2. 物理感交互动效 (Physics-based Motion)

#### 技术要求

使用 **Framer Motion** 实现所有动效。前端依赖中必须包含 `framer-motion`。

#### 动效规则

**所有动画默认必须使用弹簧物理 (Spring Physics)，禁止使用线性 (linear) 或简单 ease 缓动。**

**允许的例外（必须加注释说明原因）**：

- **旋转加载动画 (Spinner)**：允许 `ease: "linear"`
- **循环脉动动画 (Pulse)**：允许 `ease: "easeInOut"`
- **AnimatePresence 的 exit 动画**：**必须使用 tween（duration + ease）**，**禁止使用 spring**

```tsx
// ✅ 正确：入场用 spring，退出用 tween
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -20 }}
  transition={{
    ...SPRING_GENTLE,
    exit: { duration: 0.2, ease: "easeOut" }
  }}
>
```

#### AnimatePresence 使用范围限制

**禁止在主页面级别的组件切换（如 Dashboard ↔ PTRComparePage ↔ ReportCheckPage）中使用 `AnimatePresence mode="wait"`。**

**正确做法**：页面切换使用路由或简单条件渲染 + 独立入场动画。

**AnimatePresence 允许使用的场景**（仅限页面内小元素进出）：

- ✅ 文件上传卡片内的状态切换
- ✅ Toast/Alert 的弹出和消失
- ✅ 条款卡片展开后差异区域的淡入
- ✅ 筛选切换后列表项的进出

#### 弹簧参数（必须从常量文件导入）

所有弹簧参数统一定义在 `frontend/src/constants/motion.ts` 中，**禁止在组件中硬编码 spring 参数**：

```typescript
const SPRING_GENTLE = { type: "spring", stiffness: 120, damping: 20, mass: 1 };
const SPRING_SNAPPY = { type: "spring", stiffness: 400, damping: 25, mass: 0.8 };
const SPRING_SMOOTH = { type: "spring", stiffness: 200, damping: 30, mass: 1.2 };
const SPRING_PAGE = { type: "spring", stiffness: 80, damping: 20, mass: 1.5 };
```

#### 必须实现的动效

1. **容器入场**：`initial={{ opacity: 0, y: 20 }}` → `animate={{ opacity: 1, y: 0 }}`，配合 `SPRING_GENTLE`
2. **列表项错位入场**：条款列表每项使用 `staggerChildren: 0.04` 逐个浮现
3. **按钮交互**：`whileHover={{ scale: 1.03 }}` + `whileTap={{ scale: 0.97 }}`，配合 `SPRING_SNAPPY`
4. **状态标签**：一致/不一致标签使用不同颜色的柔和脉动效果
5. **卡片展开**：使用 `layout` 属性 + `AnimatePresence` 实现平滑尺寸变换

### 3. 高级沉浸式功能

#### 3.1 自定义鼠标光标

- 主光标：12px 实心圆，颜色 `var(--color-accent)`，带 `mix-blend-mode: difference`
- 跟随光标：36px 空心圆环，80ms 延迟跟随，使用弹簧物理
- 悬停可点击元素时：跟随光标平滑放大至 56px

#### 3.2 卡片动态展开 (Layout Animation)

1. 默认状态：紧凑卡片，显示编号 + 摘要 + 状态标签
2. 点击后：通过 `layoutId` 平滑扩展，展现完整内容
3. 差异高亮使用 `AnimatePresence` 淡入

#### 3.3 背景视差与微动

- 2-3 个大尺寸（300-500px）模糊光斑（radial-gradient）
- 跟随鼠标产生微弱视差偏移（±10px），系数 50-80

#### 3.4 滚动体验

- `scroll-behavior: smooth`
- 自定义滚动条：4px 宽，圆角，颜色 `var(--glass-highlight)`

### 4. Dashboard 页面设计

Dashboard 是应用首页，提供两个功能模块的入口。设计要求：

- 两个功能入口卡片，使用 `GlassCard` 容器
- 每个卡片包含：图标、功能名称、简短描述
- 悬停时卡片有微弹效果和光效变化
- 整体居中布局，背景使用深色渐变 + 视差光斑
- 顶部显示应用名称 "Report Checker Pro"

### 5. 实现方式映射

| 设计要素 | 实现文件 | 说明 |
|---------|---------|------|
| 主题色 / CSS 变量 | `src/styles/design-tokens.css` | 所有色值、间距、圆角统一定义，禁止组件内硬编码 |
| 弹簧动画参数 | `src/constants/motion.ts` | `SPRING_GENTLE` / `SNAPPY` / `SMOOTH` / `PAGE` |
| 玻璃拟态容器 | `components/ui/GlassCard.tsx` | 4 属性：半透明背景 + blur + 边框 + 多层阴影 |
| 背景渐变 + 光斑 | `components/layout/Background.tsx` | 深色渐变 + 2-3 个 radial-gradient 模糊光斑 |
| 自定义光标 | `components/layout/MouseFollower.tsx` | 主光标 12px + 跟随光环 36px，弹簧延迟 |
| 按钮 / 标签 / 计数器 | `components/ui/Button/Badge/AnimatedCounter.tsx` | 弹簧交互 + 语义色 |

### 6. UI 交付检查清单

每个前端 Task 完成时，对照检查：

- [ ] 使用 `design-tokens.css` 中的 CSS 变量，**未硬编码色值**
- [ ] 动画使用 `motion.ts` 中的弹簧常量，**未硬编码 spring 参数**
- [ ] 容器使用 `GlassCard`，满足 4 个视觉属性（背景 + blur + 边框 + 阴影）
- [ ] 文字对比度足够（柔白 `rgba(255,255,255,0.87)` + 深色背景 `#0f1117`）
- [ ] 所有圆角 ≥ 16px
- [ ] 入场动画使用 `staggerChildren` 错位浮现
- [ ] 按钮有 `whileHover` + `whileTap` 弹簧反馈
- [ ] 不同状态有明确视觉反馈（加载中/错误/成功使用语义色区分）
- [ ] `npm run build` 零编译错误

## 核心业务规则

> ⚠️ 以下业务规则摘自 `docs/prd.md`，如两处内容不一致，**以 `docs/prd.md` 为准**。修改业务规则时应先更新 `docs/prd.md`，再同步至本文件。

### 模块一：PTR 条款核对

#### 1. 报告结构识别

- 报告首页（PDF 第3页）的"检验项目"字段标明了需检验的 PTR 条款范围
- 报告第2页（PDF 第4页）的"型号规格或其他说明"中，若包含**"标准的内容"字样**，则解析该段中的序号范围，这些序号不参与核对
- 标准类型可能包括 GB、GB/T、YY、YY/T 等
- 标准内容序号不参与核对，从最大标准序号之后开始核对

#### 2. PTR 结构解析

- PTR **第2章**为核对目标（章节名称不固定，可能为"性能指标""性能要求"等，按编号 `2.` 定位即可）
- 条款层级：2 → 2.1 → 2.1.1 → 2.1.1.1 → ...
- 条款可引用其他位置的表格（"见表1"），需同时解析被引用表格

#### 3. 文本一致性判定规则

**核心规则：严格匹配**：
- 条款正文文本必须与 PTR 原文严格一致，任何不匹配均判定为不一致
- 条款编号必须与 PTR 对应
- 展开的表格参数名称和参数值必须与 PTR 表格一致

**比对前的标准化处理（不算差异）**：
- 全角/半角字符统一
- 因列宽导致的自然换行合并
- 多余空格去除

**不允许的差异（标记为不一致）**：
- 增删改任何字符
- 在 PTR 原文前后插入内容
- 条款编号不匹配

#### 4. 条款拆分处理

同一条款拆分为多行时，合并后再与 PTR 原文比较。

#### 5. "见表X"展开内容核对

核对表格参数名称和参数值与 PTR 源表一致。

### 模块二：报告自身核对

#### C01: 首页与第三页一致性核对

- **数据来源**：
  - 来源 A：报告**首页**（PDF 第1页）的字段
  - 来源 B：报告**第三页**（页眉包含"检验报告首页"的页面）的对应字段
- **核对对象**：`委 托 方`、`样品名称`、`型号规格` 三个字段
- **核对规则**：严格一致（字符级完全一致）
- **判定结果**：
  - ✅ 三个字段全部严格一致 → PASS
  - ❌ 任意字段不一致 → ERROR

---

#### C02: 第三页扩展字段核对

- **数据来源**：
  - 来源 A：报告**第三页**（页眉包含"检验报告首页"的页面）表格中的三个字段
  - 来源 B：**照片页**中 Caption 主体名与第三页"样品名称"一致的**中文标签**，OCR 提取的字段值
- **核对对象**：`型号规格`、`生产日期`、`产品编号/批号`、`委托方`、`委托方地址` 五个字段
- **核对规则**：分两步执行

**规则1："见样品描述栏"一致性校验**（仅针对`型号规格`、`生产日期`、`产品编号/批号`三个字段）
- 三个字段全部为"见'样品描述'栏" → ✅ PASS（这三个字段结束，`委托方`和`委托方地址`仍需规则2比对）
- 三个字段全部不是"见'样品描述'栏" → 进入规则2（五个字段均比对）
- 部分是"见'样品描述'栏" → ❌ ERROR（三个字段必须统一）

**规则2：标签字段比对**

从照片页中找到 Caption 主体名与第三页"样品名称"一致的中文标签，将第三页表格值与该标签 OCR 提取值进行比对：

| 第三页表格字段 | 标签字段映射（OCR 提取） |
|-------------|---------------------|
| `型号规格` | `型号` / `规格` / `规格型号` |
| `生产日期` | `MFG` / `MFD` / `生产日期` |
| `产品编号/批号` | `批号` / `LOT` / `序列号` / `SN` |
| `委托方` | `注册人` / `注册人名称` |
| `委托方地址` | `注册人住所` / `注册人地址` |

- **判定结果**：
  - ✅ 表格值与标签 OCR 值一致 → PASS
  - ❌ 表格值与标签 OCR 值不一致 → ERROR

---

#### C03: 生产日期格式与值一致性核对

- **数据来源**：
  - 来源 A：报告**第三页**表格的 `生产日期` 字段值
  - 来源 B：**照片页**中 Caption 主体名与第三页"样品名称"一致的中文标签，OCR 提取的生产日期值
- **核对对象**：生产日期的**格式模式**和**日期值**
- **触发条件**：第三页 `生产日期` ≠ "见'样品描述'栏"（即 C02 规则1判定为"全部不是"时）
- **核对规则**：格式（如 `.` vs `/` vs `-`）和值都必须一致，以标签为基准
- **判定结果**：
  - ✅ 格式和值都一致 → PASS
  - ❌ 格式不一致 → ERROR
  - ❌ 值不一致 → ERROR
- **示例**：

| 第三页表格 | 中文标签 OCR | 判定 |
|-----------|------------|------|
| `2026.01.08` | `2026/01/08` | ❌ 格式不一致（`.` vs `/`） |
| `2026-01-08` | `2026-01-09` | ❌ 值不一致 |
| `2026-01-08` | `2026-01-08` | ✅ PASS |

---

#### C04: 样品描述表格核对

- **数据来源**：
  - 来源 A：**样品描述表格**（从第四页起，页面文本包含"样品描述"的页面中的表格）
  - 来源 B：**照片页**中各部件对应的**中文标签**，OCR 提取的字段值
- **核对对象**：表格每行（每个部件）的字段值与该部件对应中文标签 OCR 值
- **核对规则**：严格一致，`/` 或空白视为无值，与标签无该字段等价
- **判定结果**：
  - ✅ 一致 → PASS
  - ❌ 不一致 → ERROR
- **忽略列**：`序号`、`备注`
- **同义词映射**：

| 标准列名 | 可识别的同义词 |
|---------|-------------|
| `部件名称` | 部件名称、产品名称、名称 |
| `规格型号` | 规格型号、型号规格、型号、规格 |
| `序列号批号` | 序列号批号、序列号/批号、批号、序列号、SN、LOT |
| `生产日期` | 生产日期、MFG、MFD |
| `失效日期` | 失效日期、有效期至、EXP |

---

#### C05: 照片覆盖性核对

- **数据来源**：
  - 来源 A：**样品描述表格**中的每个部件（`部件名称`列）
  - 来源 B：**照片页**中所有照片的 Caption 主体名
- **核对对象**：每个部件是否至少有一张照片覆盖
- **核对规则**：Caption 主体名与部件名称匹配（支持精确匹配 + 部分匹配）
- **判定结果**：
  - ✅ 部件有至少一张照片匹配 → PASS
  - ❌ 部件无任何照片匹配 → ERROR
- **忽略/特殊处理**：备注列包含"本次检测未使用"的部件，无照片不报错

---

#### C06: 中文标签覆盖核对

- **数据来源**：
  - 来源 A：**样品描述表格**中的每个部件（`部件名称`列）
  - 来源 B：**照片页**中所有中文标签的 Caption 主体名（Caption 包含"中文标签"/"中文标签样张"/"标签样张"等关键词）
- **核对对象**：每个部件是否至少有一张中文标签覆盖
- **核对规则**：
  - 单一部件：至少有一张中文标签匹配
  - 同名多行部件：多张标签，按"非空字段联合键"分别匹配
- **判定结果**：
  - ✅ 部件有至少一张中文标签匹配 → PASS
  - ❌ 部件无任何中文标签匹配 → ERROR
- **忽略/特殊处理**：备注列包含"本次检测未使用"的部件，无标签不报错

---

#### C07: 检验项目-单项结论核对

- **数据来源**：
  - 来源：**检验项目表格**（表头包含：序号、检验项目、标准条款、标准要求、检验结果、单项结论、备注）
- **核对对象**：每个序号的`单项结论`是否与`检验结果`逻辑一致
- **核对规则**：按优先级判定期望结论，与实际结论比对

| 优先级 | 条件 | 期望结论 |
|-------|------|---------|
| 1 | 任意标准要求的检验结果 = "不符合要求" 或空白 | `不符合` |
| 2 | 所有标准要求的检验结果 = "——" 或 "/" | `/` |
| 3 | 任意标准要求的检验结果 = "符合要求" 或非空文本/数字 | `符合` |

- **判定结果**：
  - ✅ 实际单项结论 = 期望单项结论 → PASS
  - ❌ 实际单项结论 ≠ 期望单项结论 → ERROR

---

#### C08: 检验项目-非空字段核对

- **数据来源**：
  - 来源：**检验项目表格**
- **核对对象**：每行的 `检验结果`、`单项结论`、`备注` 三个字段
- **核对规则**：三个字段均不得为空
- **判定结果**：
  - ✅ 三字段均非空 → PASS
  - ❌ 任意字段为空 → ERROR
- **特殊处理**：合并单元格以合并区域首行值为准，首行为空则整个区域视为空

---

#### C09: 检验项目-序号连续性核对

- **数据来源**：
  - 来源：**检验项目表格**的`序号`列
- **核对对象**：序号的连续性和完整性
- **核对规则**：序号从1开始连续递增，无跳号、无重复、无空白
- **判定结果**：
  - ✅ 序号连续完整 → PASS
  - ❌ 序号跳号/重复/空白 → ERROR

---

#### C10: 检验项目-续表标记核对

- **数据来源**：
  - 来源：**检验项目表格**跨页时的序号列
- **核对对象**：跨页续行的"续"字标记
- **核对规则**：同一序号跨页时，新页第一行的序号前必须加"续"字；"续"字只能出现在本页第一行
- **判定结果**：
  - ✅ 续表标记正确 → PASS
  - ❌ 缺少续表标记 → ERROR
  - ❌ 续字位置错误 → ERROR
- **示例**：

```
✅ 正确：
  第2页末尾: 5 | 项目X | ...（未完成）
  第3页第一行: 续5 | 项目X | ...（续上）
  第3页第二行: 6 | 项目Y | ...

❌ 错误：
  第3页第一行: 5  ← 应标记为"续5"
  第3页第二行: 续5  ← "续"字应在第一行
```

---

#### C11: 页码连续性核对

- **数据来源**：
  - 来源：从**第三页**开始，每页**右上角**的页码文字（格式：`共XXX页 第Y页`）
- **核对对象**：页码 Y 的连续性和 XXX 的一致性
- **核对规则**：
  - Y 从1开始连续递增，无跳号、无重复
  - 最后一页的 Y 值必须等于 XXX
  - 所有页的 XXX 值必须相同
- **判定结果**：
  - ✅ 全部满足 → PASS
  - ❌ Y 不连续 → ERROR
  - ❌ 末页 Y ≠ XXX → ERROR
  - ❌ XXX 不一致 → ERROR

## LLM 配置

系统支持三种 LLM 模式（通过 `.env` 配置）：

| 模式 | 行为 | 适用场景 |
|-----|------|---------|
| `enhance` | VLM 优先，OCR 辅助验证 | 追求最高准确率 |
| `fallback` | OCR 优先，失败时调用 VLM | 节省 API 成本 |
| `disabled` | 纯 OCR/规则引擎 | 离线环境 |

```bash
# .env
OPENROUTER_API_KEY=xxx
LLM_MODEL=google/gemini-2.0-flash-exp
ENABLE_LLM_COMPARISON=false
LLM_COMPARISON_MODE=fallback
```

## 开发约定

- 后端 API 使用 RESTful 风格
- 所有代码注释、变量名使用英文，UI 文案使用中文
- PDF 解析优先尝试电子版提取，失败或文字密度过低时自动切换 OCR
- 比对结果返回结构化 JSON，前端渲染差异高亮

### React 编码规范

1. **Hooks 规则**：所有 React Hooks **只能在组件函数的顶层调用**
2. **组件导出**：使用 barrel exports（`index.ts`）
3. **类型定义**：共享 interface 提取到 `types/` 目录

### Tailwind CSS v4 注意事项

1. v4 使用 CSS-first 配置（`@import "tailwindcss"`），不再使用 `tailwind.config.js`
2. 复杂 arbitrary value 若渲染异常，改用 inline style 或 `design-tokens.css` 中的 CSS class

### API 轮询容错规范

所有轮询类请求必须处理：`completed`、`error`、`not_found` 状态，以及 60 秒超时机制。

## 开发流程约束

### 子任务驱动开发

按 `docs/tasks.md` 中定义的子任务顺序执行。每个子任务是独立、可验证的工作单元。

**铁律：当前子任务的所有测试通过后，才能开始下一个子任务。**

### 测试要求

#### 后端单元测试

- 使用 `pytest` 编写，存放在 `backend/tests/`
- 每个子任务完成后运行 `cd backend && pytest tests/ -v` 确认通过

#### 前端实测（Playwright MCP）

> ⚠️ **所有前端或前端+后端联调的功能，必须使用 Playwright MCP 在浏览器中实际验证。严禁使用以下方式替代：**
> - ❌ 仅靠 `npm run build` 编译通过就算完成
> - ❌ 仅靠 `npm run dev` 启动成功就算完成
> - ❌ 编写单元测试模拟 DOM 替代浏览器实测
> - ❌ 截图或人工描述替代实际操作验证
>
> **如果 Playwright MCP 不可用或无法正常工作，必须立即停止并告知用户，不得使用任何替代方案绕过。**

前端任务验收流程：

```
1. npm run build → 零编译错误（必要条件，但不充分）
2. 启动前后端服务（npm run dev + uvicorn）
3. 使用 Playwright MCP 打开浏览器访问页面
4. 实际操作验证：页面渲染、交互响应、数据流转
5. 确认通过后才可标记 [x]
```

#### 通用测试铁律

> ⚠️ **所有测试要求均不允许使用替代方案。后端必须用 pytest 实测，前端必须用 Playwright MCP 实测。如果任何测试工具不可用或测试无法通过，必须停止并告知用户，不得绕过。**

### Golden File 测试策略 (必选)

本项目强制使用 Golden File 测试策略来保障解析和核心比对逻辑的准确性。用户已经在 `素材/` 目录下放置了真实业务样本和预期结果基准。核心验证逻辑必须确保真实样本输入与预期结果完全一致。

#### 样本结构:
```
素材/
├── ptr/                            ← 产品技术要求 (PTR)
│   ├── 1539/射频脉冲电场消融系统产品技术要求-20260102-Clean.pdf
│   └── 2795/产品技术要求-心脏脉冲电场消融仪 - 1201.pdf
└── report/                         ← 对应的检验报告
    ├── 1539/QW2025-1539 Draft.pdf
    └── 2795/QW2025-2795 Draft.pdf
```

#### 工作流要求:
1. **生成预期基准**：在使用解析器（PDF/OCR）或比对器（Comparator）处理这些样本后，需将正确的人工校验结果保存为 `.expected.json` (Golden File)。
2. **自动化校验**：后续的 pytest 单元测试和集成测试，必须加载对应的样本文件进行处理，并将实际输出与对应的 `.expected.json` 进行断言对比。
3. **不可回归**：任何导致与 Golden File 不一致的代码修改都必须被拦截并修复，或者在确认业务规则变更后显式更新 Golden File。

### 子任务执行流程

```
对于每个子任务：
1. 阅读 docs/tasks.md 中该任务描述和验收标准
2. 实现功能代码
3. 编写/运行对应测试
   - 后端任务：pytest
   - 前端任务：npm run build + Playwright MCP 实测
   - 联调任务：pytest + Playwright MCP 实测
4. 测试失败 → 修复 → 重新测试
5. 所有测试通过 → 在 docs/tasks.md 中标记 [x]
6. 进入下一个子任务
```

### 验证铁律

- 标记 [x] 前必须实际执行测试命令并确认通过
- 后端：`cd backend && source .venv/bin/activate && pytest tests/ -v`
- 前端：`cd frontend && npm run build` **+** Playwright MCP 浏览器实测
- 修复 bug 后必须运行所有已有测试确认无回归
- **无法完成测试时必须停止并告知用户，严禁跳过或使用替代方案**

## 运行命令

```bash
# 后端
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# 前端
cd frontend && npm run dev

# 后端测试
cd backend && source .venv/bin/activate && pytest tests/ -v
```

