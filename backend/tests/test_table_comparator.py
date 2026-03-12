"""
Tests for Table Comparator module.

Tests table expansion, parameter comparison, and value extraction.
"""

import pytest

from app.models.ptr_models import (
    PTRClause,
    PTRClauseNumber,
    PTRDocument,
    PTRTable,
    PTRTableReference,
)
from app.models.report_models import InspectionItem
from app.services.ptr_extractor import PTRExtractor
from app.services.table_comparator import (
    TableComparator,
    ParameterComparison,
    TableExpansionResult,
    compare_table_expansions,
    get_table_expansion_summary,
)


class TestParameterComparison:
    """Test ParameterComparison model."""

    def test_creation(self):
        """Test creating parameter comparison."""
        comp = ParameterComparison(
            parameter_name="Test",
            ptr_value="100",
            report_value="100",
            matches=True,
        )
        assert comp.parameter_name == "Test"
        assert comp.ptr_value == "100"
        assert comp.report_value == "100"
        assert comp.matches is True
        assert comp.is_expanded is False


class TestTableExpansionResult:
    """Test TableExpansionResult model."""

    def test_creation(self):
        """Test creating table expansion result."""
        result = TableExpansionResult(
            table_number=1,
            table_found=True,
        )
        assert result.table_number == 1
        assert result.table_found is True

    def test_all_match_property(self):
        """Test all_match property."""
        result1 = TableExpansionResult(
            table_number=1,
            table_found=True,
            total_parameters=2,
            total_matches=2,
        )
        assert result1.all_match is True

        result2 = TableExpansionResult(
            table_number=1,
            table_found=True,
            total_parameters=2,
            total_matches=1,
        )
        assert result2.all_match is False

    def test_match_rate_property(self):
        """Test match_rate property."""
        result1 = TableExpansionResult(
            table_number=1,
            table_found=True,
            total_parameters=4,
            total_matches=2,
        )
        assert result1.match_rate == 0.5

        result2 = TableExpansionResult(
            table_number=1,
            table_found=True,
            total_parameters=0,
            total_matches=0,
        )
        assert result2.match_rate == 0.0


class TestTableComparator:
    """Test TableComparator class."""

    def test_comparator_initialization(self):
        """Test comparator can be initialized."""
        comparator = TableComparator()
        assert comparator.normalizer is not None

    def test_compare_empty_documents(self):
        """Test comparing with empty data."""
        ptr_doc = PTRDocument()
        report_items = []

        comparator = TableComparator()
        results = comparator.compare_table_references(ptr_doc, report_items)

        assert isinstance(results, list)
        assert len(results) == 0

    def test_compare_values(self):
        """Test value comparison."""
        comparator = TableComparator()

        assert comparator._compare_values("100", "100") is True
        assert comparator._compare_values("100", "200") is False
        assert comparator._compare_values("", "") is True
        assert comparator._compare_values("100", "") is False

    def test_compare_values_with_normalization(self):
        """Test value comparison with normalization."""
        comparator = TableComparator()

        # Full-width numbers should match
        assert comparator._compare_values("１００", "100") is True

        # Extra whitespace should be normalized
        assert comparator._compare_values("Test  Value", "Test Value") is True

    def test_compare_values_numeric_constraints(self):
        """Comparator/range/tolerance expressions should be semantically evaluated."""
        comparator = TableComparator()

        assert comparator._compare_values("≤2.0mL", "1.1mL") is True
        assert comparator._compare_values("≤2.0mL", "2.5mL") is False

        assert comparator._compare_values("20~350", "180") is True
        assert comparator._compare_values("20-350", "10") is False

        assert comparator._compare_values("100±20%", "120") is True
        assert comparator._compare_values("100±20%", "130") is False

        assert comparator._compare_values("/", "——") is True

    def test_compare_values_should_support_real_numeric_report_patterns(self):
        comparator = TableComparator()

        assert comparator._compare_values("2.5±0.1", "+0.03") is True
        assert comparator._compare_values("2.5±0.1", "-0.02~+0.06") is True
        assert comparator._compare_values("180±20°", "+6~+9") is True
        assert comparator._compare_values("≥10", "17~46") is True
        assert comparator._compare_values("≥15", "50~55") is True
        assert comparator._compare_values("≤2.0mL", "0.4mL") is True
        assert comparator._compare_values("≤20EU/套", "<20") is True
        assert comparator._compare_values("≤10Ω", "6Ω") is True
        assert comparator._compare_values("2m±0.05m", "+0.02m") is True
        assert comparator._compare_values("6.5mm±0.5mm", "-0.2~+0.0mm") is True

    def test_extract_parameter_value(self):
        """Test parameter value extraction."""
        comparator = TableComparator()

        # Pattern: "参数: 值"
        result = comparator._extract_parameter_value(
            "频率",
            "频率: 100MHz"
        )
        assert "100MHz" in result or "100" in result

        # Pattern: "参数 值"
        result = comparator._extract_parameter_value(
            "电压",
            "电压 220V"
        )
        assert "220V" in result or "220" in result

    def test_extract_parameter_value_multiline(self):
        """Parameter value can appear on the next line."""
        comparator = TableComparator()
        text = "频率\n100Hz\n电压\n220V"
        result = comparator._extract_parameter_value("电压", text)
        assert "220" in result

    def test_extract_parameter_value_not_found(self):
        """Test when parameter is not found."""
        comparator = TableComparator()

        result = comparator._extract_parameter_value(
            "NotFound",
            "Some other text"
        )
        assert result == ""

    def test_find_matching_report_item(self):
        """Test finding matching report item."""
        comparator = TableComparator()

        # Create clause
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test",
            text_content="Test",
            level=2,
        )

        # Create report items
        items = [
            InspectionItem(sequence_number="2.1", inspection_project="Test Item"),
            InspectionItem(sequence_number="2.2", inspection_project="Other Item"),
        ]

        found = comparator._find_matching_report_item(clause, items)
        assert found is not None
        assert found.sequence_number == "2.1"

    def test_find_matching_report_item_not_found(self):
        """Test when no matching item is found."""
        comparator = TableComparator()

        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test",
            text_content="Test",
            level=2,
        )

        items = [
            InspectionItem(sequence_number="3.1", inspection_project="Different"),
        ]

        found = comparator._find_matching_report_item(clause, items)
        assert found is None


class TestTableReferenceComparison:
    """Test table reference comparison."""

    def test_compare_table_reference_not_found(self):
        """Test when referenced table is not found."""
        ptr_doc = PTRDocument()
        report_items = []

        # Create clause with table reference
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test 见表1",
            text_content="Test 见表1",
            level=2,
            table_references=[PTRTableReference(table_number=1)],
        )
        ptr_doc.clauses.append(clause)

        comparator = TableComparator()
        result = comparator._compare_table_reference(
            1, clause, ptr_doc, report_items
        )

        assert result.table_number == 1
        assert result.table_found is False
        assert result.clause_number == "2.1"

    def test_compare_table_reference_found(self):
        """Test when referenced table is found."""
        ptr_doc = PTRDocument()

        # Add table to PTR
        table = PTRTable(
            table_number=1,
            headers=["参数", "值"],
            rows=[["频率", "100MHz"]],
        )
        ptr_doc.tables.append(table)

        # Create clause with table reference
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test 见表1",
            text_content="Test 见表1",
            level=2,
            table_references=[PTRTableReference(table_number=1)],
        )
        ptr_doc.clauses.append(clause)

        # Create matching report item
        report_items = [
            InspectionItem(
                sequence_number="2.1",
                test_result="频率: 100MHz",
            )
        ]

        comparator = TableComparator()
        result = comparator._compare_table_reference(
            1, clause, ptr_doc, report_items
        )

        assert result.table_number == 1
        assert result.table_found is True
        assert result.total_parameters >= 0
        assert result.clause_number == "2.1"

    def test_compare_table_references_should_ignore_non_main_requirement_clauses(self):
        ptr_doc = PTRDocument()
        ptr_doc.clauses.extend(
            [
                PTRClause(
                    number=PTRClauseNumber.from_string("2.1.3"),
                    full_text="2.1.3 断裂力见表1",
                    text_content="断裂力见表1",
                    level=3,
                    clause_type="main_requirement",
                    table_references=[PTRTableReference(table_number=1)],
                ),
                PTRClause(
                    number=PTRClauseNumber.from_string("2.2.1"),
                    full_text="2.2.1 将测试系统按图1进行安装，见表1",
                    text_content="将测试系统按图1进行安装，见表1",
                    level=3,
                    clause_type="test_method",
                    table_references=[PTRTableReference(table_number=1)],
                ),
            ]
        )
        ptr_doc.tables.append(
            PTRTable(
                table_number=1,
                headers=["参数", "值"],
                rows=[["断裂力", "≥10N"]],
            )
        )

        report_items = [
            InspectionItem(
                sequence_number="12",
                standard_clause="2.1.3",
                inspection_project="断裂力",
                test_result="17~46N",
            )
        ]

        results = TableComparator().compare_table_references(ptr_doc, report_items)

        assert len(results) == 1
        assert results[0].clause_number == "2.1.3"

    def test_compare_table_reference_should_select_best_candidate_when_duplicate_number(self):
        """When duplicate table numbers exist, should pick parameter table not narrative table."""
        ptr_doc = PTRDocument()
        ptr_doc.tables.extend(
            [
                PTRTable(
                    table_number=1,
                    headers=["该产品和植入式系统属于磁共振安全医疗器械..."],
                    rows=[["器械类型", "植入式心脏起搏器"]],
                    page=2,
                ),
                PTRTable(
                    table_number=1,
                    headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
                    rows=[["脉冲宽度(ms)", "全部型号", "0.1...1.5", "0.4", "±20μs"]],
                    page=3,
                ),
            ]
        )

        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
            table_references=[PTRTableReference(table_number=1)],
        )
        ptr_doc.clauses.append(clause)

        report_items = [
            InspectionItem(
                sequence_number="39",
                standard_clause="2.1.3",
                test_result="脉冲宽度(ms) 0.4",
            )
        ]

        comparator = TableComparator()
        result = comparator._compare_table_reference(1, clause, ptr_doc, report_items)
        assert result.table_found is True
        assert result.total_parameters >= 1
        # If narrative table was selected, parameter name would not be 脉冲宽度.
        assert any("脉冲宽度" in p.parameter_name for p in result.parameters)

    def test_compare_table_reference_should_prefer_chapter2_table_then_fallback(self):
        """For duplicated 表1 across chapters, should prioritize chapter-2 table candidates."""
        ptr_doc = PTRDocument(chapter2_start=4, chapter2_end=10)
        ptr_doc.tables.extend(
            [
                # Chapter 1 table 1 (same number, wrong context)
                PTRTable(
                    table_number=1,
                    headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
                    rows=[["脉冲宽度(ms)", "全部型号", "0.1...1.5", "9.9", "±20μs"]],
                    page=2,
                ),
                # Chapter 2 table 1 (target)
                PTRTable(
                    table_number=1,
                    headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
                    rows=[["脉冲宽度(ms)", "全部型号", "0.1...1.5", "0.4", "±20μs"]],
                    page=5,
                ),
            ]
        )

        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
            table_references=[PTRTableReference(table_number=1)],
        )
        ptr_doc.clauses.append(clause)

        report_items = [
            InspectionItem(
                sequence_number="39",
                standard_clause="2.1.3",
                test_result="脉冲宽度(ms) 标准设置 0.4",
            )
        ]

        comparator = TableComparator()
        result = comparator._compare_table_reference(1, clause, ptr_doc, report_items)
        assert result.table_found is True
        assert result.parameters
        # Should come from chapter-2 table candidate.
        assert any(p.ptr_value == "0.4" for p in result.parameters)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_compare_table_expansions(self):
        """Test compare_table_expansions function."""
        ptr_doc = PTRDocument()
        report_items = []

        results = compare_table_expansions(ptr_doc, report_items)
        assert isinstance(results, list)

    def test_get_table_expansion_summary(self):
        """Test get_table_expansion_summary function."""
        results = [
            TableExpansionResult(
                table_number=1,
                table_found=True,
                total_parameters=4,
                total_matches=4,
            ),
            TableExpansionResult(
                table_number=2,
                table_found=True,
                total_parameters=4,
                total_matches=2,
            ),
        ]

        summary = get_table_expansion_summary(results)

        assert summary["total_tables"] == 2
        assert summary["found_tables"] == 2
        assert summary["total_parameters"] == 8
        assert summary["total_matches"] == 6
        assert summary["match_rate"] == 0.75

    def test_get_table_expansion_summary_empty(self):
        """Test summary with empty results."""
        summary = get_table_expansion_summary([])

        assert summary["total_tables"] == 0
        assert summary["found_tables"] == 0
        assert summary["total_parameters"] == 0
        assert summary["total_matches"] == 0
        assert summary["match_rate"] == 0.0


class TestEdgeCases:
    """Test edge cases."""

    def test_compare_with_empty_table(self):
        """Test comparing with empty PTR table."""
        ptr_doc = PTRDocument()

        table = PTRTable(
            table_number=1,
            headers=[],
            rows=[],
        )
        ptr_doc.tables.append(table)

        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test",
            text_content="Test",
            level=2,
            table_references=[PTRTableReference(table_number=1)],
        )
        ptr_doc.clauses.append(clause)

        report_items = [
            InspectionItem(sequence_number="2.1"),
        ]

        comparator = TableComparator()
        results = comparator.compare_table_references(ptr_doc, report_items)

        assert len(results) >= 0

    def test_compare_with_empty_parameter_name(self):
        """Test handling rows with empty parameter names."""
        comparator = TableComparator()

        report_item = InspectionItem(
            sequence_number="1",
            test_result="Some text",
        )

        # Empty parameter name should not crash
        value = comparator._extract_parameter_value("", report_item.test_result)
        assert value == ""

    def test_compare_with_special_characters(self):
        """Test comparing values with special characters."""
        comparator = TableComparator()

        # Values with units and special characters
        assert comparator._compare_values("100Ω", "100Ω") is True
        assert comparator._compare_values("±5%", "±5%") is True

    def test_compare_with_multiple_parameters(self):
        """Test extracting and comparing multiple parameters."""
        ptr_doc = PTRDocument()

        table = PTRTable(
            table_number=1,
            headers=["参数", "值"],
            rows=[
                ["频率", "100MHz"],
                ["电压", "220V"],
                ["功率", "10W"],
            ],
        )
        ptr_doc.tables.append(table)

        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test",
            text_content="Test",
            level=2,
            table_references=[PTRTableReference(table_number=1)],
        )
        ptr_doc.clauses.append(clause)

        report_text = "频率: 100MHz, 电压: 220V, 功率: 10W"
        report_items = [
            InspectionItem(
                sequence_number="2.1",
                test_result=report_text,
            )
        ]

        comparator = TableComparator()
        results = comparator.compare_table_references(ptr_doc, report_items)

        if results and results[0].table_found:
            assert results[0].total_parameters == 3

    def test_pick_ptr_value_should_prefer_standard_setting_column(self):
        """For 5-column parameter tables, value should prioritize 标准设置 over 型号."""
        comparator = TableComparator()
        headers = ["参数", "型号", "常规数值", "标准设置", "允许误差"]
        row = ["脉冲宽度(ms)", "全部型号", "0.1...1.5", "0.4", "±20μs"]

        picked = comparator._pick_ptr_value_from_row(row, headers=headers)
        assert picked == "0.4"

    def test_compare_table_parameters_should_filter_rows_by_clause_topic(self):
        """Only parameter rows related to clause topic should be compared."""
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["脉冲宽度(ms)", "全部型号", "0.1...1.5", "0.4", "±20μs"],
                ["基础频率(bpm)", "全部型号", "30...200", "60", "±20ms"],
            ],
        )
        report_item = InspectionItem(
            sequence_number="39",
            standard_clause="2.1.3",
            test_result="脉冲宽度(ms) 标准设置 0.4",
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
        )
        assert len(comparisons) == 1
        assert comparisons[0].parameter_name.startswith("脉冲宽度")

    def test_compare_table_parameters_should_not_fallback_to_first_rows_when_topic_has_no_match(self):
        """Table-reference evidence must not default to unrelated leading rows when clause topic is explicit."""
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["起搏模式", "Edora 8 DR", "DDDR", "DDDR", "/"],
                ["脉冲宽度(ms)", "全部型号", "0.1...1.5", "0.4", "±20μs"],
            ],
        )
        report_item = InspectionItem(
            sequence_number="46",
            standard_clause="2.1.12",
            inspection_project="心室后心房不应期（PVARP）",
            standard_requirement="心室后心房不应期应符合表1中的数值。",
            test_result="-15～-12",
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.12"),
            full_text="2.1.12 心室后心房不应期（PVARP）",
            text_content="心室后心房不应期（PVARP）：心室后心房不应期应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
            report_items=[report_item],
        )

        assert comparisons == []

    def test_compare_table_parameters_should_use_coverage_mode_with_extra_report_content(self):
        """Report may contain extra formulas/details; core PTR row content appearing should pass."""
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["脉冲宽度(ms)", "全部型号", "0.1...(0.1)...0.5...(0.25)...1.5", "0.4", "±20μs或±10%中取较大值"],
            ],
        )
        report_item = InspectionItem(
            sequence_number="39",
            standard_clause="2.1.3",
            standard_requirement=(
                "脉冲宽度应符合表1中的数值。"
                "脉冲宽度(ms)（心房）常规数值：0.1 ...(0.1) ... 0.5 ...(0.25) ... 1.5；"
                "标准设置：0.4；允许误差：±20μs 或 ±10%中取较大值；"
                "并给出@240Ω/@500Ω/@2000Ω等附加测试结果。"
            ),
            test_result="符合要求",
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
            report_items=[report_item],
        )
        assert len(comparisons) == 1
        assert comparisons[0].matches is True
        assert comparisons[0].details["referenced_table_label"] == "表1"
        assert comparisons[0].details["ptr_parameter_name"] == "脉冲宽度(ms)"

    def test_compare_table_parameters_should_keep_multiple_report_evidence_segments(self):
        """One matched parameter should preserve multiple report evidence segments for display."""
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["脉冲宽度(ms)", "全部型号", "0.1...(0.1)...1.5", "0.4", "±20μs"],
            ],
        )
        head_row = InspectionItem(
            sequence_number="39",
            standard_clause="2.1.3",
            standard_requirement="脉冲宽度应符合表1中的数值。",
            inspection_project="脉冲宽度(ms)",
        )
        continuation_rows = [
            InspectionItem(
                sequence_number="",
                inspection_project="",
                standard_requirement="脉冲宽度(ms)（心房）\n常规数值：0.1...(0.1)...1.5\n标准设置：0.4",
                test_result="允许误差：±20μs\n@240Ω 0.1ms：±20μs",
            ),
            InspectionItem(
                sequence_number="",
                inspection_project="",
                standard_requirement="脉冲宽度(ms)（右室）\n常规数值：0.1...(0.1)...1.5\n标准设置：0.4",
                test_result="允许误差：±20μs\n@500Ω 0.2ms～1.5ms：±10%",
            ),
        ]
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=head_row,
            clause=clause,
            report_items=[head_row, *continuation_rows],
        )

        assert len(comparisons) == 1
        evidence_rows = comparisons[0].details["report_evidence_rows"]
        assert len(evidence_rows) >= 2
        assert "心房" in evidence_rows[0]["label"]
        assert "右室" in evidence_rows[1]["label"]

    def test_table_summary_reference_should_not_require_single_parameter_match(self):
        comparator = TableComparator()
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.2"),
            full_text="2.1.2 尺寸",
            text_content="尺寸具体要求见表1。\n组件\n项目\n接收标准\n导管有效长度L",
            level=3,
            table_references=[PTRTableReference(table_number=1)],
        )
        ptr_doc = PTRDocument(clauses=[clause], tables=[])
        report_item = InspectionItem(
            sequence_number="11",
            standard_clause="2.1.2",
            inspection_project="尺寸",
            standard_requirement="尺寸具体要求见表1。\n表1 尺寸\n组件\n导管\n导丝",
        )

        result = comparator._compare_table_reference(1, clause, ptr_doc, [report_item])

        assert result.table_found is True
        assert result.reference_type == "table_summary_reference"
        assert result.parameters[0].parameter_name == "整表摘要"
        assert result.parameters[0].details["reference_type"] == "table_summary_reference"
        assert result.parameters[0].details["referenced_table_label"] == "表1"

    def test_extract_value_map_from_segment_should_keep_multi_step_expression_intact(self):
        comparator = TableComparator()
        segment = "基础频率(bpm) 常规数值：30...(5)...100...(10)...200 标准设置：60 允许误差：±20ms 单位：ms"

        value_map = comparator._extract_value_map_from_segment(segment)

        assert value_map["常规数值"] == "30...(5)...100...(10)...200"
        assert value_map["标准设置"] == "60"
        assert value_map["允许误差"] == "±20ms"
        assert value_map["单位"] == "ms"

    def test_extract_condition_result_rows_should_bind_condition_to_result(self):
        comparator = TableComparator()
        content = "@240Ω\n-10～+3\n@500Ω\n-10～+3\n@2000Ω\n-10～+3\n单位：ms"

        rows = comparator._extract_condition_result_rows(content)

        assert rows == [
            {"condition": "@240Ω", "result": "-10～+3"},
            {"condition": "@500Ω", "result": "-10～+3"},
            {"condition": "@2000Ω", "result": "-10～+3"},
        ]

    def test_resolve_report_value_from_condition_rows_should_not_return_condition_label(self):
        comparator = TableComparator()
        report_evidence_rows = [
            {
                "label": "基础频率(bpm)",
                "content": "允许误差：±20ms\n@240Ω\n@500Ω\n@2000Ω",
                "condition_rows": [
                    {"condition": "@240Ω", "result": "-10～+3"},
                    {"condition": "@500Ω", "result": "-10～+3"},
                    {"condition": "@2000Ω", "result": "-10～+3"},
                ],
            }
        ]

        report_value = comparator._resolve_report_value_from_evidence_rows(
            report_evidence_rows=report_evidence_rows,
            report_text="基础频率(bpm)\n@240Ω\n-10～+3\n@500Ω\n-10～+3\n@2000Ω\n-10～+3",
            parameter_name="基础频率(bpm)",
        )

        assert report_value == "-10～+3（@240Ω/@500Ω/@2000Ω）"

    def test_compare_table_parameters_should_mark_external_reference_without_failing(self):
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["参数", "值"],
            rows=[["电磁兼容性", "应符合要求"]],
        )
        report_item = InspectionItem(
            sequence_number="88",
            standard_clause="2.9.1",
            inspection_project="电磁兼容性",
            test_result="/",
            remark="电磁兼容性检验见另一份报告",
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.9.1"),
            full_text="2.9.1 电磁兼容性",
            text_content="电磁兼容性应符合要求。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
            report_items=[report_item],
        )

        assert len(comparisons) == 1
        assert comparisons[0].matches is True
        assert comparisons[0].comparison_status == "external_reference"

    def test_compare_table_parameters_should_merge_continuation_rows_by_same_sequence(self):
        """Continuation rows under same sequence should be included in report text for coverage."""
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[["脉冲宽度(ms)", "全部型号", "0.1...(0.1)...0.5...(0.25)...1.5", "0.4", "±20μs"]],
        )
        head_row = InspectionItem(
            sequence_number="39",
            standard_clause="2.1.3",
            standard_requirement="脉冲宽度应符合表1中的数值。",
            test_result="符合",
            inspection_project="脉冲宽度(ms)",
        )
        continuation_row = InspectionItem(
            sequence_number="",
            standard_clause="",
            standard_requirement="常规数值：0.1 ...(0.1) ... 0.5 ...(0.25) ... 1.5",
            test_result="标准设置：0.4；允许误差：±20μs",
            inspection_project="",
        )
        next_item = InspectionItem(
            sequence_number="40",
            standard_clause="2.1.4",
            standard_requirement="基础频率应符合表1中的数值。",
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=head_row,
            clause=clause,
            report_items=[head_row, continuation_row, next_item],
        )
        assert len(comparisons) == 1
        assert comparisons[0].matches is True

    def test_compare_table_parameters_should_prefer_report_topic_over_noisy_clause_text(self):
        """Noisy OCR text in PTR clause should not pull unrelated parameter rows."""
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["脉冲幅度(V)③", "全部型号", "0.2...(0.2)...6.0...(0.5)...7.5", "3.0", "±50mV"],
                ["Vs 后远场保护(ms)", "Edora 8 DR", "100...(10)...220", "100", "±20"],
            ],
        )
        report_item = InspectionItem(
            sequence_number="38",
            standard_clause="2.1.2",
            inspection_project="脉冲幅度(V)",
            standard_requirement="脉冲幅度应符合表1中的数值。",
            test_result="脉冲幅度(V) 常规数值 0.2...(0.2)...6.0...(0.5)...7.5 标准设置 3.0",
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.2"),
            full_text="2.1.2 脉冲幅度",
            # Simulate OCR pollution from nearby rows.
            text_content="脉冲幅度(V)：脉冲幅度应符合表1中的数值。Vs后远场保护(ms) Edora 8 DR",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
            report_items=[report_item],
        )
        assert len(comparisons) == 1
        assert comparisons[0].parameter_name.startswith("脉冲幅度")

    def test_compare_table_parameters_should_use_parameter_records_when_available(self):
        """Comparator should support structured ParameterRecord-style inputs.

        Phase-0 lock: legacy row scan cannot pass this case because table rows are empty.
        """
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[["", "", "", "", ""]],
        )
        # Simulate future canonical payload carried on PTRTable.
        setattr(
            ptr_table,
            "metadata",
            {
                "parameter_records": [
                    {
                        "parameter_name": "脉冲宽度(ms)",
                        "dimensions": {"型号": "全部型号"},
                        "values": {
                            "常规数值": "0.1...(0.1)...1.5",
                            "标准设置": "0.4",
                            "允许误差": "±20μs",
                        },
                    }
                ]
            },
        )
        setattr(
            ptr_table,
            "column_paths",
            [["参数"], ["型号"], ["常规数值"], ["标准设置"], ["允许误差"]],
        )

        report_item = InspectionItem(
            sequence_number="39",
            standard_clause="2.1.3",
            test_result=(
                "脉冲宽度(ms) 常规数值 0.1...(0.1)...1.5；"
                "标准设置 0.4；允许误差 ±20μs"
            ),
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
            report_items=[report_item],
        )
        assert len(comparisons) == 1
        assert comparisons[0].matches is True
        assert ptr_table.metadata is not None
        assert ptr_table.metadata.get("comparison_path_used") == "canonical"

    def test_compare_table_parameters_should_see_page2_records_after_no_number_continuation_merge(self):
        """Merged no-number continuation should still surface continuation-page parameters canonically."""
        extractor = PTRExtractor()
        comparator = TableComparator()

        p1 = PTRTable(
            table_number=None,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            column_paths=[["参数"], ["型号"], ["常规数值"], ["标准设置"], ["允许误差"]],
            rows=[
                ["参数", "型号", "常规数值", "标准设置", "允许误差"],
                ["脉冲宽度(ms)", "全部型号", "0.1...(0.1)...1.5", "0.4", "±20μs"],
            ],
            page=20,
            position=(0, 520),
        )
        p2 = PTRTable(
            table_number=None,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            column_paths=[["参数"], ["型号"], ["常规数值"], ["标准设置"], ["允许误差"]],
            rows=[
                ["参数", "型号", "常规数值", "标准设置", "允许误差"],
                ["基础频率(bpm)", "全部型号", "30...(5)...200", "60", "±20ms"],
            ],
            page=21,
            position=(0, 40),
        )

        merged = extractor._merge_continuation_tables([p1, p2])
        assert len(merged) == 1
        ptr_table = merged[0]

        report_item = InspectionItem(
            sequence_number="39",
            standard_clause="2.1.3",
            inspection_project="基础频率",
            standard_requirement="基础频率应符合表1中的数值。",
            test_result="基础频率(bpm) 常规数值 30...(5)...200 标准设置 60 允许误差 ±20ms",
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 基础频率",
            text_content="基础频率(bpm)：基础频率应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
            report_items=[report_item],
        )

        assert len(comparisons) == 1
        assert comparisons[0].parameter_name == "基础频率(bpm)"
        assert comparisons[0].matches is True
        assert ptr_table.metadata is not None
        assert ptr_table.metadata.get("comparison_path_used") == "canonical"

    def test_compare_table_parameters_should_fallback_to_legacy_when_canonical_invalid(self, monkeypatch):
        """Canonical failure should transparently fall back to legacy path."""
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["参数", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["脉冲宽度(ms)", "0.1...(0.1)...1.5", "0.4", "±20μs"],
            ],
        )
        setattr(
            ptr_table,
            "column_paths",
            [["参数"], ["常规数值"], ["标准设置"], ["允许误差"]],
        )
        monkeypatch.setattr(
            comparator,
            "_compare_table_parameters_canonical",
            lambda *args, **kwargs: ([], "missing_parameter_records"),
        )
        setattr(
            ptr_table,
            "metadata",
            {
                "canonical_available": True,
                "canonical_low_confidence": True,
            },
        )

        report_item = InspectionItem(
            sequence_number="39",
            standard_clause="2.1.3",
            test_result="脉冲宽度(ms) 标准设置 0.4",
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
            report_items=[report_item],
        )
        assert len(comparisons) == 1
        assert comparisons[0].matches is True
        assert ptr_table.metadata is not None
        assert ptr_table.metadata.get("comparison_path_used") == "legacy"
        assert "canonical_path_unavailable" not in ptr_table.metadata.get("comparison_path_reason", "")

    def test_compare_table_parameters_should_route_by_column_paths_roles(self):
        """Comparator should not depend on fragile column index when column_paths exist."""
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=["列1", "列2", "列3", "列4"],
            rows=[
                ["全部型号", "0.4", "脉冲宽度(ms)", "±20μs"],
            ],
        )
        setattr(
            ptr_table,
            "column_paths",
            [["型号"], ["标准设置"], ["参数"], ["允许误差"]],
        )

        report_item = InspectionItem(
            sequence_number="39",
            standard_clause="2.1.3",
            test_result="脉冲宽度(ms) 标准设置 0.4 允许误差 ±20μs",
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
            report_items=[report_item],
        )
        assert len(comparisons) == 1
        assert comparisons[0].parameter_name == "脉冲宽度(ms)"
        assert comparisons[0].matches is True

    def test_compare_table_parameters_dimension_records_keep_siblings_separate(self):
        """Sibling dimensions in multi-dimension tables should generate separate records."""
        comparator = TableComparator()
        ptr_table = PTRTable(
            table_number=1,
            headers=[
                "参数",
                "型号",
                "心房",
                "常规数值",
                "心室",
                "常规数值",
            ],
            rows=[
                ["脉冲宽度(ms)", "全部型号", "20...1.5", "3.0", "10...6.5", "2.5"],
            ],
            column_paths=[
                ["参数"],
                ["型号"],
                ["心房", "常规数值"],
                ["心房", "标准设置"],
                ["心室", "常规数值"],
                ["心室", "标准设置"],
            ],
        )

        report_item = InspectionItem(
            sequence_number="39",
            standard_clause="2.1.3",
            test_result=(
                "脉冲宽度(ms) 心房 常规数值 20...1.5 标准设置 3.0"
                "心室 常规数值 10...6.5"
            ),
        )
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度",
            text_content="脉冲宽度(ms)：脉冲宽度应符合表1中的数值。",
            level=3,
        )

        comparisons = comparator._compare_table_parameters(
            ptr_table=ptr_table,
            report_item=report_item,
            clause=clause,
            report_items=[report_item],
        )
        assert len(comparisons) == 2
        heart_records = {
            item.ptr_value for item in comparisons
            if item.parameter_name == "脉冲宽度(ms)"
        }
        assert "3.0" in heart_records or "20...1.5" in heart_records

    def test_compare_table_parameters_should_favor_default_first_for_pick_value(self):
        """Canonical pick should prefer default/标准设置 over 单个常规数值 when both exist."""
        comparator = TableComparator()
        record = {
            "parameter_name": "脉冲宽度(ms)",
            "values": {
                "常规数值": "0.1...(0.1)...1.5",
                "标准设置": "0.4",
                "允许误差": "±20μs",
            },
        }
        ptr_value = comparator._pick_ptr_value_from_parameter_record(record)
        assert ptr_value == "0.4"
