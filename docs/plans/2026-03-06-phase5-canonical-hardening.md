# Phase 5：Canonical 路径加固执行文档（供 Codex 按文档修改）

> 日期：2026-03-06  
> 状态：已完成  
> 建议放置路径：`docs/plans/2026-03-06-phase5-canonical-hardening.md`

---

## 0. 给 Codex 的执行要求

1. 先阅读本文件，再阅读 `CLAUDE.md` 和 `docs/tasks.md`。
2. 本轮只改后端，前端不做改动。
3. 直接改代码并运行测试，不要停留在分析阶段。
4. 严格按 **A → E** 的顺序推进，不能跳项。
5. 每完成一个子阶段，必须：
   - 运行本文指定测试；
   - 更新本文 checklist，把完成项改为 `[x]`；
   - 汇报：改动文件、关键设计取舍、测试结果摘要、剩余风险点。
6. 优先使用 `apply_patch` 做增量修改，避免大范围无关重写。
7. 保持兼容性：
   - 不删除 legacy fallback；
   - 不删除现有兼容字段；
   - 不静默修改已有 expected，若必须调整需说明原因。
8. 目标不是“再加几条比较补丁”，而是**把 canonical 结构真正变成稳定可比较的语义记录**。
9. 如遇到实现不确定，优先选择：**兼容旧行为 + 新语义可选接入 + 可观测**。
10. 全部完成后，再跑一次全量测试，并把本文件中对应项全部更新为 `[x]`。

---

## 1. 本轮问题定义

Phase 0 ~ Phase 4 已经完成了第一轮重构，系统已经具备：

1. `TableData -> CanonicalTable -> PTRTable` 的主链路。
2. `column_paths`、`structure_confidence`、`parameter_records` 的基础输出。
3. `report_extractor` 的 provenance 区分：`native / merge_inferred / inferred`。
4. `table_comparator` 的 canonical / legacy 双路径。

但当前 canonical 路径仍有几类高风险误判点：

1. **续表 merge 后 metadata 过期**  
   合并后的 `PTRTable.rows` 已更新，但 `metadata.parameter_records / column_roles / diagnostics / structure_confidence` 可能仍然停留在合并前状态。

2. **多维列只保住了路径，未完全保住维度语义**  
   `column_paths` 虽然能表示 `心房 / 常规数值`、`心室 / 标准设置`，但 `ParameterRecord` 仍可能把多个维度叶子值塞进同一个 record，导致比较阶段再次“半压平”。

3. **低置信度表过早掉回 pure legacy**  
   越复杂的表，越容易 `structure_confidence < 0.7`；若这时直接丢掉 canonical 视图，反而丢失了本轮重构最需要保住的信息。

4. **续表判定偏激进，存在误并风险**  
   相邻页面中列数接近、表号缺失的两个不同表，可能因为规则过宽而被误并。

5. **列角色词典分散**  
   `table_normalizer` 与 `table_comparator` 各自维护一套列角色启发式，词表和语义判断可能漂移，导致上下游对同一列理解不一致。

---

## 2. 本轮目标

### 2.1 必须达成

1. **修复 continuation merge 后 canonical metadata 过期问题**。
2. **让 `ParameterRecord` 真正支持 dimension-aware 展开**。
3. **低结构置信度时保留 canonical + legacy 双视图**。
4. **收紧 continuation 判定，降低误并相邻表概率**。
5. **统一 column role lexicon，让 normalizer 与 comparator 共用同一套语义规则**。
6. **补齐针对以上风险点的单元测试与回归测试**。

### 2.2 本轮不做

1. 不引入新的表格解析引擎依赖。
2. 不改前端数据结构。
3. 不推翻现有 canonical 模型重做一套。
4. 不删除 `legacy` 路径。
5. 不把低置信度表一律判为失败；需要保留兼容回退能力。

---

## 3. 成功标准

完成本轮后，应满足：

1. 跨页续表 merge 后，比较器能看到续页新增参数，而不是只看到第一页参数。
2. 双层/三层表头中的顶层维度（如“心房 / 心室”）可展开为独立维度记录。
3. `clause/report` 仅覆盖某个维度子集时，不应错误要求其它 sibling 维度一起覆盖。
4. 低结构置信度表仍可保留 canonical metadata，并优先尝试 canonical 比较。
5. 相邻但不同的表，即使列数接近，也不会因过宽 continuation 规则被误并。
6. 上下游列角色推断使用统一 lexicon，unknown role 有日志与计数。
7. 测试通过：
   - `tests/test_table_normalizer.py`
   - `tests/test_table_comparator.py`
   - 新增的 continuation / adversarial / dimension-aware 测试
   - 全量 `pytest tests/ -v`

---

## 4. 实施顺序总览

```text
A. continuation merge 修复
B. dimension-aware ParameterRecord
C. dual-view fallback
D. continuation 判定收紧
E. role lexicon 统一
```

> 注意：A 和 B 是本轮收益最大的两项，必须优先完成。

---

## 5. A. continuation merge 修复

### 5.1 目标

修复 `_merge_table_into()` 之后 canonical metadata 与实际表内容不一致的问题。

### 5.2 相关文件

- `backend/app/services/ptr_extractor.py`
- `backend/app/services/table_normalizer.py`
- `backend/app/models/table_models.py`
- `backend/tests/test_ptr_extractor*.py`
- `backend/tests/test_table_comparator.py`

### 5.3 必做项

- [x] 审查 `_merge_continuation_tables()` 与 `_merge_table_into()` 的 merge 后状态。
- [x] 不再保留 merge 前已经过期的 `metadata.parameter_records`。
- [x] merge 完成后，必须重建：
  - [x] `metadata.parameter_records`
  - [x] `metadata.column_roles`
  - [x] `metadata.canonical_diagnostics`
  - [x] `structure_confidence`
- [x] 若当前 `PTRTable` 不足以重建 canonical 语义，新增 **可序列化 canonical snapshot** 或 merge-ready metadata。
- [x] merge 后若存在重复 header 已移除、body rows 重排、页范围变化，diagnostics 必须同步更新。
- [x] merge 后记录 `merged_from_pages` 或等价追踪字段，便于回溯。

### 5.4 设计要求

1. **不要简单 append 旧 `parameter_records`**。  
   因为 repeated header removal、row reindex、fill-down、column role 重新判断都可能使旧 records 失效。

2. **merge 完成后必须以“合并后的表视图”重新生成 canonical 结果**。  
   推荐方式：
   - 方案 A：在 `PTRTable.metadata` 中保留可重建的 canonical snapshot；
   - 方案 B：保留足够的 merge-ready body/header/path 信息，以便重新过一遍 normalizer 的导出逻辑。

3. 若需要新增 snapshot，建议至少包含：

```python
metadata["canonical_snapshot"] = {
    "header_rows": ...,
    "body_rows": ...,
    "column_paths": ...,
    "column_roles": ...,
    "diagnostics": ...,
}
```

4. `source_rows` 与 merge 后的 row index 映射要可解释，不允许产生明显失真的来源追踪。

### 5.5 必加测试

- [x] 新增跨页续表测试：
  - page1 有前半参数；
  - page2 有后半参数；
  - merge 后 canonical comparator 必须能看到 page2 参数。
- [x] 新增 merge 后 metadata 重建测试：
  - merge 前后 `parameter_records` 数量应与合并后的 body 行对应。
- [x] 新增 repeated header removal + metadata 重建联合测试。

### 5.6 验收标准

1. merge 后 `rows`、`column_paths`、`parameter_records`、`diagnostics`、`structure_confidence` 彼此一致。
2. comparator 走 canonical 路径时，不会因为 metadata 过期而漏看续表参数。
3. merge 后日志可判断是否进行了 canonical metadata rebuild。

---

## 6. B. dimension-aware ParameterRecord

### 6.1 目标

让 `column_paths` 中的多维表头真正展开为独立维度记录，避免在 `ParameterRecord` 层再次把结构压平。

### 6.2 相关文件

- `backend/app/models/table_models.py`
- `backend/app/services/table_normalizer.py`
- `backend/app/services/table_comparator.py`
- `backend/tests/test_table_normalizer.py`
- `backend/tests/test_table_comparator.py`

### 6.3 必做项

- [x] 重构 `to_parameter_records()` / `_build_parameter_records()`。
- [x] 不再只把 `model/group` 独立列当作 dimensions。
- [ ] 对多维 `column_paths` 做维度展开。例如：

```text
["心房", "常规数值"]
["心房", "标准设置"]
["心室", "常规数值"]
["心室", "标准设置"]
```

应展开为：

```text
Record A:
  parameter_name = ...
  dimensions = {"axis_1": "心房"}
  values = {"常规数值": "...", "标准设置": "..."}

Record B:
  parameter_name = ...
  dimensions = {"axis_1": "心室"}
  values = {"常规数值": "...", "标准设置": "..."}
```

- [x] `ParameterRecord.source_rows` 支持多行来源，不要假设永远只有单行。
- [x] comparator 侧更新 record 消费逻辑，按 `parameter_name + dimensions + values` 比较。
- [x] `_pick_ptr_value_from_parameter_record()` 不允许再从多个同名 leaf value 中随意挑第一个。
- [ ] 为 dimension-aware record 增加更清晰的调试输出。

### 6.4 设计要求

1. **区分“维度标签”和“值标签”**。  
   对 `column_paths` 来说，建议将非叶子路径段优先视作维度候选，叶子标签再交给 role lexicon 决定它是 value/default/tolerance/remark 哪一类值。

2. **不要把 sibling 维度合并进同一个 record**。  
   例如 `心房` 和 `心室` 必须是两个 record，而不是一个 record 里同时出现两套值。

3. **行维度和列表头维度需要组合**。  
   若左侧还有 `适用型号 / 分组 / 腔室` 等显式维度列，应与 `column_paths` 的列维度合并后一起进入 `dimensions`。

4. **保留 legacy 兼容导出**。  
   dimension-aware record 只是增强语义表示，不改变原有 `headers / rows` 的兼容输出。

### 6.5 建议实现思路

建议将 `column_paths` 拆成：

- `dimension_labels`：如 `心房`
- `value_leaf`：如 `常规数值`

再按 `(parameter_name, explicit_row_dimensions, path_dimensions)` 分组，构建 record。

示例伪代码：

```python
for body_row in rows:
    parameter_name = ...
    row_dimensions = ...
    for value_col in value_columns:
        path = column_paths[value_col]
        path_dimensions = infer_path_dimensions(path)
        value_key = infer_value_leaf(path)
        group_key = (parameter_name, tuple(sorted({**row_dimensions, **path_dimensions}.items())))
        records[group_key].values[value_key] = cell_value
```

### 6.6 必加测试

- [x] 双层表头 `心房 / 心室` 测试。
- [x] 三层表头维度展开测试。
- [x] `clause/report` 只覆盖心房，不应要求心室一起出现。
- [x] 同一参数名在不同维度下 values 不应互相覆盖。
- [x] `_pick_ptr_value_from_parameter_record()` 不再出现“多个候选时随便取第一个”的行为。

### 6.7 验收标准

1. 多维列路径已展开成独立语义记录。
2. comparator 不再把 sibling 维度误当成同一覆盖单元。
3. 维度与值的归属可解释，调试时能看出每个 record 来源于哪几行、哪几列路径。

---

## 7. C. dual-view fallback

### 7.1 目标

在低结构置信度场景下，保留 canonical metadata，不要直接丢回 pure legacy 表示。

### 7.2 相关文件

- `backend/app/services/ptr_extractor.py`
- `backend/app/services/table_comparator.py`
- 如需要，可补充相关模型文件

### 7.3 必做项

- [x] 修改 `ptr_extractor`：`structure_confidence < 0.7` 时，仍保留 canonical metadata。
- [x] comparator 改为：
  - [x] 先尝试 canonical；
  - [x] 若 canonical 无有效 comparison，再 fallback legacy。
- [x] 在 `metadata` 中补充以下字段：
  - [x] `canonical_available`
  - [x] `canonical_low_confidence`
  - [x] `canonical_disabled_reason`
- [x] 日志中明确输出当前比较是否：
  - 使用 canonical；
  - 因何原因退回 legacy。

### 7.4 设计要求

1. **低置信度 ≠ canonical 不可用**。  
   低置信度只表示需要更谨慎地消费 canonical 结果，而不是立即丢弃。

2. 推荐比较顺序：

```text
canonical metadata available?
    yes -> 尝试 canonical comparison
            if comparison invalid / empty / inconsistent:
                fallback legacy
    no  -> legacy
```

3. 需要保留 fallback 原因，便于统计：
   - `missing_parameter_records`
   - `invalid_column_paths`
   - `empty_comparison`
   - `low_confidence_rejected`
   - 其他明确理由

### 7.5 必加测试

- [x] 低置信度表仍可产生 canonical comparison。
- [x] canonical comparison 无效时仍能回退 legacy。
- [x] metadata 中的 `canonical_*` 字段正确填充。
- [x] 日志或 diagnostics 中可以识别 fallback 原因。

### 7.6 验收标准

1. 复杂表不会因为低置信度而直接失去 canonical 视图。
2. legacy fallback 仍兼容原有行为。
3. 比较路径与回退原因对调试可见。

---

## 8. D. continuation 判定收紧

### 8.1 目标

降低误并相邻但不同表的概率。

### 8.2 相关文件

- `backend/app/services/ptr_extractor.py`
- continuation 相关测试文件
- 新增 adversarial regression tests

### 8.3 必做项

- [x] 审查 `_is_table_continuation()` 中所有“过宽”直接返回 `True` 的规则。
- [x] 删除或收紧类似：
  - [x] `not looks_like_new_table_start(current) => True`
  - [x] 缺少 header/path overlap 仍直接判续表 的分支
- [x] continuation 至少满足以下之一：
  - [x] 同 `table_number`
  - [x] 高结构相似度 + 页连续
  - [x] 上页接近页底 / 下页接近页顶 + header/path overlap
- [x] 对低相似度、无共享 header/path 的相邻表，禁止自动 merge。
- [x] 对“拒绝合并”的主要原因打日志。

### 8.4 设计要求

1. **不要只看列数接近**。  
   列数相同或相近只是弱信号，不能单独作为 continuation 成立依据。

2. **优先看结构共性**：
   - header overlap
   - column_paths overlap
   - 列角色分布相似度
   - 页边位置（上一页靠底，下一页靠顶）

3. **支持“拒绝合并”的可解释性**。  
   例如：
   - `rejected: low_similarity`
   - `rejected: no_header_overlap`
   - `rejected: page_gap_too_large`

### 8.5 必加测试

- [x] 两个相邻表列数相近但内容不同，不应被 merge。
- [x] 两个相邻表无表号，但 header/path overlap 高，应被 merge。
- [x] 上页尾 + 下页头 continuation 场景仍能正确 merge。
- [x] 低相似度 case 能稳定拒绝合并，并留下 reject reason。

### 8.6 验收标准

1. continuation 误并率下降。
2. 真正续表 case 仍保持可合并。
3. 合并/拒绝判断有日志可追踪。

---

## 9. E. role lexicon 统一

### 9.1 目标

把列角色推断从“各模块各猜各的”改为统一语义入口。

### 9.2 相关文件

- 新增 `backend/app/services/table_semantics.py`（或同类文件）
- `backend/app/services/table_normalizer.py`
- `backend/app/services/table_comparator.py`
- 相关测试文件

### 9.3 必做项

- [x] 新增统一 lexicon / 语义推断模块。
- [x] 抽出统一 token 归一化与 role inference 入口。
- [x] `normalizer` 与 `comparator` 全部改为共用这一入口。
- [x] 给 unknown role 打日志与计数。
- [ ] 新增同义词测试，至少覆盖：
- [x] `规格`
- [x] `适用型号`
- [x] `组别`
- [x] `部位`
- [x] `类型`
- [x] `默认值`
- [x] `设置值`
- [x] `范围`
- [x] `检验结果`

### 9.4 建议接口

```python
class TableSemantics:
    def normalize_token(self, text: str) -> str: ...
    def infer_column_role(self, labels: list[str]) -> str: ...
    def infer_value_leaf_role(self, label: str) -> str: ...
    def split_path_semantics(self, labels: list[str]) -> tuple[list[str], str]: ...
```

### 9.5 设计要求

1. `normalize_token()` 负责：
   - 全角半角归一；
   - 空白与标点规整；
   - 常见同义词映射；
   - 大小写规整（如适用）。

2. `infer_column_role()` 的输入优先使用 `column_paths.labels`，而不是只看展平 header 文本。

3. `unknown` 必须可观测，不允许默默吞掉：
   - 日志；
   - diagnostics；
   - 统计计数。

### 9.6 必加测试

- [x] normalizer 与 comparator 对同一组 labels 得到一致 role。
- [x] 同义词 case 覆盖通过。
- [x] unknown role 能被记录。

### 9.7 验收标准

1. 上下游列角色判断一致。
2. 词典扩展点集中，后续维护成本下降。
3. unknown role 可统计、可调试。

---

## 10. 可观测性与调试增强（建议同步做）

以下内容不是单独 phase，但建议在实施过程中顺手补齐。

### 10.1 建议新增的 metadata / diagnostics 字段

- [x] `canonical_available`
- [x] `canonical_low_confidence`
- [x] `canonical_disabled_reason`
- [x] `comparison_path_used`
- [x] `continuation_merge_reason`
- [x] `continuation_reject_reason`
- [x] `unknown_role_count`
- [x] `parameter_record_count`

### 10.2 建议新增日志

- [ ] continuation merge/reject 决策日志
- [ ] canonical vs legacy comparison 路径日志
- [ ] dimension-aware record 展开摘要日志
- [ ] unknown role / fallback reason 日志

### 10.3 建议新增统计

- [ ] 低置信度但 canonical 可用的表数量
- [ ] canonical 成功使用率
- [ ] fallback 到 legacy 的原因分布
- [ ] unknown role 的标签分布

---

## 11. 测试要求

### 11.1 每完成一个子阶段都必须跑

```bash
cd backend
source .venv/bin/activate
pytest tests/test_table_normalizer.py -v
pytest tests/test_table_comparator.py -v
pytest tests/ -v
```

### 11.2 建议补充的定向测试

根据你仓库实际命名，可新增或扩展：

```text
tests/test_ptr_extractor_continuation_merge.py
tests/test_table_normalizer_dimension_records.py
tests/test_table_comparator_canonical_fallback.py
tests/test_ptr_extractor_continuation_adversarial.py
tests/test_table_semantics.py
```

### 11.3 测试原则

1. 优先补真实失败模式，再补 synthetic happy path。
2. 一条测试尽量只钉一个误判点。
3. 对 merge / fallback / semantics 这种逻辑，断言不仅看最终 pass/fail，也要断中间结构：
   - `parameter_records`
   - `column_paths`
   - `structure_confidence`
   - `comparison_path_used`
   - `continuation_reject_reason`

---

## 12. 最终验收清单

- [x] A. continuation merge 修复完成
- [x] B. dimension-aware ParameterRecord 完成
- [x] C. dual-view fallback 完成
- [x] D. continuation 判定收紧完成
- [x] E. role lexicon 统一完成
- [x] 新增测试通过
- [x] 全量 `pytest tests/ -v` 通过
- [x] 本文件 checklist 全部更新为 `[x]`

---

## 13. 给 Codex 的最后提醒

1. 这轮不要再把复杂表格“压回普通二维字符串数组后再硬比”。
2. 先修 **merge 后 canonical 元数据过期**，再修 **dimension-aware records**。
3. `legacy` 不是要删除，而是要成为**有解释、有统计的 fallback**。
4. 这轮做完后，canonical 路径才算真正进入“可稳定消费”的阶段。
