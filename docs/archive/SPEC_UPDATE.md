# 报告核对工具 - 规格更新说明

> 本文档记录实际实现与原 SPEC.md 的差异、新增功能及实现细节。
> 生成时间: 2026年2月11日

---

## 一、已实现功能概览

### 1.1 核心核对功能 ✅

| 功能模块 | 实现状态 | 说明 |
|---------|---------|------|
| PDF 文件解析 | ✅ 已实现 | PyMuPDF 提取页面、表格、图片 |
| DOCX 文件支持 | ✅ 已实现 | 自动转换为 PDF 后解析 |
| 首页三字段提取 | ✅ 已实现 | 委托方、样品名称、型号规格 |
| 第三页表格提取 | ✅ 已实现 | 页眉锚点定位 "检验报告首页" |
| 样品描述表格提取 | ✅ 已实现 | 支持跨页表格合并 |
| 照片页识别 | ✅ 已实现 | 页眉锚点定位 "检验报告照片页" |
| 中文标签 OCR | ✅ 已实现 | PaddleOCR + LLM 增强 |
| 字段一致性比对 | ✅ 已实现 | 严格一致 + /与空白等价 |
| 照片覆盖性检查 | ✅ 已实现 | 每个部件需有照片说明 |
| 标签覆盖性检查 | ✅ 已实现 | 每个部件需有中文标签 |

### 1.2 增强功能 ✅

| 功能 | 实现状态 | 说明 |
|-----|---------|------|
| LLM 增强识别 | ✅ 已实现 | OCR 失败时调用大模型 |
| 详细比对日志 | ✅ 已实现 | 记录每个比对步骤 |
| 报告导出 PDF | ✅ 已实现 | 格式化核对报告 |
| 报告导出 Excel | ✅ 已实现 | 多 Sheet 数据表格 |
| 报告导出 JSON | ✅ 已实现 | 完整数据结构 |

---

## 二、与原 SPEC 的差异

### 2.1 页眉锚点规则

**原 SPEC:**
- 第三页：页眉等于 `检验报告首页` / `检验报告首页`
- 第四页起：页眉等于 `检验报告`
- 照片页：页眉等于 `检验报告照片页`

**实际实现:**
- 使用 `_clean_whitespace()` 去除全部空白后匹配
- 第三页匹配：`检验报告首页`（已包含两种变体）
- 照片页匹配：`检验报告照片页`
- 第四页起通过 `"样品描述"` 文本标记定位表格

### 2.2 Caption 解析规则

**原 SPEC:**
- 去除前缀：`^(?:№|No\.?|NO\.?|Number)\s*\d+\s*`
- 去除方位词：`前侧/后侧/左侧/右侧/正面/背面/侧面/俯视/仰视/顶部/底部/局部`
- 去除类别词：`中文标签/中文标签样张/英文标签/原文标签/标签`

**实际实现:**
```python
CAPTION_PATTERNS = {
    'prefix_number': r'^(?:№|No\.?|NO\.?|Number)\s*\d+\s*',
    'any_number_prefix': r'^(?:№|No\.?|NO\.?|Number)?\s*\d+\s*',
    'position_words': r'(?:前侧|后侧|左侧|右侧|左面|右面|正面|背面|侧面|俯视|仰视|顶部|底部|局部)',
    'label_types': r'(?:中文标签样张|中文标签|英文标签|原文标签|标签)'
}
```
- 额外支持：纯数字前缀（如 `25:`）
- 额外支持：`左面/右面` 方位词
- 中文标签识别包含更多变体：
  - `中文标签`
  - `中文标签样张`
  - `中文標籤`
  - `中文标签样本`
  - `中文标签照片`
  - `标签样张`

### 2.3 部件名称匹配规则

**原 SPEC:** 主体名提取后精确匹配

**实际实现:** 支持三种匹配方式
1. **精确匹配**：部件名称完全等于主体名
2. **部分匹配（组件→主体）**：部件名称包含在主体名中，且后面跟着连接词
   - ✅ `心脏脉冲电场消融仪-主机` 匹配 `心脏脉冲电场消融仪-主机及推车`
   - ❌ `心脏脉冲电场消融仪-触摸屏` 不匹配 `心脏脉冲电场消融仪-触摸屏连接线缆`
3. **部分匹配（主体→组件）**：主体名包含在部件名称中，且后面跟着分隔符
   - ✅ `触摸屏连接线缆（30m）` 匹配 `心脏脉冲电场消融仪-触摸屏连接线缆（30m）`

### 2.4 表格列名映射

**实际实现新增同义列名映射:**
```python
COLUMN_SYNONYMS = {
    '部件名称': ['部件名称', '产品名称', '名称'],
    '规格型号': ['规格型号', '型号规格', '型号', '规格'],
    '序列号批号': ['序列号批号', '批号', '序列号', 'SN', 'LOT'],
    '生产日期': ['生产日期', 'MFG', 'MFD'],
    '失效日期': ['失效日期', '有效期至', 'EXP']
}
```

### 2.5 "本次检测未使用" 处理

**实际实现:**
- 检查备注列是否包含 `本次检测未使用`
- 未使用的部件：有照片/标签则检查，没有也不报错
- 状态标记为 `pass` 或 `warning`，不作为失败

---

## 三、新增功能规格

### 3.1 LLM 增强识别

**配置项:**
```python
ENABLE_LLM_COMPARISON: bool = False  # 功能开关
LLM_COMPARISON_MODE: str = "fallback"  # fallback/enhance/disabled
LLM_RETRY_ON_FAILURE: bool = True
LLM_CONFIDENCE_THRESHOLD: float = 0.8
```

**支持的 LLM 提供商:**
- OpenRouter (默认): `google/gemini-2.0-flash-exp`
- Anthropic (Claude)
- OpenAI (GPT)
- Azure OpenAI

**API 使用:**
```bash
POST /api/check/{file_id}?enable_llm=true
```

**界面控制:**
- 文件上传后显示 "LLM 增强识别" 开关
- 开启后本次核对使用 LLM 辅助

### 3.2 详细比对信息

**配置项:**
```bash
POST /api/check/{file_id}?enable_detailed=true
```

**返回内容:**
- `comparison_details`: 每个比对步骤的详细记录
- `matched_photos`: 匹配到的照片列表（含页码、caption）
- `matched_labels`: 匹配到的标签列表（含页码、caption）
- `match_reason`: 匹配/不匹配的原因说明

### 3.3 报告导出

**API 端点:**
```bash
GET /api/export/{file_id}?format=pdf
GET /api/export/{file_id}?format=excel
GET /api/export/{file_id}?format=json
```

**PDF 报告内容:**
- 文件信息和核对时间
- 核对统计（总部件数、通过/失败/警告数）
- 首页与第三页字段比对表
- 样品描述表格
- 每个部件的详细核对结果：
  - 照片覆盖状态
  - 中文标签覆盖状态
  - 字段比对详情
  - 问题列表
- 问题汇总

**Excel 报告内容:**
- Sheet1: 核对概览
- Sheet2: 部件核对明细
- Sheet3: 问题汇总

---

## 四、技术实现细节

### 4.1 后端服务架构

```
python_backend/
├── main.py                 # FastAPI 入口
├── config.py              # 配置管理（含 LLM 配置）
├── models/
│   └── schemas.py         # Pydantic 数据模型
└── services/
    ├── pdf_parser.py      # PDF 解析服务
    ├── docx_parser.py     # DOCX 转换服务
    ├── ocr_service.py     # OCR 识别服务
    ├── report_checker.py  # 核对引擎核心
    ├── llm_service.py     # LLM 服务
    └── report_export_service.py  # 导出服务
```

### 4.2 前端架构

```
src/
├── main/                  # Electron 主进程
│   ├── main.js           # 主入口
│   └── preload.js        # 预加载脚本
└── renderer/             # React 前端
    ├── src/
    │   ├── App.jsx       # 主应用组件
    │   └── components/
    │       ├── FileUpload.jsx    # 文件上传
    │       └── CheckResult.jsx   # 结果展示
    └── vite.config.js    # Vite 配置
```

### 4.3 API 端点清单

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/health` | GET | 健康检查 |
| `/api/upload` | POST | 上传文件（PDF/DOCX） |
| `/api/parse/{file_id}` | POST | 解析文件 |
| `/api/ocr/{file_id}/page/{page_num}` | POST | 页面 OCR |
| `/api/ocr/{file_id}/image` | POST | 图片 OCR |
| `/api/check/{file_id}` | POST | 执行核对 |
| `/api/result/{file_id}` | GET | 获取结果 |
| `/api/export/{file_id}` | GET | 导出报告 |

### 4.4 OCR 字段提取规则

**已实现正则规则:**

| 字段 | 正则模式 |
|-----|---------|
| 批号 | `(?:批号\|(?:LOT\|Lot\|BATCH\|Batch)\s*(?:No\.?\|#)?)[：:\s]*([^\s]+)` |
| 序列号 | `(?:序列号\|(?:SN\|S/N\|Serial)\s*(?:No\.?\|#)?)[：:\s]*([^\s]+)` |
| 生产日期 | `(?:生产日期\|(?:MFG\|MFD\|Manufacture(?:d)?\s*Date\|Production\s*Date\|Date))[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)` |
| 失效日期 | `(?:失效日期\|有效期至\|(?:EXP\|Expiry\|Expiration)\s*(?:Date)?)[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)` |
| 型号 | `型号` |
| 规格 | `规格` |

---

## 五、数据模型

### 5.1 核对结果 (CheckResult)

```python
class CheckResult:
    success: bool                    # 核对是否成功
    file_id: str                     # 文件ID
    filename: str                    # 文件名
    check_time: str                  # 核对时间
    total_pages: int                 # 总页数
    home_page_fields: Dict           # 首页字段
    third_page_fields: Dict          # 第三页字段
    home_third_comparison: List      # 首页与第三页比对
    sample_description_table: TableData  # 样品描述表格
    component_checks: List           # 部件核对结果
    photo_page_check: Dict           # 照片页检查结果
    errors: List                     # 错误列表
    warnings: List                   # 警告列表
    info: List                       # 信息列表
    total_components: int            # 总部件数
    passed_components: int           # 通过数
    failed_components: int           # 失败数
```

### 5.2 部件核对 (ComponentCheck)

```python
class ComponentCheck:
    component_name: str              # 部件名称
    has_photo: bool                  # 是否有照片
    has_chinese_label: bool          # 是否有中文标签
    field_comparisons: List          # 字段比对列表
    issues: List                     # 问题列表
    status: str                      # 状态: pass/warning/fail
    # 详细模式特有字段:
    comparison_details: Dict         # 详细比对日志
    matched_photos: List             # 匹配的照片
    matched_labels: List             # 匹配的标签
    match_reason: str                # 匹配原因
```

### 5.3 字段比对 (FieldComparison)

```python
class FieldComparison:
    field_name: str                  # 字段名
    table_value: str                 # 表格值
    ocr_value: str                   # OCR识别值
    is_match: bool                   # 是否一致
    issue_type: str                  # 问题类型
```

---

## 六、环境配置

### 6.1 环境变量 (.env)

```bash
# LLM API Keys
OPENROUTER_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=your_endpoint_here

# LLM 配置
LLM_MODEL=google/gemini-2.0-flash-exp
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0

# 功能开关
ENABLE_LLM_POST_PROCESSING=true
ENABLE_LLM_COMPARISON=false
LLM_COMPARISON_MODE=fallback
```

### 6.2 启动方式

**方式1: 双击启动（推荐）**
```bash
./启动报告核对工具.command
```

**方式2: 终端启动**
```bash
./启动工具.sh
```

**方式3: 开发模式**
```bash
npm run dev
```

---

## 七、待实现/优化项

### 7.1 已知限制

| 项目 | 说明 |
|-----|------|
| DOCX 转换 | 依赖外部转换，格式可能有偏差 |
| OCR 准确率 | 复杂标签可能需要 LLM 增强 |
| 表格跨页 | 已支持，但极端情况可能出错 |
| 照片页表格 | 3行表格结构假设，非标准布局可能识别失败 |

### 7.2 建议优化

1. **OCR 后处理**: 添加更多字段提取规则
2. **UI 增强**: 支持结果筛选、搜索
3. **批量处理**: 支持多文件批量核对
4. **历史记录**: 保存和查看历史核对结果
5. **模板配置**: 支持不同报告模板配置

---

## 八、版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| 1.0.0 | 2026-02-11 | 初始版本，核心功能完整实现 |

---

*本文档与实际代码同步维护，如有疑问请参考源代码。*
