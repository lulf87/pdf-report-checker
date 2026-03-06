# 多维度表格重构执行文档（供 Codex 按文档修改）

> 日期：2026-03-06  
> 状态：待实施  
> 建议放置路径：`docs/plans/2026-03-06-multidimensional-table-refactor.md`

---

## 0. 给 Codex 的执行要求

1. 先阅读本文件，再阅读 `CLAUDE.md` 和 `docs/tasks.md`。
2. 严格按 **Phase 0 → Phase 4** 的顺序执行，**不得跳阶段**。
3. 每完成一个 Phase，必须运行本文件指定的测试；测试不通过，不得进入下一阶段。
4. 这次改造的核心目标是：**在不破坏现有外部行为的前提下，让多维度表格的结构信息在解析链路中尽量保留下来**。
5. **第一阶段不要引入新的第三方表格引擎依赖**。先用现有 `PyMuPDF + 规则 + 可选增强` 完成结构保真改造。
6. **不要一上来重写 `table_comparator.py`**。先把表格结构保住，再改比较逻辑。
7. **不要删除兼容字段**：在所有调用方迁移完成前，必须保留 `PTRTable.headers`、`PTRTable.rows` 以及现有结果结构。
8. 本次改造只聚焦后端；前端不做结构级改造。
9. 对真实业务样本的验证必须遵循项目既有测试铁律：后端用 `pytest`，Golden File 必须回归验证。
10. 每个 Phase 完成后，把本文件中对应任务标记为 `[x]`；未完成保持 `[ ]`。

---

## 1. 问题定义

当前系统在处理普通平面表格时已经可以工作，但在以下场景中容易出错：

1. **多行表头**：例如顶层是“心房 / 心室”，下一层是“常规数值 / 标准设置”。
2. **首列或前几列存在 rowspan**：参数名、项目组名、型号适用范围经常通过合并单元格向下延续。
3. **跨页续表**：第二页可能重复表头，也可能只出现正文，导致续表合并不稳定。
4. **表头和表体混淆**：有些表的第一行不是完整 header，而是部分 caption + group header。
5. **过早扁平化**：一旦在解析早期把表格压成 `headers + rows`，后面只能靠 heuristics 补救，稳定性会越来越差。

### 本次改造要解决的核心问题

不是“再加几条补丁规则”，而是要把现有链路从：

```text
PDFParser -> TableData(近似平面) -> PTRTable(headers/rows) -> Comparator
```

调整为：

```text
PDFParser -> Raw TableData -> TableNormalizer -> CanonicalTable -> 业务适配器 -> Comparator
```

即：**先保结构，再做业务映射，再做比较**。

---

## 2. 当前实现中的主要结构性缺口

### 2.1 解析阶段已经存在过早扁平化

当前代码链路里，问题主要集中在以下几点：

1. `CellData` 已经有 `row_span` / `col_span` 字段，但实际 parser 侧并没有把 span 信息稳定打通。
2. `pdf_parser.py` 在 `_extract_tables()` 中已经把表格拆成 `CellData`，但目前主要保存的是 `text / row / col / bbox` 这类平面信息。
3. `ptr_extractor.py` 在 `_convert_to_ptr_table()` 中会直接把 `TableData` 变成 `PTRTable(headers, rows)`。
4. `ptr_extractor.py` 的 `_merge_continuation_tables()` 当前是在 **平面 PTRTable** 层做续表合并。
5. `report_extractor.py` 里的 `_has_merged_cells()` 依赖 `CellData.is_merged()`，但如果上游没有把 span 填出来，这条链天然不稳。
6. `table_comparator.py` 当前主要围绕平面列索引和 coverage 文本匹配工作，对多级列语义感知不够。

### 2.2 直接后果

这会直接导致：

1. 多行表头的父子关系丢失。
2. rowspan 只剩“空白格”，后续只能猜是否应该向下继承。
3. 跨页重复表头和真正正文不容易区分。
4. 比较逻辑只能依赖“第几列是什么”，而不是“这个列路径代表什么”。
5. Debug 困难：因为错误发生在前面，但症状常常在 comparator 才出现。

---

## 3. 改造目标

### 3.1 必须达成

1. **保留表格结构信息**：至少保留 header rows、body rows、cell 坐标、rowspan/colspan（原生或推断）、跨页来源信息。
2. **建立统一中间层**：新增 `CanonicalTable` 作为标准中间表示。
3. **兼容旧业务模型**：现有 `PTRTable.headers / rows` 暂时不删，由 `CanonicalTable` 适配生成。
4. **多级表头可还原为列路径**：例如 `心房 / 常规数值`。
5. **首列 rowspan 可控 fill-down**：仅对维度列做受控继承，不允许把数值列也盲目向下复制。
6. **续表合并基于结构而不是只靠 caption**。
7. **比较逻辑从“按列索引”逐步过渡到“按列语义”**。
8. **新增单元测试 + Golden 回归**，保障真实样本不回退。

### 3.2 本轮明确不做

1. 不重写前端。
2. 不在第一阶段引入新表格解析依赖。
3. 不追求一次性支持所有极端版式。
4. 不修改已有 API 输出结构到前端不可兼容的程度。
5. 不把所有逻辑都替换成 LLM/VLM 黑盒；结构恢复仍然以规则和可解释中间层为主。

### 3.3 第一轮 MVP 的覆盖范围

本轮改造必须至少稳定支持以下三类复杂表：

1. **双层/三层表头**。
2. **左侧维度列 rowspan 延续**。
3. **跨页续表（重复表头 or 缺失表号）**。

---

## 4. 目标数据流

### 4.1 新的数据流

```text
PDF / OCR 结果
    ↓
PDFParser / OCR Parser
    ↓
Raw TableData（尽量保留原始网格、bbox、页码、caption）
    ↓
TableNormalizer
    ↓
CanonicalTable
    ├── 生成 legacy PTRTable(headers/rows)
    ├── 生成 ParameterRecord / RowRecord
    └── 为 ReportExtractor / Comparator 提供结构化语义
```

### 4.2 关键原则

1. **原始数据不覆盖**：任何推断（例如 fill-down）都必须保留 provenance。
2. **推断有边界**：维度列可以受控继承；值列不可随意继承。
3. **先结构，后语义，最后比较**。
4. **低置信度要降级**：如果结构恢复置信度太低，可以回退 legacy 行为，但必须留下 diagnostics。

---

## 5. 数据模型设计

## 5.1 新增 `backend/app/models/table_models.py`

新增一个独立模型文件，避免把所有结构信息都塞到现有 `PTRTable` 中。

建议新增以下 dataclass：

```python
from dataclasses import dataclass, field
from typing import Literal
from app.models.common_models import BoundingBox

CellSource = Literal["native", "inferred", "vlm"]
CellRole = Literal["header", "body", "stub", "value", "unknown"]
ColumnRole = Literal[
    "parameter", "model", "group", "value", "default", "tolerance", "remark", "unknown"
]


@dataclass
class CanonicalCell:
    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    bbox: BoundingBox | None = None
    is_header: bool = False
    source: CellSource = "native"
    propagated_from: tuple[int, int] | None = None
    confidence: float | None = None


@dataclass
class ColumnPath:
    leaf_col: int
    labels: list[str] = field(default_factory=list)
    role: ColumnRole = "unknown"

    @property
    def key(self) -> str:
        return " / ".join([x for x in self.labels if x])


@dataclass
class CanonicalTableDiagnostics:
    header_row_count: int = 0
    inferred_rowspans: int = 0
    inferred_colspans: int = 0
    repeated_header_removed: int = 0
    continuation_merged: bool = False
    structure_confidence: float = 1.0
    notes: list[str] = field(default_factory=list)


@dataclass
class CanonicalTable:
    page_start: int
    page_end: int
    caption: str = ""
    table_number: int | None = None
    n_rows: int = 0
    n_cols: int = 0
    cells: list[CanonicalCell] = field(default_factory=list)
    header_rows: list[int] = field(default_factory=list)
    body_rows: list[int] = field(default_factory=list)
    column_paths: list[ColumnPath] = field(default_factory=list)
    diagnostics: CanonicalTableDiagnostics = field(default_factory=CanonicalTableDiagnostics)
    metadata: dict[str, object] = field(default_factory=dict)
```

### 5.2 新增业务适配记录（建议）

为了减少 `table_comparator.py` 对原始二维网格的直接依赖，建议新增：

```python
@dataclass
class ParameterRecord:
    parameter_name: str
    dimensions: dict[str, str] = field(default_factory=dict)
    values: dict[str, str] = field(default_factory=dict)
    source_rows: list[int] = field(default_factory=list)
```

用途：

1. `parameter_name`：参数名，例如“脉冲宽度(ms)”
2. `dimensions`：型号/适用范围/分组等维度
3. `values`：由 `column_paths` 产生的语义键值，例如 `心房 / 常规数值 -> 0.1...`
4. `source_rows`：便于调试和回溯

### 5.3 对现有模型的兼容扩展

#### 5.3.1 `common_models.py`

保留现有 `CellData` / `TableData`，但做**兼容增强**而不是语义重定义。

建议：

```python
@dataclass
class TableData:
    rows: list[list[CellData]] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    bbox: BoundingBox | None = None
    page: int = 1
    caption: str = ""
    table_number: int | None = None

    # 新增
    raw_rows: list[list[CellData]] = field(default_factory=list)
    source_engine: str = "pymupdf"
    extraction_meta: dict[str, object] = field(default_factory=dict)
```

说明：

1. `rows` 保持现有语义，避免立刻破坏调用方。
2. `raw_rows` 保存 parser 直接产出的网格。
3. `extraction_meta` 保存 header 行数候选、原始 bbox 信息、是否疑似复杂表等。

#### 5.3.2 `PTRTable` 兼容增强

在不破坏旧行为的前提下，给 `PTRTable` 增加可选结构字段：

```python
header_rows: list[list[str]] = field(default_factory=list)
column_paths: list[list[str]] = field(default_factory=list)
structure_confidence: float | None = None
metadata: dict[str, object] = field(default_factory=dict)
```

注意：

- `headers` 仍然保留，建议由 `column_paths` 展平生成，例如：
  - `参数`
  - `心房 / 常规数值`
  - `心房 / 标准设置`
- 旧代码仍可只看 `headers/rows`。
- 新代码优先看 `column_paths`。

---

## 6. 规范化算法（TableNormalizer）

新增：`backend/app/services/table_normalizer.py`

建议提供主入口：

```python
class TableNormalizer:
    def normalize(self, table_data: TableData) -> CanonicalTable:
        ...
```

## 6.1 处理步骤概览

```text
raw TableData
    ↓
构建 dense grid
    ↓
识别 header rows / body rows
    ↓
恢复或推断 rowspan / colspan
    ↓
生成 column_paths
    ↓
对维度列做 fill-down
    ↓
生成 CanonicalTable + diagnostics
    ↓
生成 legacy PTRTable / ParameterRecord
```

### 6.2 dense grid 构建

要求：

1. 优先使用 parser 已给出的 `CellData` 网格。
2. 每个位置必须有稳定 `(row, col)`。
3. 原始空字符串要保留，不要在第一步就删除空格。
4. 如果 parser 能拿到原生 span，则直接写入 `row_span / col_span`。
5. 如果 parser 拿不到 span，先保持 `1x1`，后续在 normalizer 阶段推断。

### 6.3 header rows 识别

建议策略：

1. 只在表格前 `1~4` 行中寻找 header 区域。
2. 从顶部开始，连续判断某行是否更像 header：
   - 包含 header 关键词：`参数`、`型号`、`常规数值`、`标准设置`、`允许误差`、`项目`、`备注`、`结论` 等。
   - 数值占比低。
   - 出现明显“上层分组 + 下层子列”模式。
   - 行内存在空白占位，但列布局稳定。
3. 一旦遇到首个明显数据行，就停止扩展 header 区域。
4. header 行数允许为 `0/1/2/3/4`，但第一轮重点支持 `1~3`。

### 6.4 列路径生成（column_paths）

对于每个叶子列，自上而下收集该列在所有 header 行上的有效标签：

示例：

```text
Row 0: 参数 | 心房 |      | 心室 |      
Row 1:      | 常规数值 | 标准设置 | 常规数值 | 标准设置
```

应生成：

```text
col0 -> [参数]
col1 -> [心房, 常规数值]
col2 -> [心房, 标准设置]
col3 -> [心室, 常规数值]
col4 -> [心室, 标准设置]
```

规则：

1. 空 label 不进入最终路径。
2. 同一层连续空白列，可继承最近的左侧父标签，但要在 diagnostics 记录为推断。
3. `column_paths` 的 `leaf_col` 必须和最终 body 列一一对应。
4. 允许最终生成的 `headers` 直接由 `column_paths.key` 展平得到。

### 6.5 rowspan / fill-down 规则

这是本次改造的关键点。

#### 只允许对“维度列”做受控 fill-down

维度列包括：

1. 参数列
2. 型号列
3. 左侧分组列
4. 其他明确作为分类维度的列

**禁止**对以下列盲目 fill-down：

1. 常规数值
2. 标准设置
3. 允许误差
4. 备注 / 说明类值列

#### fill-down 的触发条件

某个 body row 的维度列为空，且满足以下条件时，才允许继承上一条非空值：

1. 当前列被识别为维度列。
2. 当前行不是新的 header / footer / 小节标题。
3. 同一行的右侧值列存在有效内容。
4. 上一个非空值所在行与当前行之间没有新的同级维度起点。

#### provenance 要求

任何被继承出来的单元格必须标记：

- `source = "inferred"`
- `propagated_from = (source_row, source_col)`

这样后续 debug 才知道它不是原始文本。

### 6.6 colspan / 父列标签传播

如果 header 行存在“父列 + 多个子列”的情况，且父列下面连续若干列为空白，需要把父标签横向传播给这些子列。

规则：

1. 只在 header 区域做横向传播。
2. 传播范围由相邻空白列和下一层非空子列共同约束。
3. 传播行为要记录在 diagnostics 中。

### 6.7 续表合并规则

续表合并不能只靠表号或 caption，必须引入结构指纹。

建议结构指纹包含：

1. 展平后的 `headers`
2. `column_paths`
3. 列数
4. 维度列角色分布

#### 允许合并的条件

后表满足以下多数条件时，可判定为前表续表：

1. 页面紧邻或近邻。
2. 新表出现在页面上部。
3. caption 缺失或表号缺失。
4. `column_paths` 与前表高度相似。
5. 首行是重复 header，或者首行是明显 body continuation。

#### 合并动作

1. 去掉后续表的重复 header 行。
2. body rows 追加到前表。
3. `page_end` 更新。
4. diagnostics 标记 `continuation_merged=True`。

### 6.8 置信度与降级

每张 canonical table 需要一个 `structure_confidence`。

建议考虑：

1. header 检测是否稳定
2. 推断次数是否过多
3. 列路径是否完整
4. 续表合并是否有冲突
5. 维度列 fill-down 是否过多

当 `structure_confidence` 太低时：

1. 可以保留 legacy 行为作为 fallback。
2. 但必须在 `metadata` 或 diagnostics 记录 `needs_manual_review=True`。
3. 不能静默地做大量高风险推断。

---

## 7. 模块修改说明

## 7.1 `backend/app/services/pdf_parser.py`

### 必改项

1. `_extract_tables()` 输出的 `TableData` 必须尽量保留原始网格。
2. 构造 `CellData` 时，如果当前 PyMuPDF 版本能拿到 span 信息，就直接填 `row_span / col_span`。
3. 如果拿不到原生 span，也要保留足够的原始信息给 normalizer 推断：
   - 原始 cell matrix
   - bbox
   - header names
   - row_count / col_count
4. `TableData.raw_rows` 必须填充。
5. 对疑似复杂表打标记，例如：
   - header 超过 1 行候选
   - 空白占位较多
   - 列数稳定但 header 不完整
   - 首列空白延续明显

### 禁止项

1. 不要在 parser 内直接做 aggressive fill-down。
2. 不要把复杂结构直接压成最终业务语义。
3. parser 只负责“保真抽取”，不负责最终业务解释。

## 7.2 `backend/app/services/table_normalizer.py`（新增）

### 必须实现的方法

```python
class TableNormalizer:
    def normalize(self, table_data: TableData) -> CanonicalTable: ...
    def to_legacy_headers(self, canonical: CanonicalTable) -> list[str]: ...
    def to_legacy_rows(self, canonical: CanonicalTable) -> list[list[str]]: ...
    def to_parameter_records(self, canonical: CanonicalTable) -> list[ParameterRecord]: ...
```

### 推荐拆分的内部方法

```python
_detect_header_rows(...)
_infer_column_paths(...)
_infer_header_colspans(...)
_fill_down_dimension_cells(...)
_infer_column_roles(...)
_remove_repeated_header_rows(...)
_build_parameter_records(...)
_compute_structure_confidence(...)
```

## 7.3 `backend/app/services/ptr_extractor.py`

### 当前问题

`_convert_to_ptr_table()` 现在基本是把 `TableData` 直接转成 `PTRTable`，这一步需要改为：

```text
TableData -> CanonicalTable -> PTRTable
```

### 必改项

1. 在 extractor 初始化或内部创建 `TableNormalizer`。
2. `_convert_to_ptr_table()` 先调用 `normalizer.normalize(table_data)`。
3. `PTRTable.headers` 由 `canonical.column_paths` 展平生成。
4. `PTRTable.rows` 由 canonical body rows 生成。
5. `PTRTable` 额外挂上：
   - `header_rows`
   - `column_paths`
   - `structure_confidence`
   - `metadata`
6. `_merge_continuation_tables()` 的判断条件要升级：
   - 不能只看 `caption` / `table_number`
   - 需要结合 `column_paths` 与页位置

### 输出兼容要求

旧调用方如果只读：

- `table.headers`
- `table.rows`
- `table.page`
- `table.page_end`

应该还能继续工作。

## 7.4 `backend/app/services/report_extractor.py`

本次改造目标不是重写报告解析，但要把合并单元格逻辑建立在更可靠的结构上。

### 必改项

1. 如果报告表格来自 `TableData`，在进入 InspectionItem 构造前先经过结构化 fill-down。
2. `_has_merged_cells()` 不应再只是“看上游有没有填 span”，而应能利用 normalizer 的结构推断结果。
3. 对 C08 非空项的逻辑要符合业务规范：
   - 合并区域首行值作为该区域值
   - 首行为空则整个区域视为空
4. 需要保留“该值是否来自 merge 推断”的 provenance，方便解释错误来源。

## 7.5 `backend/app/services/table_comparator.py`

### 当前问题

现有比较逻辑对 flat table 已经做了不少优化，但多维表的关键问题是：

- 参数列不一定只是一列索引。
- 值列不一定只有简单 `headers[2:]`。
- 比较目标应该是“参数 + 维度 + 值路径”，而不是只有“第 N 列”。

### 改造方向

#### 第一阶段：兼容增强，不推翻现有逻辑

1. 保留现有 coverage comparison 主体。
2. 新增“优先从 `column_paths` 推断角色”的逻辑。
3. 当 `column_paths` 存在时，按角色选择：
   - parameter 列
   - model / group 维度列
   - value / default / tolerance 值列
4. 当 `column_paths` 不存在或置信度过低时，回退原先逻辑。

#### 第二阶段：引入 `ParameterRecord`

1. `_compare_table_parameters()` 改为优先读取 `ParameterRecord`。
2. 每条记录按：
   - `parameter_name`
   - `dimensions`
   - `values`
   去和报告文本做 coverage。
3. 不要把多维表重新压回“只有一个 param_col_idx”的旧模型再比较。

### 列角色推断建议

基于 `column_paths.key` 判断：

- 包含 `参数` / `项目` / `检验项目` → `parameter`
- 包含 `型号` / `适用型号` / `机型` → `model`
- 包含 `分组` / `类别` / `腔室` → `group`
- 包含 `常规数值` / `数值` / `范围` → `value`
- 包含 `标准设置` / `默认设置` → `default`
- 包含 `允许误差` / `误差` / `偏差` → `tolerance`
- 包含 `备注` / `说明` → `remark`

如果多列同时命中，优先级：

```text
parameter > model/group > value/default/tolerance > remark > unknown
```

---

## 8. 分阶段任务清单

## Phase 0：先补测试，再动代码

### 目标

先把多维表失败样式固定下来，避免“边改边飘”。

### 任务

- [x] 新增 `backend/tests/test_table_normalizer.py`
- [x] 新增 synthetic fixture builder，方便直接构造复杂表网格
- [x] 为以下 archetype 各写至少 1 个测试：
  - [x] 双层表头
  - [x] 三层表头
  - [x] 首列 rowspan / fill-down
  - [x] 跨页重复表头续表
  - [x] 续表无表号但结构相同
- [x] 在 `backend/tests/test_table_comparator.py` 中新增基于 `column_paths` / `ParameterRecord` 的比较用例
- [x] 新增 `backend/tests/test_report_extractor_merged_cells.py`，覆盖 C08 合并单元格场景
- [x] 准备至少 1 组真实样本 Golden 回归入口

### 验收标准

- [x] 新测试能在当前代码上暴露问题（允许先 fail）
- [x] 测试命名清晰，覆盖目标结构性问题

---

## Phase 1：引入 CanonicalTable 与 TableNormalizer

### 目标

先建立中间层，但暂不大规模接管业务流程。

### 任务

- [x] 新增 `backend/app/models/table_models.py`
- [x] 新增 `backend/app/services/table_normalizer.py`
- [x] 为 `TableData` 增加 `raw_rows / source_engine / extraction_meta`
- [x] 完成 header rows 检测
- [x] 完成 column_paths 生成
- [x] 完成维度列 fill-down
- [x] 完成 diagnostics 与 structure_confidence
- [x] 输出 legacy `headers/rows` 适配方法

### 验收标准

- [x] `test_table_normalizer.py` 通过
- [x] 不修改 `PTRExtractor / Comparator` 时，不影响现有测试

---

## Phase 2：接管 PTR 提取与续表合并

### 目标

让 PTR 侧先用上 CanonicalTable。

### 任务

- [x] 修改 `ptr_extractor.py`，在 `_convert_to_ptr_table()` 中接入 `TableNormalizer`
- [x] `PTRTable.headers` 改由 `column_paths` 展平生成
- [x] `PTRTable.rows` 改由 canonical body rows 生成
- [x] 为 `PTRTable` 增加 `header_rows / column_paths / structure_confidence / metadata`
- [x] 升级 `_merge_continuation_tables()`：按结构指纹 + 页位置做续表合并
- [x] 对低置信度表保留 fallback 行为

### 验收标准

- [x] 旧的 PTR 提取测试全部通过
- [x] 新增的多维表 PTR 测试通过
- [x] 真实样本 Golden 不出现明显回退

---

## Phase 3：接管报告表格中的 merge 语义

### 目标

让报告侧的合并单元格逻辑基于结构化结果，不再纯依赖原始 span。

### 任务

- [x] 在报告表格进入 InspectionItem 构造前做受控 fill-down
- [x] `_has_merged_cells()` 能识别原生 merge 与推断 merge
- [x] C08 非空规则严格符合规范
- [x] 为 merge 推断值保留 provenance

### 验收标准

- [x] `test_report_extractor_merged_cells.py` 通过
- [x] C08 / C09 / C10 相关已有测试不回退

---

## Phase 4：让 Comparator 优先吃结构化语义

### 目标

比较阶段不再只依赖平面列索引。

### 任务

- [x] 在 `table_comparator.py` 中增加列角色推断
- [x] 当 `PTRTable.column_paths` 可用时，优先按语义列处理
- [x] 引入 `ParameterRecord` 或等价中间表示
- [x] `_compare_table_parameters()` 以 `parameter_name + dimensions + values` 作为主要比较对象
- [x] 保留对旧 flat tables 的回退路径
- [x] 完善日志，输出当前使用的是 `legacy` 还是 `canonical` 比较路径

### 验收标准

- [x] `backend/tests/test_table_comparator.py` 通过
- [x] 复杂参数表 coverage 匹配稳定性明显提升
- [x] 平面表无明显回退

---

## 9. 测试要求

## 9.1 必新增的单元测试文件

1. `backend/tests/test_table_normalizer.py`
2. `backend/tests/test_report_extractor_merged_cells.py`
3. `backend/tests/test_ptr_extractor_multidim.py`（建议）
4. `backend/tests/test_table_comparator.py`（扩展已有文件）

## 9.2 必测 archetype

### A. 双层表头

输入：

```text
参数 | 心房 |      | 心室 |      
     | 常规数值 | 标准设置 | 常规数值 | 标准设置
```

断言：

- `header_row_count == 2`
- 生成正确 `column_paths`
- 展平 headers 正确

### B. 首列 rowspan

输入：

```text
脉冲宽度(ms) | 全部型号 | 0.1... | 0.4
            | Edora 8  | 0.2... | 0.5
```

断言：

- 第二行参数列被受控继承
- `propagated_from` 正确
- 数值列不得被误继承

### C. 续表重复表头

输入：

- page 10: 表1 正文到一半
- page 11: 无新表号，顶部重复 header，继续正文

断言：

- 两表合并为 1 张 canonical table
- 重复 header 被移除
- `page_end == 11`

### D. 报告表 merge 非空逻辑（C08）

断言：

- 合并区域首行非空 → 后续空白行视为继承值
- 合并区域首行为空 → 区域内逐行判空报错

### E. Comparator 多维参数对齐

断言：

- 同一参数在多个列路径下能被正确比对
- 不因 OCR 噪声把无关参数行误拉入

## 9.3 必跑命令

后端阶段每个 Phase 结束后至少执行：

```bash
cd backend
source .venv/bin/activate
pytest tests/test_table_normalizer.py -v
pytest tests/test_table_comparator.py -v
pytest tests/ -v
```

如果接入真实样本 Golden，还必须执行对应 Golden 测试。

---

## 10. 验收标准（Definition of Done）

满足以下全部条件，才可认为本次改造完成：

1. 多维表的 `header_rows`、`column_paths`、受控 fill-down 能稳定产出。
2. `PTRTable.headers / rows` 仍兼容旧调用方。
3. 续表合并明显比当前稳定，特别是“缺表号 + 重复表头”场景。
4. 报告表的合并单元格逻辑符合 C08 业务规则。
5. `table_comparator.py` 能优先使用结构化语义而不是只靠列索引。
6. 现有 flat table 行为无明显回退。
7. 所有新增测试通过。
8. 既有 pytest 通过。
9. 真实样本 Golden 通过，或有明确、可审计的 expected 更新说明。

---

## 11. 禁止事项

1. **禁止**一开始就删除 `PTRTable.headers / rows`。
2. **禁止**把所有复杂逻辑继续堆到 comparator 末端补救。
3. **禁止**对值列做无边界 fill-down。
4. **禁止**在没有 provenance 的情况下静默推断大量单元格内容。
5. **禁止**只改 synthetic test，不跑真实样本 Golden。
6. **禁止**只凭 build / import 成功就标记完成，必须跑 pytest。
7. **禁止**为了通过测试而把复杂表重新降级成纯字符串拼接。

---

## 12. 建议的调试输出

为了后续排查方便，建议增加以下 debug 日志：

1. `table_normalizer`: header 行数、column_paths、推断次数、structure_confidence
2. `ptr_extractor`: 续表合并前后表数量、匹配到的结构指纹
3. `report_extractor`: 哪些单元格来自 merge 推断
4. `table_comparator`: 当前采用 `legacy` 还是 `canonical` 路径比较

日志级别建议：

- `info`: 续表合并、canonical/legacy 分支选择
- `debug`: 列角色推断、fill-down 明细、header 推断明细
- `warning`: 低置信度结构、冲突 merge、疑似人工复核场景

---

## 13. Appendix A：推荐的最小 synthetic fixture 形式

建议在测试里提供一个 helper，减少重复样板代码：

```python
def build_table(
    rows: list[list[str]],
    page: int = 1,
    caption: str = "",
    table_number: int | None = None,
) -> TableData:
    ...
```

对于需要测试原生 span 的用例，再提供：

```python
def build_cell(
    text: str,
    row: int,
    col: int,
    row_span: int = 1,
    col_span: int = 1,
) -> CellData:
    ...
```

这样可以把大部分复杂结构测试直接写成可读网格。

---

## 14. Appendix B：给 Codex 的一句话总原则

**不要再把复杂表格当成普通二维字符串数组处理。先保住结构，再做语义映射，再做比对。**
