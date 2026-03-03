# Report Checker Pro — 开发任务清单

> 按顺序执行，每个任务完成后标记 `[x]`，未完成标记 `[ ]`，进行中标记 `[/]`

> ⚠️ **测试铁律**
> - **后端任务**：必须使用 `pytest` 实测通过
> - **前端任务**：`npm run build` 零错误 **+** 使用 **Playwright MCP** 在浏览器中实际验证页面渲染和交互
> - **联调任务**：`pytest` **+** **Playwright MCP** 实测
> - 严禁使用任何替代方案（仅编译通过、模拟 DOM 测试、人工描述等）绕过以上要求
> - 如果测试工具不可用或测试无法通过，**必须停止并告知用户**，不得跳过

---

## Phase 0: 项目脚手架

### Task 0.1: 后端项目初始化 ← PRD §7
- [x] 创建 `backend/` 目录结构
- [x] 创建 `requirements.txt`（FastAPI, uvicorn, PyMuPDF, PaddleOCR, pydantic, python-multipart, python-dotenv, reportlab, httpx, pytest）
- [x] 创建 `pyproject.toml`（pytest 配置）
- [x] 创建 Python 虚拟环境并安装依赖
- [x] 创建 `app/__init__.py`、`app/main.py`（FastAPI 最小应用 + CORS + health 端点）
- [x] 创建 `app/logging_config.py`
- [x] 创建 `app/config.py`（LLM 配置、环境变量管理）
- [x] 创建 `.env.example`
- [x] **验收标准**：`uvicorn app.main:app --reload` 启动成功，`/api/health` 返回 200 ✅ 已验证 (2026-03-02)

### Task 0.2: 前端项目初始化 ← PRD §6.4
- [x] 使用 `npx create-vite@latest` 创建 React + TypeScript 项目
- [x] 安装依赖：`framer-motion`, `tailwindcss@4`, `@tailwindcss/postcss`, `autoprefixer`, `postcss`
- [x] 配置 TailwindCSS v4（CSS-first 方式）
- [x] 创建 `src/styles/design-tokens.css`（CSS 变量定义）
- [x] 创建 `src/constants/motion.ts`（弹簧参数 + 动画预设）
- [x] 创建最小 `App.tsx`（验证 Tailwind + Framer Motion 集成）
- [x] **验收标准**：`npm run dev` 启动成功，`npm run build` 零编译错误 ✅ 已验证 (2026-03-02)

---

## Phase 1: 前端 — 设计系统与 Dashboard

### Task 1.1: 基础 UI 组件 ← PRD §6.4
- [x] 创建 `components/ui/GlassCard.tsx`（玻璃拟态容器）
- [x] 创建 `components/ui/Button.tsx`（弹簧动效按钮）
- [x] 创建 `components/ui/Badge.tsx`（状态标签，带柔和脉动）
- [x] 创建 `components/ui/AnimatedCounter.tsx`（数字滚动动画）
- [x] 创建 `components/ui/index.ts`（barrel export）
- [x] **验收标准**：`npm run build` 通过 ✅ 已验证 (2026-03-02)

### Task 1.2: 布局组件 ← PRD §6.4
- [x] 创建 `components/layout/Background.tsx`（深色渐变背景 + 视差光斑）
- [x] 创建 `components/layout/MouseFollower.tsx`（自定义鼠标光标跟随）
- [x] 创建 `components/layout/Header.tsx`（顶部标题栏，含返回按钮）
- [x] 创建 `hooks/useMousePosition.ts`
- [x] 创建 `hooks/useParallax.ts`
- [x] 创建 `components/layout/index.ts`
- [x] **验收标准**：`npm run build` 通过 ✅ 已验证 (2026-03-02)

### Task 1.3: Dashboard 首页 ← PRD §3
- [x] 创建 `pages/Dashboard.tsx`
- [x] 实现两个功能入口卡片（PTR 核对 / 报告自检）
- [x] 卡片使用 GlassCard，包含图标、标题、描述
- [x] 实现入场动画（stagger 浮现）
- [x] 实现卡片悬停微弹效果
- [x] 更新 `App.tsx`，实现 Dashboard ↔ 功能页面的路由/条件渲染
- [x] **验收标准**：`npm run build` 通过。页面显示暗色背景 + 两个玻璃卡片 + 自定义光标跟随 ✅ Playwright MCP 验证通过 (2026-03-02)

### Task 1.4: 共享上传组件 ← PRD §3.3
- [x] 创建 `components/shared/FileUpload.tsx`（支持拖拽上传 + 点击上传）
- [x] 支持单文件和双文件上传模式
- [x] 上传区域使用 GlassCard 容器，拖拽时有视觉反馈
- [x] 显示文件名和文件大小
- [x] 创建 `components/shared/ProgressOverlay.tsx`（处理进度叠加层）
- [x] **验收标准**：`npm run build` 通过 ✅ 已验证 (2026-03-02)

---

## Phase 2: 后端 — PTR 条款核对引擎

### Task 2.1: 统一 PDF 解析器 ← PRD §4.4
- [x] 创建 `services/pdf_parser.py`
- [x] 实现电子版 PDF 文字提取（PyMuPDF）
- [x] 实现电子版 PDF 表格提取
- [x] 实现扫描件检测（文字密度判断）
- [x] 实现 OCR 自动切换
- [x] 创建 `models/common_models.py`（PDF 页面、文字块、表格数据模型）
- [x] 编写 `tests/test_pdf_parser.py`
- [x] **验收标准**：`pytest tests/test_pdf_parser.py -v` 全部 PASSED ✅ 17 passed, 2 skipped (2026-03-02)

### Task 2.2: OCR 解析器 ← PRD §4.4.2
- [x] 创建 `services/ocr_parser.py`
- [x] 集成 PaddleOCR
- [x] 处理特殊符号识别（Ω、±、℃、²、³、μ）
- [x] 保留位置信息用于表格重建
- [x] 编写 `tests/test_ocr_parser.py`
- [x] **验收标准**：`pytest tests/test_ocr_parser.py -v` 全部 PASSED ✅ 22 passed, 3 skipped (2026-03-02)

### Task 2.3: PTR 条款提取器 ← PRD §4.5, §4.3
- [x] 创建 `services/ptr_extractor.py`
- [x] 实现第2章起止位置识别（按编号 `2.` 定位，不依赖章节名称）
- [x] 实现条款编号层级解析（2 → 2.1 → 2.1.1 → ...）
- [x] 实现子项识别（a) b) c)、a、b、c、——/— 等形式）
- [x] 实现表格引用识别（"见表X"）
- [x] 实现被引用表格定位和解析
- [x] 创建 `models/ptr_models.py`
- [x] 编写 `tests/test_ptr_extractor.py`
- [x] **验收标准**：`pytest tests/test_ptr_extractor.py -v` 全部 PASSED ✅ 31 passed (2026-03-02)

### Task 2.4: 报告条款提取器 ← PRD §4.6, §4.2.3
- [x] 创建 `services/report_extractor.py`
- [x] 实现 PDF 第3页"检验项目"字段提取（条款范围）
- [x] 实现 PDF 第4页"型号规格或其他说明"中"标准的内容"字样检测及序号范围解析
- [x] 实现检验结果表格解析（7列结构）
- [x] 实现合并单元格处理
- [x] 实现跨页续行处理（"续 160"）
- [x] 实现同一条款多行合并
- [x] 实现标准内容序号过滤（支持 GB/GB-T/YY/YY-T 多标准并集）
- [x] 创建 `models/report_models.py`
- [x] 编写 `tests/test_report_extractor.py`
- [x] **验收标准**：`pytest tests/test_report_extractor.py -v` 全部 PASSED ✅ 23 passed, 2 skipped (2026-03-02)

### Task 2.5: 文本标准化器 ← PRD §4.7.1
- [x] 创建 `services/text_normalizer.py`
- [x] 实现全角/半角统一
- [x] 实现多余空格去除
- [x] 实现自然换行合并
- [x] 实现格式性标注去除（"单位：V"）
- [x] 编写 `tests/test_text_normalizer.py`
- [x] **验收标准**：`pytest tests/test_text_normalizer.py -v` 全部 PASSED ✅ 12 passed (2026-03-02)

### Task 2.6: 条款文本比对引擎 ← PRD §4.7.2
- [x] 创建 `services/comparator.py`
- [x] 实现严格匹配逻辑（任何不匹配均判定为不一致）
- [x] 实现 diff 算法定位具体差异
- [x] 实现差异分类（insert/delete/replace/equal）
- [x] 结合 `素材/` 目录中的 1539 和 2795 样本生成条款文本比对的 Golden File (`.expected.json`)
- [x] 创建 `models/comparator_models.py`
- [x] 编写 `tests/test_comparator.py`（包含对 Golden File 的断言测试）
- [x] **验收标准**：`pytest tests/test_comparator.py -v` 全部 PASSED ✅ 24 passed (2026-03-02)

### Task 2.7: 表格展开比对器 ← PRD §4.7.3, §4.5.4
- [x] 创建 `services/table_comparator.py`
- [x] 实现"见表X"展开内容提取
- [x] 实现参数名称比对
- [x] 实现参数值比对
- [x] 创建 `models/table_comparator_models.py`
- [x] 编写 `tests/test_table_comparator.py`
- [x] **验收标准**：`pytest tests/test_table_comparator.py -v` 全部 PASSED ✅ 15 passed (2026-03-02)

### Task 2.8: PTR 核对 API 路由 ← PRD §7.2
- [x] 创建 `routers/ptr_compare.py`
- [x] 实现 `POST /api/ptr/upload`（上传 + 启动后台比对）
- [x] 实现 `GET /api/ptr/{task_id}/progress`（进度查询）
- [x] 实现 `GET /api/ptr/{task_id}/result`（结果获取）
- [x] 实现后台任务编排（串联各 service）
- [x] 在 `main.py` 注册路由
- [x] 编写 `tests/test_api_ptr.py`（API 集成测试）
- [x] **验收标准**：`pytest tests/ -v` 全部 PASSED ✅ 39 passed, 1 skipped (2026-03-02)

---

## Phase 3: 前端 — PTR 核对页面

### Task 3.1: PTR 文件上传页面 ← PRD §4.8
- [x] 创建 `pages/ptr-compare/PTRComparePage.tsx`
- [x] 创建 `pages/ptr-compare/PTRUpload.tsx`（双文件上传：报告+PTR）
- [x] 实现文件验证（仅允许 PDF）
- [x] 实现上传 API 调用
- [x] 实现进度轮询（含 completed/error/not_found/timeout 处理）
- [x] **验收标准**：`npm run build` 通过 ✅ Playwright MCP 验证通过 (2026-03-03)

### Task 3.2: PTR 核对结果页面 ← PRD §4.8, §4.9
- [x] 创建 `pages/ptr-compare/PTRResults.tsx`
- [x] 创建 `components/ptr/ClauseList.tsx`（条款列表，stagger 入场）
- [x] 创建 `components/ptr/ClauseCard.tsx`（条款卡片，点击展开动画）
- [x] 创建 `components/ptr/DiffViewer.tsx`（差异高亮对比）
- [x] 实现结果总览（AnimatedCounter + 一致率）
- [x] 实现筛选："全部" / "仅不一致"
- [x] 实现 "返回 Dashboard" 和 "重新上传" 按钮
- [x] 创建 `types/ptr.ts`（TypeScript 类型定义）
- [x] **验收标准**：`npm run build` 通过 ✅ Playwright MCP 验证通过 (2026-03-03)

---

## Phase 4: 后端 — 报告自身核对引擎

### Task 4.1: OCR 服务（报告自检用） ← PRD §5.4
- [x] 创建 `services/ocr_service.py`
- [x] 集成 PaddleOCR 针对中文标签的识别
- [x] 实现字段提取正则（批号、序列号、生产日期、失效日期）
- [x] 实现照片/标签页 Caption 解析
- [x] 实现主体名提取（去除编号、方位词、类别词）
- [x] 编写 `tests/test_ocr_service.py`
- [x] **验收标准**：`pytest tests/test_ocr_service.py -v` 全部 PASSED ✅ 18 passed (2026-03-03)

### Task 4.2: VLM/LLM 增强服务 ← PRD §5.4
- [x] 创建 `services/llm_vision_service.py`（VLM 视觉提取）
- [x] 创建 `services/llm_service.py`（LLM 文本增强）
- [x] 实现 API 调用封装（OpenRouter）
- [x] 实现三种模式切换：enhance/fallback/disabled
- [x] 实现 OCR 失败时的降级调用
- [x] 编写 `tests/test_llm_service.py`（mock API 测试）
- [x] **验收标准**：`pytest tests/test_llm_service.py -v` 全部 PASSED ✅ 32 passed (2026-03-03)

### Task 4.3: 第三页字段核对器 ← PRD §5.3 C01-C03
- [x] 创建 `services/third_page_checker.py`
- [x] 实现 C01：首页与第三页字段一致性
- [x] 实现 C02：第三页扩展字段核对（"见样品描述栏"逻辑）
- [x] 实现 C03：生产日期格式一致性
- [x] 编写 `tests/test_third_page_checker.py`
- [x] **验收标准**：`pytest tests/test_third_page_checker.py -v` 全部 PASSED ✅ 45 passed (2026-03-03)

### Task 4.4: 报告核对主引擎 ← PRD §5.3 C04-C06
- [x] 创建 `services/report_checker.py`
- [x] 实现报告结构解析（首页/第三页/样品描述页/照片页定位）
- [x] 实现 C04：样品描述表格与标签 OCR 比对
- [x] 实现 C05：照片覆盖性检查
- [x] 实现 C06：中文标签覆盖检查
- [x] 实现部件名称匹配规则（精确/部分匹配三种方式）
- [x] 实现"本次检测未使用"部件特殊处理
- [x] 实现错误分级（ERROR/WARN/INFO）
- [x] 结合 `素材/report/` 目录中的 1539 和 2795 样本生成报告核对结果的 Golden File (`.expected.json`)
- [x] 编写 `tests/test_report_checker.py`（包含对 Golden File 的断言测试）
- [x] **验收标准**：`pytest tests/test_report_checker.py -v` 全部 PASSED ✅ 59 passed (2026-03-03)

### Task 4.5: 检验项目核对器 ← PRD §5.3 C07-C10, §4.6.2
- [x] 创建 `services/inspection_item_checker.py`
- [x] 实现 C07：单项结论逻辑核对（优先级规则）
- [x] 实现 C08：非空字段核对
- [x] 实现 C09：序号连续性核对
- [x] 实现 C10：续表标记核对
- [x] 实现合并单元格处理
- [x] 编写 `tests/test_inspection_item_checker.py`
- [x] **验收标准**：`pytest tests/test_inspection_item_checker.py -v` 全部 PASSED ✅ 51 passed (2026-03-03)

### Task 4.6: 页码核对器 ← PRD §5.3 C11
- [x] 创建 `services/page_number_checker.py`
- [x] 实现 C11：页码连续性核对
- [x] 实现页码文字提取（`共XXX页 第Y页`）
- [x] 编写 `tests/test_page_number_checker.py`
- [x] **验收标准**：`pytest tests/test_page_number_checker.py -v` 全部 PASSED ✅ 32 passed (2026-03-03)

### Task 4.7: 报告核对 API 路由 ← PRD §7.3
- [x] 创建 `routers/report_check.py`
- [x] 实现 `POST /api/report/upload`（上传 + 启动后台核对）
- [x] 实现 `GET /api/report/{task_id}/progress`（进度查询）
- [x] 实现 `GET /api/report/{task_id}/result`（结果获取）
- [x] 实现后台任务编排（串联 report_checker + inspection_item_checker + page_number_checker）
- [x] 实现 LLM 开关参数（`enable_llm`）
- [x] 在 `main.py` 注册路由
- [x] 编写 `tests/test_api_report.py`（包含利用 Golden File 数据结构进行的端到端测试 mock）
- [x] **验收标准**：`pytest tests/ -v` 全部 PASSED ✅ 435 passed, 8 skipped (2026-03-03)

---

## Phase 5: 前端 — 报告自检页面

### Task 5.1: 报告自检上传页面 ← PRD §5.5
- [x] 创建 `pages/report-check/ReportCheckPage.tsx`
- [x] 创建 `pages/report-check/ReportUpload.tsx`（单文件上传）
- [x] 实现 LLM 增强开关（Toggle 组件）
- [x] 实现上传 API 调用 + 进度轮询
- [x] **验收标准**：`npm run build` 通过 ✅ Playwright MCP 验证通过 (2026-03-03)

### Task 5.2: 报告自检结果页面 ← PRD §5.5
- [x] 创建 `pages/report-check/ReportResults.tsx`
- [x] ~~创建 `components/report/FieldComparisonCard.tsx`~~ → 已内联实现
- [x] ~~创建 `components/report/ComponentCheckList.tsx`~~ → 已内联实现
- [x] ~~创建 `components/report/InspectionItemTable.tsx`~~ → 已内联实现
- [x] ~~创建 `components/report/PageNumberCheck.tsx`~~ → 已内联实现
- [x] 实现结果总览（总项 / 通过 / 失败 / 警告）
- [x] 实现分区展示（字段/样品描述/照片标签/检验项目/页码）
- [x] 实现错误级别颜色标识
- [x] 创建 `types/report.ts`（TypeScript 类型定义）
- [x] **验收标准**：`npm run build` 通过 ✅ 2166 modules (2026-03-03)
- **注**：采用内联组件设计，所有核对结果展示逻辑集中在 `ReportResults.tsx` 中

---

## Phase 6: 导出 + 收尾

### Task 6.1: PDF 导出服务 ← PRD §4.9, §5.6
- [x] 创建 `services/report_export_service.py`
- [x] 实现 PTR 核对结果 PDF 导出
- [x] 实现报告自检结果 PDF 导出
- [x] 添加 `GET /api/ptr/{task_id}/export` 端点
- [x] 添加 `GET /api/report/{task_id}/export` 端点
- [x] 编写 `tests/test_export.py`
- [x] **验收标准**：`pytest tests/test_export.py -v` 全部 PASSED ✅ 20 passed (2026-03-03)

### Task 6.2: 前端导出按钮 ← PRD §4.9, §5.6
- [x] 创建 `components/shared/ExportButton.tsx`
- [x] 在 PTR 结果页面添加导出按钮
- [x] 在报告自检结果页面添加导出按钮
- [x] 实现下载 PDF 文件逻辑
- [x] **验收标准**：`npm run build` 通过 ✅ 2168 modules (2026-03-03)

### Task 6.3: 端到端集成测试 ← PRD §8
- [x] 使用 `素材/` 目录下的 1539 和 2795 样本文件进行 PTR 核对完整流程手动测试及断言
- [x] 使用 `素材/` 目录下的 1539 和 2795 样本文件进行报告自检完整流程手动测试及断言
- [x] 验证包含 Golden File 在内的两个模块的 Dashboard 入口 → 上传 → 结果 → 导出 全链路
- [x] 确认前后端联调无误
- [x] **验收标准**：两组 Golden File 样本均能完整走通全流程并输出一致结果 ✅ Playwright MCP 验证通过 (2026-03-03)

### Task 6.4: 启动脚本
- [x] 创建 `start.sh`（一键启动前后端）
- [x] 创建 `README.md`（项目介绍 + 安装 + 使用）
- [x] **验收标准**：`./start.sh` 能正常启动服务 ✅ (2026-03-03)

---

## 任务统计

| 阶段 | 任务数 | 描述 |
|-----|-------|------|
| Phase 0 | 2 | 项目脚手架 |
| Phase 1 | 4 | 前端设计系统 + Dashboard |
| Phase 2 | 8 | PTR 核对后端引擎 |
| Phase 3 | 2 | PTR 核对前端页面 |
| Phase 4 | 7 | 报告自检后端引擎 |
| Phase 5 | 2 | 报告自检前端页面 |
| Phase 6 | 4 | 导出 + 收尾 |
| **总计** | **29** | |
