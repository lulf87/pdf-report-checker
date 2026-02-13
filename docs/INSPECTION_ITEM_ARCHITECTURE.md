# 检验项目表格核对功能 - 架构设计文档

> 版本: 1.0
> 日期: 2026-02-12
> 状态: 设计完成

---

## 1. 架构概述

### 1.1 功能目标

实现检验报告中的"检验项目表格"自动解析和单项结论逻辑核对功能。

### 1.2 核心能力

1. **表格检测**: 自动识别包含7列（序号、检验项目、标准条款、标准要求、检验结果、单项结论、备注）的检验项目表格
2. **跨页处理**: 支持续表识别和数据连续性处理
3. **单项结论判定**: 根据检验结果自动判定单项结论是否正确
4. **结果展示**: 前端可视化展示核对结果

### 1.3 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              报告核对工具架构                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   Frontend   │     │   Backend    │     │   Services   │                │
│  │  (React+TS)  │◄────┤  (FastAPI)   │◄────┤  (Python)    │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│         │                    │                    │                        │
│         ▼                    ▼                    ▼                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     检验项目核对模块 (新增)                           │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │   ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐  │   │
│  │   │  TableDetector  │───►│  TableParser    │───►│ItemCheckEngine │  │   │
│  │   │  (表格检测)      │    │  (表格解析)      │    │ (核对引擎)      │  │   │
│  │   └─────────────────┘    └─────────────────┘    └────────────────┘  │   │
│  │            │                    │                    │              │   │
│  │            ▼                    ▼                    ▼              │   │
│  │   ┌─────────────────────────────────────────────────────────────┐   │   │
│  │   │              InspectionItemCheckResult (数据模型)            │   │   │
│  │   └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 处理流程

### 2.1 整体流程

```
PDF输入
    │
    ▼
┌─────────────────┐
│ 1. 页面解析      │ ◄── 复用现有 PDFParser
│    (PageInfo)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 表格检测      │ ◄── 新增 TableDetector
│    查找7列表格   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 表格解析      │ ◄── 新增 InspectionTableParser
│    提取结构化数据 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 跨页处理      │ ◄── 续表识别 + 数据合并
│    处理续表标记  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 单项结论核对  │ ◄── 新增 ConclusionValidator
│    判定逻辑验证  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. 结果生成      │ ◄── InspectionItemCheckResult
│    整合到CheckResult │
└─────────────────┘
```

### 2.2 单项结论判定算法

```python
# 判定优先级（从高到低）
def validate_conclusion(requirement_checks: List[RequirementCheck],
                       actual_conclusion: str) -> Tuple[bool, str]:
    """
    返回: (是否正确, 期望结论)
    """
    results = [r.inspection_result for r in requirement_checks]

    # 优先级1: 任意检验结果包含"不符合" → 应为"不符合"
    if any("不符合" in r for r in results if r):
        expected = "不符合"
    # 优先级2: 所有检验结果都为"——"或空白 → 应为"/"
    elif all(r in ["——", "", None] for r in results):
        expected = "/"
    # 优先级3: 其他情况 → 应为"符合"
    else:
        expected = "符合"

    is_correct = (actual_conclusion == expected)
    return is_correct, expected
```

### 2.3 跨页处理逻辑

```
页面N                          页面N+1 (续表)
┌──────────────┐              ┌──────────────┐
│ 检验项目表格  │              │ 续 / 续表     │ ◄── 续表标记检测
├────┬────┬────┤              ├────┬────┬────┤
│ 1  │ A  │ 符合│              │    │ B  │ ——│ ◄── 序号为空
├────┼────┼────┤              ├────┼────┼────┤
│ 2  │ C  │ 符合│              │ 2  │ D  │ 符合│ ◄── 新序号
└────┴────┴────┘              └────┴────┴────┘
       │                             │
       └───────────┬─────────────────┘
                   ▼
            ┌──────────────┐
            │ 数据合并      │
            │ - 继承序号    │
            │ - 继承检验项目 │
            │ - 追加条款    │
            └──────────────┘
```

---

## 3. 模块划分

### 3.1 新增模块清单

| 模块 | 文件路径 | 职责 |
|-----|---------|------|
| TableDetector | `services/table_detector.py` | 检测检验项目表格 |
| InspectionTableParser | `services/inspection_table_parser.py` | 解析表格为结构化数据 |
| ConclusionValidator | `services/conclusion_validator.py` | 单项结论判定逻辑 |
| 数据模型 | `models/schemas.py` (扩展) | 新增4个数据模型 |

### 3.2 修改模块清单

| 模块 | 修改内容 |
|-----|---------|
| `services/report_checker.py` | 集成检验项目核对流程 |
| `models/schemas.py` | 添加InspectionItemCheckResult到CheckResult |
| `main.py` | 无需修改（数据通过CheckResult返回） |

### 3.3 前端模块

| 模块 | 文件路径 | 职责 |
|-----|---------|------|
| InspectionItemTab | `components/InspectionItemTab.tsx` | 检验项目核对展示页签 |
| InspectionItemTable | `components/InspectionItemTable.tsx` | 表格组件 |
| ConclusionBadge | `components/ConclusionBadge.tsx` | 单项结论状态标记 |
| types/index.ts | 扩展类型定义 | 新增检验项目相关类型 |

---

## 4. 数据模型设计

### 4.1 模型关系图

```
CheckResult
    │
    ├── inspection_item_check: InspectionItemCheckResult
    │       │
    │       ├── item_checks: List[InspectionItemCheck]
    │       │       │
    │       │       ├── item_number: str
    │       │       ├── item_name: str
    │       │       ├── clauses: List[ClauseCheck]
    │       │       │       │
    │       │       │       ├── clause_number: str
    │       │       │       ├── conclusion: str (实际值)
    │       │       │       ├── expected_conclusion: str (期望值)
    │       │       │       ├── is_conclusion_correct: bool
    │       │       │       └── requirements: List[RequirementCheck]
    │       │       │               │
    │       │       │               ├── requirement_text: str
    │       │       │               ├── inspection_result: str
    │       │       │               └── remark: str
    │       │       │
    │       │       └── status: str (pass/warning/fail)
    │       │
    │       ├── errors: List[ErrorItem]
    │       └── statistics: Dict
    │
    └── ... (其他已有字段)
```

### 4.2 模型定义

```python
# models/schemas.py

class RequirementCheck(BaseModel):
    """标准要求核对 - 最细粒度"""
    requirement_text: str           # 标准要求内容
    inspection_result: str          # 检验结果
    remark: str = ""                # 备注


class ClauseCheck(BaseModel):
    """标准条款核对 - 包含多条标准要求"""
    clause_number: str              # 标准条款编号
    requirements: List[RequirementCheck] = []  # 标准要求列表
    conclusion: str                 # 单项结论（文档实际值）
    expected_conclusion: str        # 期望的单项结论
    is_conclusion_correct: bool     # 结论是否正确


class InspectionItemCheck(BaseModel):
    """检验项目核对 - 一个检验项目可包含多条标准条款"""
    item_number: str                # 序号
    item_name: str                  # 检验项目名称
    clauses: List[ClauseCheck] = [] # 标准条款列表
    issues: List[str] = []          # 问题列表
    status: str = "pass"            # pass/warning/fail


class InspectionItemCheckResult(BaseModel):
    """检验项目核对结果 - 汇总"""
    has_table: bool = False         # 是否检测到检验项目表格
    total_items: int = 0            # 检验项目总数
    total_clauses: int = 0          # 标准条款总数
    correct_conclusions: int = 0    # 单项结论正确的条款数
    incorrect_conclusions: int = 0  # 单项结论错误的条款数
    item_checks: List[InspectionItemCheck] = []  # 各项目核对详情
    cross_page_continuations: int = 0  # 跨页续表数量
    errors: List[ErrorItem] = []    # 错误列表
```

### 4.3 CheckResult扩展

```python
class CheckResult(BaseModel):
    # ... 已有字段 ...

    # 检验项目核对结果（新增）
    inspection_item_check: Optional[InspectionItemCheckResult] = None
```

---

## 5. API 接口变更

### 5.1 现有接口（无需变更）

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/api/check/{file_id}` | POST | 核对端点，返回的CheckResult已包含inspection_item_check |
| `/api/result/{file_id}` | GET | 获取结果，包含检验项目核对数据 |
| `/api/export/{file_id}` | GET | 导出报告，需支持检验项目核对Sheet |

### 5.2 导出功能扩展

**Excel导出 (Sheet3 - 检验项目核对明细)**:

| 列名 | 说明 |
|-----|------|
| 序号 | 检验项目序号 |
| 检验项目 | 检验项目名称 |
| 标准条款 | 条款编号 |
| 标准要求 | 要求内容 |
| 检验结果 | 实际检验结果 |
| 单项结论 | 文档中的结论 |
| 期望结论 | 根据规则计算的正确结论 |
| 核对状态 | 正确/错误 |

---

## 6. 错误代码定义

| 错误代码 | 描述 | 级别 |
|---------|------|------|
| `CONCLUSION_MISMATCH_001` | 应标为"/"但标为其他 | ERROR |
| `CONCLUSION_MISMATCH_002` | 应标为"符合"但标为其他 | ERROR |
| `CONCLUSION_MISMATCH_003` | 应标为"不符合"但标为其他 | ERROR |
| `CONCLUSION_MISMATCH_004` | 不应标为"不符合" | ERROR |
| `CONTINUITY_ERROR_001` | 跨页数据不连续 | WARN |
| `TABLE_NOT_FOUND` | 未找到检验项目表格 | INFO |

---

## 7. 前端界面设计

### 7.1 新增页签

在ResultsPage的结果展示区域新增"检验项目核对"页签：

```
┌─────────────────────────────────────────────────────────────┐
│  首页与第三页比对  │  样品描述表格  │  [检验项目核对]  │  部件核对  │  问题汇总  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  统计卡片: 总项目数 | 正确结论数 | 错误结论数 | 续表数        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 筛选: [全部 ▼]  搜索: [____________]  [导出明细]    │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 序号 │ 检验项目 │ 标准条款 │ 单项结论 │ 状态 │ 操作 │   │
│  ├──────┼──────────┼──────────┼──────────┼──────┼──────┤   │
│  │  1   │ 外观检查  │ 5.1      │  符合    │  ✅  │ 详情 │   │
│  │  2   │ 尺寸检查  │ 5.2      │  符合    │  ❌  │ 详情 │   │
│  ├──────┴──────────┴──────────┴──────────┴──────┴──────┤   │
│  │ [展开详情]                                           │   │
│  │ 标准要求: 长度应符合设计要求                          │   │
│  │ 检验结果: 100mm                                      │   │
│  │ 期望结论: 符合  |  实际结论: /  |  错误!              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 组件清单

| 组件名 | 文件路径 | 功能 |
|-------|---------|------|
| InspectionItemTab | `components/InspectionItemTab.tsx` | 页签容器 |
| InspectionItemStats | `components/InspectionItemStats.tsx` | 统计卡片 |
| InspectionItemTable | `components/InspectionItemTable.tsx` | 表格展示 |
| ClauseDetailRow | `components/ClauseDetailRow.tsx` | 展开详情行 |
| ConclusionBadge | `components/ConclusionBadge.tsx` | 结论状态标记 |

---

## 8. 任务分解清单

### 8.1 Backend 任务

| 任务ID | 任务名称 | 优先级 | 依赖 | 负责人 |
|-------|---------|-------|------|-------|
| B-1 | 创建 RequirementCheck/ClauseCheck/InspectionItemCheck 数据模型 | P0 | - | Backend |
| B-2 | 创建 InspectionItemCheckResult 数据模型 | P0 | B-1 | Backend |
| B-3 | 实现 TableDetector 表格检测服务 | P0 | - | Backend |
| B-4 | 实现 InspectionTableParser 表格解析服务 | P0 | B-3 | Backend |
| B-5 | 实现跨页续表检测与数据合并逻辑 | P1 | B-4 | Backend |
| B-6 | 实现 ConclusionValidator 单项结论判定逻辑 | P0 | B-1 | Backend |
| B-7 | 集成检验项目核对到 ReportChecker | P1 | B-2,B-4,B-6 | Backend |
| B-8 | 扩展 Excel 导出功能（Sheet3） | P2 | B-7 | Backend |
| B-9 | 编写单元测试 | P1 | B-7 | Backend |

### 8.2 Frontend 任务

| 任务ID | 任务名称 | 优先级 | 依赖 | 负责人 |
|-------|---------|-------|------|-------|
| F-1 | 扩展 types/index.ts 添加检验项目类型定义 | P0 | - | Frontend |
| F-2 | 创建 ConclusionBadge 组件 | P1 | F-1 | Frontend |
| F-3 | 创建 InspectionItemTable 组件 | P1 | F-1,F-2 | Frontend |
| F-4 | 创建 InspectionItemStats 统计卡片组件 | P2 | F-1 | Frontend |
| F-5 | 创建 InspectionItemTab 页签组件 | P1 | F-3,F-4 | Frontend |
| F-6 | 修改 ResultsPage 添加检验项目核对页签 | P1 | F-5 | Frontend |
| F-7 | 实现检验项目明细导出功能 | P2 | F-5 | Frontend |

### 8.3 QA 任务

| 任务ID | 任务名称 | 优先级 | 依赖 | 负责人 |
|-------|---------|-------|------|-------|
| Q-1 | 编写检验项目表格检测测试用例 | P0 | - | QA |
| Q-2 | 编写单项结论判定逻辑测试用例 | P0 | - | QA |
| Q-3 | 编写跨页续表处理测试用例 | P1 | - | QA |
| Q-4 | 准备测试PDF样本（含正常/异常/跨页场景） | P1 | - | QA |
| Q-5 | 执行集成测试 | P2 | B-7,F-6 | QA |
| Q-6 | 编写测试报告 | P2 | Q-5 | QA |

---

## 9. 实施建议

### 9.1 开发顺序

```
Week 1:
├── Backend: B-1, B-2, B-3, B-4 (数据模型 + 表格检测解析)
├── QA: Q-1, Q-2, Q-3, Q-4 (测试用例设计)
└── Frontend: F-1 (类型定义)

Week 2:
├── Backend: B-5, B-6, B-7 (跨页处理 + 判定逻辑 + 集成)
├── Frontend: F-2, F-3, F-4, F-5, F-6 (组件开发)
└── QA: 测试样本准备

Week 3:
├── Backend: B-8, B-9 (导出 + 单元测试)
├── Frontend: F-7 (导出功能)
└── QA: Q-5, Q-6 (集成测试 + 报告)
```

### 9.2 关键风险点

1. **表格检测准确性**: 不同PDF的表格结构可能有差异，需要充分测试
2. **跨页处理复杂度**: 续表标记形式多样，需处理边界情况
3. **性能考虑**: 大型检验项目表格可能导致处理时间较长

### 9.3 测试策略

1. **单元测试**: 覆盖判定逻辑、表格解析核心函数
2. **集成测试**: 完整流程测试，使用真实PDF样本
3. **边界测试**: 跨页场景、空数据、异常格式

---

*文档结束*
