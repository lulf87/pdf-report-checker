# 详细比对信息展示与LLM开关功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 1) 新增详细比对信息展示功能，记录和返回每个部件的完整比对过程；2) 增加大模型(LLM)比对开关，可配置是否启用LLM增强比对

**Architecture:** 扩展现有数据模型添加比对详情记录，在report_checker关键比对节点插入详情收集，通过config配置控制LLM调用

**Tech Stack:** Python, Pydantic, FastAPI, PaddleOCR, Anthropic/OpenAI API

---

## Task 1: 扩展数据模型添加比对详情

**Files:**
- Modify: `python_backend/models/schemas.py:65-84`

**Step 1: 添加比对详情模型**

在FieldComparison后添加新模型：

```python
class ComparisonDetail(BaseModel):
    """单个比对步骤详情"""
    step: str  # 比对步骤名称，如"caption提取"、"名称匹配"、"OCR字段提取"
    input_data: Dict[str, Any] = {}  # 输入数据
    output_data: Dict[str, Any] = {}  # 输出结果
    method: str = ""  # 使用的方法/算法
    confidence: float = 1.0  # 置信度
    execution_time_ms: Optional[int] = None  # 执行时间
    is_success: bool = True  # 是否成功
    error_message: Optional[str] = None  # 错误信息


class DetailedComponentCheck(ComponentCheck):
    """带详细比对过程的部件核对结果"""
    comparison_details: List[ComparisonDetail] = []  # 详细比对过程
    matched_photos: List[Dict[str, Any]] = []  # 匹配到的照片列表
    matched_labels: List[Dict[str, Any]] = []  # 匹配到的标签列表
    match_reason: str = ""  # 匹配/不匹配的原因说明


class DetailedCheckResult(CheckResult):
    """带详细比对信息的核对结果"""
    enable_detailed_comparison: bool = False  # 是否启用详细比对
    detailed_checks: List[DetailedComponentCheck] = []  # 详细核对结果
    llm_usage_info: Dict[str, Any] = {}  # LLM使用信息
```

**Step 2: 验证模型定义**

运行: `cd python_backend && python -c "from models.schemas import ComparisonDetail, DetailedComponentCheck, DetailedCheckResult; print('Models OK')"`

Expected: `Models OK`

**Step 3: Commit**

```bash
git add python_backend/models/schemas.py
git commit -m "feat: add detailed comparison models"
```

---

## Task 2: 添加LLM开关配置

**Files:**
- Modify: `python_backend/config.py:36-65`

**Step 1: 扩展配置类**

在ENABLE_LLM_POST_PROCESSING下方添加：

```python
    # LLM比对功能开关
    ENABLE_LLM_COMPARISON: bool = False  # 是否启用LLM进行字段比对
    LLM_COMPARISON_MODE: str = "fallback"  # 模式: "fallback"(OCR失败时调用LLM), "enhance"(总是用LLM增强), "disabled"(禁用)
    LLM_RETRY_ON_FAILURE: bool = True  # OCR失败时是否尝试LLM
    LLM_CONFIDENCE_THRESHOLD: float = 0.8  # LLM结果置信度阈值
```

在is_llm_enabled函数后添加：

```python
def is_llm_comparison_enabled() -> bool:
    """检查是否启用LLM比对功能"""
    return (
        settings.ENABLE_LLM_COMPARISON and
        is_llm_enabled() and
        settings.LLM_COMPARISON_MODE != "disabled"
    )
```

**Step 2: 验证配置加载**

运行: `cd python_backend && python -c "from config import is_llm_comparison_enabled, settings; print(f'LLM Comparison: {is_llm_comparison_enabled()}')"`

Expected: `LLM Comparison: False`

**Step 3: Commit**

```bash
git add python_backend/config.py
git commit -m "feat: add LLM comparison configuration options"
```

---

## Task 3: 创建详细比对收集器

**Files:**
- Create: `python_backend/utils/comparison_logger.py`

**Step 1: 创建比对日志记录器**

```python
"""
比对过程日志记录器
用于收集和存储详细的比对过程信息
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ComparisonStep:
    """单个比对步骤"""
    step_name: str
    start_time: float
    end_time: Optional[float] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    method: str = ""
    is_success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_name,
            "method": self.method,
            "input": self.input_data,
            "output": self.output_data,
            "execution_time_ms": int((self.end_time - self.start_time) * 1000) if self.end_time else None,
            "is_success": self.is_success,
            "error_message": self.error_message
        }


class ComparisonLogger:
    """比对过程日志记录器"""

    def __init__(self, component_name: str, enable_logging: bool = True):
        self.component_name = component_name
        self.enable_logging = enable_logging
        self.steps: List[ComparisonStep] = []
        self.current_step: Optional[ComparisonStep] = None

    def start_step(self, step_name: str, method: str = "", **inputs) -> 'ComparisonLogger':
        """开始记录一个比对步骤"""
        if not self.enable_logging:
            return self

        self.current_step = ComparisonStep(
            step_name=step_name,
            start_time=time.time(),
            input_data=dict(inputs),
            method=method
        )
        return self

    def end_step(self, success: bool = True, **outputs) -> 'ComparisonLogger':
        """结束当前比对步骤"""
        if not self.enable_logging or not self.current_step:
            return self

        self.current_step.end_time = time.time()
        self.current_step.output_data = dict(outputs)
        self.current_step.is_success = success
        self.steps.append(self.current_step)
        self.current_step = None
        return self

    def record_error(self, error_message: str):
        """记录步骤错误"""
        if self.current_step:
            self.current_step.error_message = error_message
            self.current_step.is_success = False

    def get_details(self) -> List[Dict[str, Any]]:
        """获取所有步骤详情"""
        return [step.to_dict() for step in self.steps]

    def clear(self):
        """清空记录"""
        self.steps = []
        self.current_step = None
```

**Step 2: 验证模块**

运行: `cd python_backend && python -c "from utils.comparison_logger import ComparisonLogger, ComparisonStep; logger = ComparisonLogger('test'); print('Logger OK')"`

Expected: `Logger OK`

**Step 3: Commit**

```bash
git add python_backend/utils/comparison_logger.py
git commit -m "feat: add comparison logger for detailed tracking"
```

---

## Task 4: 在report_checker中集成详细比对记录

**Files:**
- Modify: `python_backend/services/report_checker.py:1-50`
- Modify: `python_backend/services/report_checker.py:509-600`

**Step 1: 添加导入和初始化**

在文件顶部添加：

```python
from utils.comparison_logger import ComparisonLogger
from config import is_llm_comparison_enabled, settings as app_settings
```

**Step 2: 修改_check_components方法收集详细信息**

在_check_components方法中添加日志收集：

```python
    def _check_components(self, sample_table: Optional[TableData],
                         photo_analysis: Dict[str, Any],
                         enable_detailed: bool = False) -> List[ComponentCheck]:
        """核对每个部件"""
        if not sample_table:
            return []

        component_checks = []
        components = self._extract_components_from_table(sample_table)
        photos = photo_analysis.get('photos', [])
        labels = photo_analysis.get('labels', [])

        for component in components:
            component_name = component['name']

            # 初始化比对日志记录器
            logger = ComparisonLogger(component_name, enable_logging=enable_detailed)

            # 记录开始
            logger.start_step(
                "部件核对开始",
                "component_check",
                component_name=component_name,
                model=component.get('model', ''),
                serial_batch=component.get('serial_batch', '')
            )

            # 检查是否为"本次检测未使用"
            remark = component.get('remark', '')
            remark_clean = re.sub(r'\s+', '', remark)
            is_unused = '本次检测未使用' in remark_clean

            logger.start_step(
                "检查使用状态",
                "remark_check",
                remark=remark,
                is_unused=is_unused
            ).end_step(is_unused is not None, is_unused=is_unused)

            # 照片匹配 - 详细记录
            logger.start_step(
                "照片匹配",
                "photo_matching",
                available_photos=len(photos)
            )

            matched_photos = []
            for p in photos:
                is_match = self._is_component_name_match(component_name, p['subject_name'])
                if is_match and not p['is_label']:
                    matched_photos.append(p)

            has_photo = len(matched_photos) > 0
            logger.end_step(
                True,
                has_photo=has_photo,
                matched_count=len(matched_photos),
                matched_captions=[p['caption'] for p in matched_photos]
            )

            # 标签匹配 - 详细记录
            logger.start_step(
                "标签匹配",
                "label_matching",
                available_labels=len(labels)
            )

            matched_labels = []
            for l in labels:
                is_match = self._is_component_name_match(component_name, l['subject_name'])
                if is_match:
                    matched_labels.append(l)

            has_chinese_label = len(matched_labels) > 0
            logger.end_step(
                True,
                has_chinese_label=has_chinese_label,
                matched_count=len(matched_labels),
                matched_captions=[l['caption'] for l in matched_labels]
            )

            # 字段比对 - 详细记录
            field_comparisons = []
            issues = []

            if has_chinese_label:
                for idx, label_info in enumerate(matched_labels):
                    ocr_result_data = label_info.get('ocr_result', {})
                    ocr_result = OCRResult(**ocr_result_data) if ocr_result_data else None

                    if ocr_result:
                        logger.start_step(
                            f"OCR字段比对_{idx+1}",
                            "ocr_comparison",
                            label_caption=label_info.get('caption', ''),
                            label_page=label_info.get('page_num', 0)
                        )

                        comparisons = self._compare_component_fields(
                            component, ocr_result
                        )
                        field_comparisons.extend(comparisons)

                        comparison_results = []
                        for comp in comparisons:
                            comparison_results.append({
                                "field": comp.field_name,
                                "table": comp.table_value,
                                "ocr": comp.ocr_value,
                                "match": comp.is_match
                            })
                            if not comp.is_match:
                                issues.append(
                                    f"{comp.field_name}: 表格'{comp.table_value}' vs OCR'{comp.ocr_value}'"
                                )

                        logger.end_step(
                            True,
                            comparisons=comparison_results,
                            mismatch_count=sum(1 for c in comparisons if not c.is_match)
                        )

            # 确定状态
            if is_unused:
                if not has_photo and not has_chinese_label:
                    issues.append("本次检测未使用（无照片/标签）")
                status = 'pass'
            else:
                if not has_chinese_label:
                    issues.append("缺少中文标签")
                if not has_photo:
                    issues.append("缺少照片说明")
                status = 'fail' if (not has_chinese_label or not has_photo) else 'warning' if issues else 'pass'

            # 结束部件核对
            logger.start_step(
                "部件核对完成",
                "component_check_complete",
                status=status,
                issue_count=len(issues)
            ).end_step(status != 'fail')

            # 构建结果
            check_result = ComponentCheck(
                component_name=component_name,
                has_photo=has_photo,
                has_chinese_label=has_chinese_label,
                field_comparisons=field_comparisons,
                issues=issues,
                status=status
            )

            # 如果启用详细模式，添加详细信息
            if enable_detailed:
                check_result.comparison_details = logger.get_details()
                check_result.matched_photos = matched_photos
                check_result.matched_labels = matched_labels
                check_result.match_reason = "匹配成功" if (has_photo or has_chinese_label) else "未找到匹配"
                if is_unused:
                    check_result.match_reason = "本次检测未使用"

            component_checks.append(check_result)

        return component_checks
```

**Step 3: 修改check方法支持详细模式参数**

修改check方法签名：

```python
    async def check(self, pdf_path: str, file_id: str, enable_detailed: bool = False) -> CheckResult:
        """
        执行完整的报告核对流程

        Args:
            pdf_path: PDF文件路径
            file_id: 文件ID
            enable_detailed: 是否启用详细比对信息
        """
```

在调用_check_components时传递参数：

```python
        # 8. 核对部件
        component_checks = self._check_components(
            sample_table, photo_analysis, enable_detailed=enable_detailed
        )
```

**Step 4: 运行测试**

运行: `cd python_backend && python -c "from services.report_checker import ReportChecker; print('Import OK')"`

Expected: `Import OK`

**Step 5: Commit**

```bash
git add python_backend/services/report_checker.py
git commit -m "feat: integrate detailed comparison logging into component check"
```

---

## Task 5: 集成LLM比对增强功能

**Files:**
- Modify: `python_backend/services/report_checker.py:800-900`

**Step 1: 添加LLM辅助比对方法**

在_report_checker.py中添加新方法：

```python
    async def _llm_enhanced_field_comparison(
        self,
        component: Dict[str, str],
        ocr_result: OCRResult,
        logger: ComparisonLogger
    ) -> List[FieldComparison]:
        """使用LLM增强字段比对"""
        from services.llm_service import get_llm_service

        llm = get_llm_service()
        if not llm.is_available():
            logger.start_step("LLM增强", "llm_check").end_step(False, error="LLM不可用")
            return self._compare_component_fields(component, ocr_result)

        logger.start_step("LLM字段提取", "llm_extraction").end_step(True)

        # 尝试用LLM提取结构化字段
        try:
            expected_fields = ['批号', '序列号', '生产日期', '失效日期', '型号规格']
            llm_fields = llm.extract_structured_fields(
                ocr_result.full_text,
                expected_fields
            )

            # 合并LLM结果和OCR结果
            enhanced_structured = ocr_result.structured_data.copy()
            for field_key, field_data in llm_fields.items():
                if field_key not in enhanced_structured or not enhanced_structured[field_key].get('value'):
                    enhanced_structured[field_key] = field_data

            # 创建增强的OCR结果
            enhanced_ocr = OCRResult(
                page_num=ocr_result.page_num,
                image_path=ocr_result.image_path,
                text_blocks=ocr_result.text_blocks,
                full_text=ocr_result.full_text,
                structured_data=enhanced_structured
            )

            return self._compare_component_fields(component, enhanced_ocr)

        except Exception as e:
            logger.start_step("LLM处理", "llm_process").end_step(False, error=str(e))
            return self._compare_component_fields(component, ocr_result)
```

**Step 2: 修改_compare_component_fields支持LLM模式**

根据配置决定是否调用LLM：

```python
    async def _compare_with_llm_fallback(
        self,
        component: Dict[str, str],
        ocr_result: OCRResult,
        logger: ComparisonLogger
    ) -> List[FieldComparison]:
        """先尝试OCR比对，失败时使用LLM"""
        # 首先进行常规OCR比对
        comparisons = self._compare_component_fields(component, ocr_result)

        # 检查是否有字段不匹配
        has_mismatch = any(not c.is_match for c in comparisons)

        if has_mismatch and is_llm_comparison_enabled():
            logger.start_step("LLM回退比对", "llm_fallback", reason="OCR字段不匹配")

            # 尝试LLM增强
            llm_comparisons = await self._llm_enhanced_field_comparison(
                component, ocr_result, logger
            )

            # 如果LLM结果更好，使用LLM结果
            llm_success_rate = sum(1 for c in llm_comparisons if c.is_match) / len(llm_comparisons)
            ocr_success_rate = sum(1 for c in comparisons if c.is_match) / len(comparisons)

            if llm_success_rate > ocr_success_rate:
                logger.end_step(True, method="LLM", success_rate=llm_success_rate)
                return llm_comparisons
            else:
                logger.end_step(True, method="OCR", reason="OCR结果更好")

        return comparisons
```

**Step 3: Commit**

```bash
git add python_backend/services/report_checker.py
git commit -m "feat: add LLM-enhanced field comparison with fallback"
```

---

## Task 6: 更新API接口支持新参数

**Files:**
- Modify: `python_backend/main.py`

**Step 1: 修改check接口**

找到check接口并添加参数：

```python
@app.post("/check/{file_id}")
async def check_pdf(
    file_id: str,
    enable_detailed: bool = Query(False, description="启用详细比对信息"),
    enable_llm: bool = Query(False, description="启用LLM增强比对")
):
    """
    执行PDF核对检查

    - **enable_detailed**: 返回详细的比对过程信息
    - **enable_llm**: 启用大模型(LLM)辅助比对
    """
    # ... 现有代码 ...

    # 临时设置LLM开关
    original_llm_setting = app_settings.ENABLE_LLM_COMPARISON
    if enable_llm:
        app_settings.ENABLE_LLM_COMPARISON = True

    try:
        result = await checker.check(
            pdf_path,
            file_id,
            enable_detailed=enable_detailed
        )

        # 添加元信息
        result.enable_detailed_comparison = enable_detailed
        if enable_llm:
            result.llm_usage_info = {
                "enabled": True,
                "mode": app_settings.LLM_COMPARISON_MODE,
                "model": app_settings.LLM_MODEL
            }

        return result
    finally:
        # 恢复原始设置
        app_settings.ENABLE_LLM_COMPARISON = original_llm_setting
```

**Step 2: Commit**

```bash
git add python_backend/main.py
git commit -m "feat: add enable_detailed and enable_llm query parameters to check API"
```

---

## Task 7: 创建详细比对展示测试

**Files:**
- Create: `test_detailed_comparison.py`

**Step 1: 创建测试脚本**

```python
#!/usr/bin/env python3
"""测试详细比对功能"""

import sys
import asyncio
sys.path.insert(0, 'python_backend')

from services.report_checker import ReportChecker


async def test_detailed_comparison():
    """测试详细比对信息输出"""
    checker = ReportChecker()
    pdf_path = 'QW2025-2795 Draft.pdf'

    print("=" * 80)
    print("测试详细比对功能")
    print("=" * 80)

    # 启用详细比对
    result = await checker.check(pdf_path, 'test_detailed', enable_detailed=True)

    print(f"\n核对完成:")
    print(f"  总部件: {result.total_components}")
    print(f"  通过: {result.passed_components}")
    print(f"  失败: {result.failed_components}")

    # 显示第一个部件的详细比对信息
    if result.component_checks:
        first = result.component_checks[0]
        print(f"\n第一个部件 '{first.component_name}' 的详细比对:")

        if hasattr(first, 'comparison_details') and first.comparison_details:
            print(f"  比对步骤数: {len(first.comparison_details)}")
            for detail in first.comparison_details[:3]:  # 显示前3步
                print(f"    - {detail['step']}: {detail.get('method', 'N/A')}")

        if hasattr(first, 'matched_labels') and first.matched_labels:
            print(f"  匹配标签: {len(first.matched_labels)}个")

        if hasattr(first, 'match_reason'):
            print(f"  匹配原因: {first.match_reason}")


if __name__ == '__main__':
    asyncio.run(test_detailed_comparison())
```

**Step 2: 运行测试**

运行: `cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.2.9 && python test_detailed_comparison.py`

Expected: 显示详细的比对步骤信息

**Step 3: Commit**

```bash
git add test_detailed_comparison.py
git commit -m "test: add detailed comparison test script"
```

---

## Task 8: 更新文档

**Files:**
- Modify: `README.md`

**Step 1: 添加新功能说明**

在README中添加：

```markdown
## 新功能

### 详细比对信息

启用详细比对模式可以查看每个部件的完整比对过程：

```bash
POST /check/{file_id}?enable_detailed=true
```

返回结果包含：
- `comparison_details`: 每个比对步骤的详细记录
- `matched_photos`: 匹配到的照片列表
- `matched_labels`: 匹配到的标签列表
- `match_reason`: 匹配/不匹配的原因

### LLM增强比对

启用大模型(LLM)辅助比对，在OCR识别失败时自动调用LLM：

```bash
POST /check/{file_id}?enable_llm=true
```

环境变量配置：
```bash
ENABLE_LLM_COMPARISON=true
LLM_COMPARISON_MODE=fallback  # fallback/enhance/disabled
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with detailed comparison and LLM features"
```

---

## Final Verification

**Run complete test:**

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.2.9/python_backend
python -c "
from services.report_checker import ReportChecker
from models.schemas import DetailedComponentCheck
from utils.comparison_logger import ComparisonLogger
print('✓ All imports successful')
"
```

**Expected:** All imports successful

---

## Summary

**Changes made:**
1. ✅ Extended data models with `ComparisonDetail`, `DetailedComponentCheck`
2. ✅ Added LLM configuration options in `config.py`
3. ✅ Created `ComparisonLogger` utility for tracking comparison steps
4. ✅ Integrated detailed logging into `_check_components` method
5. ✅ Added LLM-enhanced field comparison with fallback mechanism
6. ✅ Updated API with `enable_detailed` and `enable_llm` parameters
7. ✅ Created test script and updated documentation
