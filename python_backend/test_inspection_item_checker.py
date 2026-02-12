"""
检验项目核对功能测试用例

测试范围：
1. 单元测试：单项结论判定逻辑（符合/不符合/ 三种情况）
2. 单元测试：跨页续表识别逻辑
3. 集成测试：完整 PDF 检验报告核对流程
4. 边界测试：缺少列名、空表格、格式异常等情况

参考文档：REPORT_CHECKER_SPEC.md 第 3.5 节、第 7.3 节
"""

import os
import sys
import json
import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent))


# =============================================================================
# 数据模型定义（用于测试）
# =============================================================================

@dataclass
class RequirementCheck:
    """标准要求核对"""
    requirement_text: str
    inspection_result: str
    remark: str = ""


@dataclass
class ClauseCheck:
    """标准条款核对"""
    clause_number: str
    requirements: List[RequirementCheck] = field(default_factory=list)
    conclusion: str = ""  # 实际单项结论
    expected_conclusion: str = ""  # 期望的单项结论
    is_conclusion_correct: bool = True


@dataclass
class InspectionItemCheck:
    """检验项目核对"""
    item_number: str
    item_name: str
    clauses: List[ClauseCheck] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    status: str = "pass"  # pass/warning/fail


@dataclass
class InspectionItemCheckResult:
    """检验项目核对结果"""
    has_table: bool = False
    total_items: int = 0
    total_clauses: int = 0
    correct_conclusions: int = 0
    incorrect_conclusions: int = 0
    item_checks: List[InspectionItemCheck] = field(default_factory=list)
    cross_page_continuations: int = 0
    errors: List[Dict] = field(default_factory=list)


# =============================================================================
# 被测试的功能（待实现）
# =============================================================================

class InspectionItemChecker:
    """检验项目核对器 - 核心逻辑实现"""

    # 检验项目表格必须包含的7个列名
    REQUIRED_COLUMNS = [
        '序号',
        '检验项目',
        '标准条款',
        '标准要求',
        '检验结果',
        '单项结论',
        '备注'
    ]

    # 续表标记
    CONTINUATION_MARKERS = [
        '续', '续表', '续上表', '续前表'
    ]

    @classmethod
    def detect_inspection_table(cls, headers: List[str]) -> bool:
        """
        检测是否为检验项目表格

        规则：表头必须包含全部7个特定列名

        Args:
            headers: 表格表头列表

        Returns:
            是否为检验项目表格
        """
        if not headers or len(headers) < 7:
            return False

        headers_str = ' '.join(str(h) for h in headers)

        for col in cls.REQUIRED_COLUMNS:
            if col not in headers_str:
                return False

        return True

    @classmethod
    def determine_conclusion(cls, inspection_results: List[str]) -> str:
        """
        根据检验结果判定单项结论

        判定优先级：
        1. 任意"不符合要求" → "不符合"
        2. 全"——"或空白 → "/"
        3. 其他 → "符合"

        Args:
            inspection_results: 该标准条款下所有标准要求的检验结果列表

        Returns:
            期望的单项结论："符合"、"不符合"或"/"
        """
        if not inspection_results:
            return "/"

        # 优先级1：判断是否包含"不符合要求"
        for result in inspection_results:
            result_clean = str(result).strip() if result else ""
            if "不符合" in result_clean and "要求" in result_clean:
                return "不符合"

        # 优先级2：判断是否全为"——"或空白
        all_empty = True
        for result in inspection_results:
            result_clean = str(result).strip() if result else ""
            if result_clean and result_clean != "——":
                all_empty = False
                break

        if all_empty:
            return "/"

        # 优先级3：其他情况
        return "符合"

    @classmethod
    def is_continuation_table(cls, page_header: str, table_text: str) -> bool:
        """
        判断是否为续表

        Args:
            page_header: 页眉文本
            table_text: 表格上方文本

        Returns:
            是否为续表
        """
        combined_text = f"{page_header} {table_text}"

        for marker in cls.CONTINUATION_MARKERS:
            if marker in combined_text:
                return True

        return False

    @classmethod
    def merge_continuation_tables(
        cls,
        base_table: Dict[str, Any],
        continuation_table: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并续表到主表

        规则：
        1. 续表可能无表头，继承上一页表头
        2. 序号为空时继承上一行的序号和检验项目名称
        3. 标准条款为空时继承上一行的标准条款

        Args:
            base_table: 主表数据
            continuation_table: 续表数据

        Returns:
            合并后的表格数据
        """
        merged_rows = base_table.get('rows', []).copy()
        cont_rows = continuation_table.get('rows', [])

        last_item_number = ""
        last_item_name = ""
        last_clause = ""

        # 获取最后一行的信息
        if merged_rows:
            last_row = merged_rows[-1]
            if len(last_row) > 0:
                last_item_number = str(last_row[0]).strip() if last_row[0] else ""
            if len(last_row) > 1:
                last_item_name = str(last_row[1]).strip() if last_row[1] else ""
            if len(last_row) > 2:
                last_clause = str(last_row[2]).strip() if last_row[2] else ""

        for row in cont_rows:
            # 处理序号列
            item_number = str(row[0]).strip() if len(row) > 0 and row[0] else ""
            if item_number:
                last_item_number = item_number
                # 新序号，重置检验项目名称
                if len(row) > 1 and row[1]:
                    last_item_name = str(row[1]).strip()
            else:
                # 继承上一行的序号和检验项目名称
                row[0] = last_item_number
                if len(row) > 1 and not row[1]:
                    row[1] = last_item_name

            # 处理标准条款列
            clause = str(row[2]).strip() if len(row) > 2 and row[2] else ""
            if clause:
                last_clause = clause
            else:
                if len(row) > 2:
                    row[2] = last_clause

            merged_rows.append(row)

        return {
            'headers': base_table.get('headers', []),
            'rows': merged_rows
        }

    @classmethod
    def parse_inspection_table(cls, table_data: Dict[str, Any]) -> InspectionItemCheckResult:
        """
        解析检验项目表格

        Args:
            table_data: 表格数据，包含headers和rows

        Returns:
            检验项目核对结果
        """
        result = InspectionItemCheckResult()
        result.has_table = True

        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])

        if not cls.detect_inspection_table(headers):
            result.has_table = False
            result.errors.append({
                'code': 'TABLE_DETECT_ERROR',
                'message': '未检测到有效的检验项目表格'
            })
            return result

        # 找到各列索引
        col_indices = cls._find_column_indices(headers)

        # 解析数据行
        current_item = None
        last_clause_number = ""

        for row in rows:
            if len(row) < 7:
                continue

            item_number = row[col_indices.get('序号', 0)].strip()
            item_name = row[col_indices.get('检验项目', 1)].strip()
            clause_number = row[col_indices.get('标准条款', 2)].strip()
            requirement_text = row[col_indices.get('标准要求', 3)].strip()
            inspection_result = row[col_indices.get('检验结果', 4)].strip()
            conclusion = row[col_indices.get('单项结论', 5)].strip()
            remark = row[col_indices.get('备注', 6)].strip()

            # 新检验项目（序号存在且与当前不同）
            is_new_item = False
            if item_number:
                if current_item is None or item_number != current_item.item_number:
                    is_new_item = True

            if is_new_item:
                current_item = InspectionItemCheck(
                    item_number=item_number,
                    item_name=item_name
                )
                result.item_checks.append(current_item)
                result.total_items += 1
                last_clause_number = ""  # 重置条款号

            # 新条款（标准条款号存在且与上一个不同）
            if clause_number and current_item:
                if clause_number != last_clause_number:
                    clause = ClauseCheck(clause_number=clause_number)
                    current_item.clauses.append(clause)
                    result.total_clauses += 1
                    last_clause_number = clause_number

            # 添加标准要求
            if current_item and current_item.clauses:
                req = RequirementCheck(
                    requirement_text=requirement_text,
                    inspection_result=inspection_result,
                    remark=remark
                )
                current_item.clauses[-1].requirements.append(req)
                # 只在有结论时更新（续行可能为空）
                if conclusion:
                    current_item.clauses[-1].conclusion = conclusion

        # 核对单项结论
        cls._verify_conclusions(result)

        return result

    @classmethod
    def _find_column_indices(cls, headers: List[str]) -> Dict[str, int]:
        """找到各列的索引"""
        indices = {}
        for idx, header in enumerate(headers):
            header_clean = str(header).strip()
            for col_name in cls.REQUIRED_COLUMNS:
                if col_name in header_clean:
                    indices[col_name] = idx
                    break
        return indices

    @classmethod
    def _verify_conclusions(cls, result: InspectionItemCheckResult):
        """核对所有单项结论"""
        for item in result.item_checks:
            for clause in item.clauses:
                # 收集该条款下所有检验结果
                results = [r.inspection_result for r in clause.requirements]

                # 判定期望结论
                expected = cls.determine_conclusion(results)
                clause.expected_conclusion = expected

                # 核对
                if clause.conclusion == expected:
                    clause.is_conclusion_correct = True
                    result.correct_conclusions += 1
                else:
                    clause.is_conclusion_correct = False
                    result.incorrect_conclusions += 1
                    item.issues.append(
                        f"序号 {item.item_number} 标准条款 {clause.clause_number} "
                        f"单项结论应为 {expected}，实际为 {clause.conclusion}"
                    )
                    item.status = "fail"


# =============================================================================
# 单元测试：单项结论判定逻辑
# =============================================================================

class TestConclusionDetermination:
    """测试单项结论判定逻辑"""

    def test_conclusion_non_compliant_priority(self):
        """测试：任意"不符合要求" → "不符合"（优先级最高）"""
        # 包含"不符合要求"的情况
        results = ["符合要求", "不符合要求", "——"]
        assert InspectionItemChecker.determine_conclusion(results) == "不符合"

        results = ["不符合要求"]
        assert InspectionItemChecker.determine_conclusion(results) == "不符合"

        results = ["不符合要求", "符合要求"]
        assert InspectionItemChecker.determine_conclusion(results) == "不符合"

    def test_conclusion_all_empty(self):
        """测试：全"——"或空白 → /"""
        results = ["——", "——"]
        assert InspectionItemChecker.determine_conclusion(results) == "/"

        results = ["", ""]
        assert InspectionItemChecker.determine_conclusion(results) == "/"

        results = ["——", ""]
        assert InspectionItemChecker.determine_conclusion(results) == "/"

        results = ["   ", "——"]
        assert InspectionItemChecker.determine_conclusion(results) == "/"

    def test_conclusion_compliant(self):
        """测试：其他情况判定为符合"""
        results = ["符合要求"]
        assert InspectionItemChecker.determine_conclusion(results) == "符合"

        results = ["符合要求", "——"]
        assert InspectionItemChecker.determine_conclusion(results) == "符合"

        results = ["100"]
        assert InspectionItemChecker.determine_conclusion(results) == "符合"

        results = ["测试文本"]
        assert InspectionItemChecker.determine_conclusion(results) == "符合"

        results = ["符合要求", "100", "测试数据"]
        assert InspectionItemChecker.determine_conclusion(results) == "符合"

    def test_conclusion_empty_input(self):
        """测试：空输入处理"""
        results = []
        assert InspectionItemChecker.determine_conclusion(results) == "/"

    def test_conclusion_mixed_scenarios(self):
        """测试：混合场景"""
        # 有数值和"——"
        results = ["100", "——"]
        assert InspectionItemChecker.determine_conclusion(results) == "符合"

        # 有文本和"——"
        results = ["测试通过", "——"]
        assert InspectionItemChecker.determine_conclusion(results) == "符合"

        # 有"不符合要求"和数值
        results = ["不符合要求", "100"]
        assert InspectionItemChecker.determine_conclusion(results) == "不符合"


# =============================================================================
# 单元测试：表格检测
# =============================================================================

class TestTableDetection:
    """测试表格检测功能"""

    def test_detect_valid_table(self):
        """测试：正确识别包含7个必需列的表格"""
        headers = ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注']
        assert InspectionItemChecker.detect_inspection_table(headers) is True

    def test_detect_invalid_table_missing_columns(self):
        """测试：缺少列名时不应识别为检验项目表格"""
        # 缺少"单项结论"
        headers = ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '备注']
        assert InspectionItemChecker.detect_inspection_table(headers) is False

        # 缺少"标准条款"
        headers = ['序号', '检验项目', '标准要求', '检验结果', '单项结论', '备注']
        assert InspectionItemChecker.detect_inspection_table(headers) is False

    def test_detect_empty_headers(self):
        """测试：空表头处理"""
        assert InspectionItemChecker.detect_inspection_table([]) is False
        assert InspectionItemChecker.detect_inspection_table(None) is False

    def test_detect_insufficient_columns(self):
        """测试：列数不足"""
        headers = ['序号', '检验项目', '标准条款']
        assert InspectionItemChecker.detect_inspection_table(headers) is False


# =============================================================================
# 单元测试：跨页续表处理
# =============================================================================

class TestContinuationTable:
    """测试跨页续表处理"""

    def test_detect_continuation_table(self):
        """测试：续表标记识别"""
        # 页眉包含"续"
        assert InspectionItemChecker.is_continuation_table("续", "") is True

        # 表格上方包含"续表"
        assert InspectionItemChecker.is_continuation_table("", "续表") is True

        # 包含"续上表"
        assert InspectionItemChecker.is_continuation_table("", "续上表") is True

        # 包含"续前表"
        assert InspectionItemChecker.is_continuation_table("", "续前表") is True

    def test_not_continuation_table(self):
        """测试：非续表识别"""
        assert InspectionItemChecker.is_continuation_table("检验报告", "") is False
        assert InspectionItemChecker.is_continuation_table("", "") is False

    def test_merge_continuation_with_item_number(self):
        """测试：续表合并 - 有序号的情况"""
        base_table = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '项目A', '条款1', '要求1', '符合要求', '符合', ''],
                ['2', '项目B', '条款2', '要求2', '——', '/', '']
            ]
        }

        continuation = {
            'rows': [
                ['3', '项目C', '条款3', '要求3', '符合要求', '符合', '']
            ]
        }

        merged = InspectionItemChecker.merge_continuation_tables(base_table, continuation)

        assert len(merged['rows']) == 3
        assert merged['rows'][2][0] == '3'
        assert merged['rows'][2][1] == '项目C'

    def test_merge_continuation_inherit_item(self):
        """测试：续表合并 - 序号为空时继承"""
        base_table = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '项目A', '条款1', '要求1', '符合要求', '符合', '']
            ]
        }

        # 续表序号为空，应继承上一行的序号和检验项目
        continuation = {
            'rows': [
                ['', '', '条款2', '要求2', '——', '/', '']
            ]
        }

        merged = InspectionItemChecker.merge_continuation_tables(base_table, continuation)

        assert len(merged['rows']) == 2
        assert merged['rows'][1][0] == '1'  # 继承序号
        assert merged['rows'][1][1] == '项目A'  # 继承检验项目
        assert merged['rows'][1][2] == '条款2'  # 自己的标准条款

    def test_merge_continuation_inherit_clause(self):
        """测试：续表合并 - 标准条款为空时继承"""
        base_table = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '项目A', '条款1', '要求1', '符合要求', '符合', '']
            ]
        }

        # 标准条款为空，应继承上一行的标准条款
        continuation = {
            'rows': [
                ['', '', '', '要求2', '——', '/', '']
            ]
        }

        merged = InspectionItemChecker.merge_continuation_tables(base_table, continuation)

        assert merged['rows'][1][2] == '条款1'  # 继承标准条款


# =============================================================================
# 单元测试：表格解析与核对
# =============================================================================

class TestTableParsing:
    """测试表格解析功能"""

    def test_parse_valid_table(self):
        """测试：正确解析检验项目表格"""
        table_data = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '外观检查', 'GB/T 1.1', '表面无损伤', '符合要求', '符合', ''],
                ['2', '尺寸测量', 'GB/T 1.2', '长度100mm', '100', '符合', ''],
                ['3', '性能测试', 'GB/T 1.3', '耐压测试', '——', '/', '']
            ]
        }

        result = InspectionItemChecker.parse_inspection_table(table_data)

        assert result.has_table is True
        assert result.total_items == 3
        assert result.correct_conclusions == 3
        assert result.incorrect_conclusions == 0

    def test_parse_with_wrong_conclusion(self):
        """测试：检测单项结论错误"""
        table_data = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '外观检查', 'GB/T 1.1', '表面无损伤', '符合要求', '符合', ''],
                # 错误：全为"——"应标记为"/"，但标记为"符合"
                ['2', '尺寸测量', 'GB/T 1.2', '长度', '——', '符合', '']
            ]
        }

        result = InspectionItemChecker.parse_inspection_table(table_data)

        assert result.correct_conclusions == 1
        assert result.incorrect_conclusions == 1
        assert result.item_checks[1].status == "fail"

    def test_parse_non_compliant_case(self):
        """测试：检测"不符合"情况"""
        table_data = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '性能测试', 'GB/T 1.1', '耐压测试', '不符合要求', '不符合', ''],
                # 错误：有"不符合要求"但标记为"符合"
                ['2', '安全测试', 'GB/T 1.2', '绝缘测试', '不符合要求', '符合', '']
            ]
        }

        result = InspectionItemChecker.parse_inspection_table(table_data)

        assert result.item_checks[0].status == "pass"
        assert result.item_checks[1].status == "fail"

    def test_parse_invalid_table(self):
        """测试：无效表格处理"""
        table_data = {
            'headers': ['列1', '列2', '列3'],
            'rows': [['a', 'b', 'c']]
        }

        result = InspectionItemChecker.parse_inspection_table(table_data)

        assert result.has_table is False
        assert len(result.errors) > 0


# =============================================================================
# 边界测试
# =============================================================================

class TestEdgeCases:
    """测试边界情况"""

    def test_empty_table(self):
        """测试：空表格"""
        table_data = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': []
        }

        result = InspectionItemChecker.parse_inspection_table(table_data)

        assert result.has_table is True
        assert result.total_items == 0

    def test_table_with_empty_rows(self):
        """测试：包含空行的表格"""
        table_data = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '项目A', '条款1', '要求1', '符合要求', '符合', ''],
                [],  # 空行
                ['', '', '', '', '', '', ''],  # 全空行
                ['2', '项目B', '条款2', '要求2', '——', '/', '']
            ]
        }

        result = InspectionItemChecker.parse_inspection_table(table_data)

        assert result.total_items == 2

    def test_multi_requirements_per_clause(self):
        """测试：一个标准条款下有多个标准要求"""
        table_data = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '综合测试', 'GB/T 1.1', '要求1', '符合要求', '符合', ''],
                ['', '', '', '要求2', '——', '', ''],  # 同一条款的不同要求
                ['', '', '', '要求3', '100', '', '']
            ]
        }

        result = InspectionItemChecker.parse_inspection_table(table_data)

        assert result.total_items == 1
        assert len(result.item_checks[0].clauses) == 1
        assert len(result.item_checks[0].clauses[0].requirements) == 3

    def test_special_characters_in_results(self):
        """测试：检验结果包含特殊字符"""
        results = ["符合要求\n", "  符合要求  ", "——\r\n"]
        assert InspectionItemChecker.determine_conclusion(results) == "符合"

        results = ["不符合要求 ", " 不符合要求"]
        assert InspectionItemChecker.determine_conclusion(results) == "不符合"


# =============================================================================
# 集成测试：完整核对流程
# =============================================================================

class TestIntegration:
    """集成测试"""

    def test_full_check_workflow(self):
        """测试：完整核对流程"""
        # 模拟完整的检验项目表格数据
        table_data = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '外观检查', 'GB/T 1.1-2024', '表面无划痕', '符合要求', '符合', ''],
                ['2', '尺寸偏差', 'GB/T 1.2-2024', '长度100±0.5mm', '100.2', '符合', ''],
                ['3', '耐压测试', 'GB/T 1.3-2024', '耐压500V', '——', '/', '不适用'],
                ['4', '绝缘测试', 'GB/T 1.4-2024', '绝缘电阻>10MΩ', '不符合要求', '不符合', '需返工'],
                # 错误案例
                ['5', '接地测试', 'GB/T 1.5-2024', '接地电阻<0.1Ω', '——', '符合', '']  # 应为"/"
            ]
        }

        result = InspectionItemChecker.parse_inspection_table(table_data)

        # 验证统计
        assert result.total_items == 5
        assert result.correct_conclusions == 4
        assert result.incorrect_conclusions == 1

        # 验证具体错误
        error_item = result.item_checks[4]
        assert error_item.status == "fail"
        assert "单项结论应为 /" in error_item.issues[0]

    def test_cross_page_table_integration(self):
        """测试：跨页表格完整流程"""
        # 第一页表格
        page1_table = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '外观检查', 'GB/T 1.1', '表面无划痕', '符合要求', '符合', ''],
                ['2', '尺寸偏差', 'GB/T 1.2', '长度100mm', '100', '符合', '']
            ]
        }

        # 第二页续表（无表头，序号延续）
        page2_table = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['3', '耐压测试', 'GB/T 1.3', '耐压500V', '——', '/', ''],
                # 续行：序号为空，继承上一行，单项结论与主行一致
                ['', '', '', '耐压1000V', '符合要求', '/', '']
            ]
        }

        # 检测是否为续表
        is_cont = InspectionItemChecker.is_continuation_table("续表 2", "")
        assert is_cont is True

        # 合并表格
        merged = InspectionItemChecker.merge_continuation_tables(page1_table, page2_table)

        # 解析合并后的表格
        result = InspectionItemChecker.parse_inspection_table(merged)

        # 验证：合并后应有4行，但解析为3个检验项目（序号3有两条标准要求）
        assert result.total_items == 3
        # 序号3有两条标准要求，属于同一个条款
        item_3 = result.item_checks[2]
        assert item_3.item_number == '3'
        assert len(item_3.clauses) == 1
        assert len(item_3.clauses[0].requirements) == 2


# =============================================================================
# 测试数据工厂
# =============================================================================

class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_normal_table() -> Dict[str, Any]:
        """创建正常表格数据"""
        return {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '外观检查', 'GB/T 1.1', '表面无划痕', '符合要求', '符合', ''],
                ['2', '尺寸测量', 'GB/T 1.2', '长度100mm', '100.2', '符合', ''],
                ['3', '耐压测试', 'GB/T 1.3', '耐压500V', '——', '/', '不适用']
            ]
        }

    @staticmethod
    def create_non_compliant_table() -> Dict[str, Any]:
        """创建包含"不符合要求"的表格"""
        return {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '性能测试', 'GB/T 1.1', '耐压测试', '不符合要求', '不符合', '需返工'],
                ['2', '绝缘测试', 'GB/T 1.2', '绝缘电阻', '不符合要求', '不符合', '不合格']
            ]
        }

    @staticmethod
    def create_all_empty_table() -> Dict[str, Any]:
        """创建全为"——"的表格"""
        return {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '不适用项1', 'GB/T 1.1', '要求1', '——', '/', ''],
                ['2', '不适用项2', 'GB/T 1.2', '要求2', '——', '/', ''],
                ['3', '不适用项3', 'GB/T 1.3', '要求3', '——', '/', '']
            ]
        }

    @staticmethod
    def create_wrong_conclusion_table() -> Dict[str, Any]:
        """创建包含错误单项结论的表格"""
        return {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                # 正确：全"——"标记为"/"
                ['1', '测试1', 'GB/T 1.1', '要求1', '——', '/', ''],
                # 错误：全"——"但标记为"符合"
                ['2', '测试2', 'GB/T 1.2', '要求2', '——', '符合', ''],
                # 错误：有"不符合要求"但标记为"符合"
                ['3', '测试3', 'GB/T 1.3', '要求3', '不符合要求', '符合', ''],
                # 错误：有实际结果但标记为"/"
                ['4', '测试4', 'GB/T 1.4', '要求4', '符合要求', '/', '']
            ]
        }

    @staticmethod
    def create_cross_page_table() -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """创建跨页续表数据"""
        page1 = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['1', '外观检查', 'GB/T 1.1', '表面无划痕', '符合要求', '符合', ''],
                ['2', '尺寸测量', 'GB/T 1.2', '长度100mm', '100', '符合', '']
            ]
        }

        page2 = {
            'headers': ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            'rows': [
                ['3', '耐压测试', 'GB/T 1.3', '耐压500V', '——', '/', ''],
                # 续行：单项结论应与主行一致（都是针对同一标准条款的不同要求）
                ['', '', '', '耐压1000V', '符合要求', '/', ''],
                ['4', '绝缘测试', 'GB/T 1.4', '绝缘电阻', '10MΩ', '符合', '']
            ]
        }

        return page1, page2

    @staticmethod
    def create_missing_header_table() -> Dict[str, Any]:
        """创建缺少表头的续表"""
        return {
            'headers': ['', '', '', '', '', '', ''],  # 空表头
            'rows': [
                ['5', '接地测试', 'GB/T 1.5', '接地电阻', '0.05Ω', '符合', '']
            ]
        }


# =============================================================================
# 使用测试数据工厂的测试用例
# =============================================================================

class TestWithFactoryData:
    """使用工厂数据的测试"""

    def test_normal_table_all_correct(self):
        """测试：正常表格所有判定正确"""
        table = TestDataFactory.create_normal_table()
        result = InspectionItemChecker.parse_inspection_table(table)

        assert result.total_items == 3
        assert result.incorrect_conclusions == 0
        assert all(item.status == "pass" for item in result.item_checks)

    def test_non_compliant_detection(self):
        """测试：正确识别不符合要求的情况"""
        table = TestDataFactory.create_non_compliant_table()
        result = InspectionItemChecker.parse_inspection_table(table)

        assert result.total_items == 2
        for item in result.item_checks:
            for clause in item.clauses:
                assert clause.expected_conclusion == "不符合"
                assert clause.is_conclusion_correct is True

    def test_all_empty_detection(self):
        """测试：正确识别全"——"情况"""
        table = TestDataFactory.create_all_empty_table()
        result = InspectionItemChecker.parse_inspection_table(table)

        assert result.total_items == 3
        for item in result.item_checks:
            for clause in item.clauses:
                assert clause.expected_conclusion == "/"
                assert clause.is_conclusion_correct is True

    def test_wrong_conclusion_errors(self):
        """测试：正确检测所有类型的单项结论错误"""
        table = TestDataFactory.create_wrong_conclusion_table()
        result = InspectionItemChecker.parse_inspection_table(table)

        # 应该有3个错误（第2、3、4行）
        assert result.correct_conclusions == 1
        assert result.incorrect_conclusions == 3

        # 验证具体错误类型
        error_types = []
        for item in result.item_checks:
            for issue in item.issues:
                if "应为 /" in issue:
                    error_types.append("CONCLUSION_MISMATCH_001")
                elif "应为 符合" in issue:
                    error_types.append("CONCLUSION_MISMATCH_002")
                elif "应为 不符合" in issue:
                    error_types.append("CONCLUSION_MISMATCH_003")

        assert "CONCLUSION_MISMATCH_001" in error_types  # 应标为"/"但标为其他
        assert "CONCLUSION_MISMATCH_002" in error_types  # 应标为"符合"但标为其他
        assert "CONCLUSION_MISMATCH_003" in error_types  # 应标为"不符合"但标为其他

    def test_cross_page_merge(self):
        """测试：跨页续表合并"""
        page1, page2 = TestDataFactory.create_cross_page_table()

        # 合并
        merged = InspectionItemChecker.merge_continuation_tables(page1, page2)

        # 验证总行数
        assert len(merged['rows']) == 5

        # 验证继承逻辑
        # 第4行（索引3）是续行，应继承序号3和检验项目"耐压测试"
        assert merged['rows'][3][0] == '3'
        assert merged['rows'][3][1] == '耐压测试'

        # 解析合并后的表格
        result = InspectionItemChecker.parse_inspection_table(merged)

        # 验证：序号3应有两条标准要求
        item_3 = result.item_checks[2]
        assert item_3.item_number == '3'
        assert len(item_3.clauses) == 1
        assert len(item_3.clauses[0].requirements) == 2


# =============================================================================
# 测试报告模板
# =============================================================================

class TestReportTemplate:
    """测试报告模板"""

    @staticmethod
    def generate_report(test_results: List[Dict]) -> str:
        """生成测试报告"""
        report_lines = [
            "=" * 80,
            "检验项目核对功能测试报告",
            "=" * 80,
            f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "一、测试概述",
            "-" * 80,
            f"总测试用例数: {len(test_results)}",
            f"通过: {sum(1 for r in test_results if r.get('passed', False))}",
            f"失败: {sum(1 for r in test_results if not r.get('passed', False))}",
            "",
            "二、测试覆盖",
            "-" * 80,
            "[✓] 表格检测正确识别7列表头",
            "[✓] 单项结论判定：'不符合'优先级最高",
            "[✓] 单项结论判定：全'——'判定为'/'",
            "[✓] 单项结论判定：其他情况判定为'符合'",
            "[✓] 跨页续表正确合并",
            "[✓] 错误结果正确标记",
            "",
            "三、详细测试结果",
            "-" * 80,
        ]

        for i, result in enumerate(test_results, 1):
            status = "✓ PASS" if result.get('passed') else "✗ FAIL"
            report_lines.extend([
                f"\n测试 #{i}: {result.get('name', 'Unknown')}",
                f"状态: {status}",
                f"描述: {result.get('description', '')}",
            ])

            if result.get('error'):
                report_lines.append(f"错误: {result['error']}")

        report_lines.extend([
            "",
            "=" * 80,
            "测试完成",
            "=" * 80,
        ])

        return "\n".join(report_lines)


# =============================================================================
# 主程序入口
# =============================================================================

def run_all_tests():
    """运行所有测试并生成报告"""
    print("=" * 80)
    print("检验项目核对功能测试")
    print("=" * 80)

    # 使用pytest运行测试
    import subprocess

    result = subprocess.run(
        ['python', '-m', 'pytest', __file__, '-v', '--tb=short'],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    print(f"\n返回码: {result.returncode}")
    return result.returncode == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
