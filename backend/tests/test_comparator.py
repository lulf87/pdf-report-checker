"""
Tests for Comparator module.

Tests strict matching, diff algorithms, and similarity computation.
"""

import pytest

from app.models.ptr_models import PTRClause, PTRClauseNumber, PTRDocument, PTRTableReference
from app.models.report_models import InspectionItem, InspectionTable, ReportDocument
from app.models.report_models import ThirdPageFields
from app.services.comparator import (
    ClauseComparator,
    ComparisonResult,
    ComparisonDetail,
    DiffFragment,
    compare_ptr_and_report,
    compare_texts,
)


class TestDiffFragment:
    """Test DiffFragment model."""

    def test_creation(self):
        """Test creating diff fragments."""
        fragment = DiffFragment(
            text="test",
            type="same",
            position=0,
        )
        assert fragment.text == "test"
        assert fragment.type == "same"
        assert fragment.position == 0


class TestComparisonDetail:
    """Test ComparisonDetail model."""

    def test_creation(self):
        """Test creating comparison detail."""
        detail = ComparisonDetail(
            result=ComparisonResult.MATCH,
            similarity=1.0,
        )
        assert detail.result == ComparisonResult.MATCH
        assert detail.similarity == 1.0
        assert detail.is_match is True

    def test_has_differences(self):
        """Test has_differences property."""
        detail1 = ComparisonDetail(differences=[])
        assert detail1.has_differences is False

        detail2 = ComparisonDetail(
            differences=[
                DiffFragment(text="test", type="removed"),
            ]
        )
        assert detail2.has_differences is True


class TestClauseComparator:
    """Test ClauseComparator class."""

    def test_comparator_initialization(self):
        """Test comparator can be initialized."""
        comparator = ClauseComparator()
        assert comparator.normalizer is not None
        assert comparator.strict_mode is True

    def test_compare_identical_texts(self):
        """Test comparing identical texts."""
        comparator = ClauseComparator()
        is_match, similarity, diffs = compare_texts("Test text", "Test text")
        assert is_match is True
        assert similarity == 1.0
        assert len(diffs) == 0

    def test_compare_different_texts(self):
        """Test comparing different texts."""
        comparator = ClauseComparator()
        is_match, similarity, diffs = compare_texts("Test text", "Other text")
        assert is_match is False
        assert similarity < 1.0
        assert len(diffs) > 0

    def test_compare_after_normalization(self):
        """Test that comparison uses normalization."""
        is_match, _, _ = compare_texts("Ｔｅｓｔ", "Test")
        assert is_match is True  # Full-width should match half-width

    def test_compare_with_whitespace_difference(self):
        """Test comparing texts with only whitespace differences."""
        is_match, _, _ = compare_texts("Test text", "Test  text")
        assert is_match is True  # Extra whitespace should be normalized

    def test_compare_with_newline_difference(self):
        """Texts should still match when only line breaks differ."""
        is_match, _, _ = compare_texts("导管外观\n应无杂质。", "导管外观 应无杂质。")
        assert is_match is True

    def test_compute_similarity(self):
        """Test similarity computation."""
        comparator = ClauseComparator()

        # Identical texts
        sim1 = comparator._compute_similarity("Test", "Test")
        assert sim1 == 1.0

        # Completely different
        sim2 = comparator._compute_similarity("Test", "Other")
        assert sim2 < 1.0

        # Empty strings
        sim3 = comparator._compute_similarity("", "")
        assert sim3 == 1.0

    def test_compute_diff(self):
        """Test diff computation."""
        comparator = ClauseComparator()

        # Simple insertion
        diffs = comparator._compute_diff("Test", "Test!")
        assert len(diffs) > 0
        # Should have 'same' fragments and 'added' fragment

        # Simple deletion
        diffs = comparator._compute_diff("Test!", "Test")
        assert any(d.type == "removed" for d in diffs)

        # Replacement
        diffs = comparator._compute_diff("Test", "Best")
        assert len(diffs) > 0

    def test_compare_empty_documents(self):
        """Test comparing empty documents."""
        ptr_doc = PTRDocument()
        report_doc = ReportDocument()

        comparator = ClauseComparator()
        results = comparator.compare_documents(ptr_doc, report_doc)

        assert isinstance(results, list)
        assert len(results) == 0


class TestCompareDocuments:
    """Test document-level comparison."""

    def test_chapter_2_heading_should_be_skipped(self):
        """Chapter heading '2' should not become a standalone comparison item."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.extend(
            [
                PTRClause(
                    number=PTRClauseNumber.from_string("2"),
                    full_text="2 性能指标",
                    text_content="性能指标",
                    level=1,
                ),
                PTRClause(
                    number=PTRClauseNumber.from_string("2.1"),
                    full_text="2.1 外观",
                    text_content="外观",
                    level=2,
                ),
            ]
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="157",
                standard_clause="2.1",
                standard_requirement="外观",
            )
        )
        report_doc.inspection_table = table

        results = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)
        assert len(results) == 1
        assert str(results[0].ptr_clause.number) == "2.1"

    def test_test_method_and_appendix_like_clauses_should_not_enter_main_pool(self):
        """Only main requirements should be compared against the report body."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.extend(
            [
                PTRClause(
                    number=PTRClauseNumber.from_string("2.1.1"),
                    full_text="2.1.1 断裂力应不小于10N",
                    text_content="断裂力应不小于10N",
                    level=3,
                    clause_type="main_requirement",
                ),
                PTRClause(
                    number=PTRClauseNumber.from_string("2.2.1"),
                    full_text="2.2.1 将测试系统按图1进行安装",
                    text_content="将测试系统按图1进行安装",
                    level=3,
                    clause_type="test_method",
                ),
                PTRClause(
                    number=PTRClauseNumber.from_string("2.2.2"),
                    full_text="2.2.2 注：箭头方向代表数据传输方向",
                    text_content="注：箭头方向代表数据传输方向",
                    level=3,
                    clause_type="informational",
                ),
            ]
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="12",
                standard_clause="2.1.1",
                standard_requirement="断裂力应不小于10N",
            )
        )
        report_doc.inspection_table = table

        results = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)

        assert [str(detail.ptr_clause.number) for detail in results] == ["2.1.1"]

    def test_compare_single_clause_match(self):
        """Test comparing a single matching clause."""
        # Create PTR document
        ptr_doc = PTRDocument()
        ptr_clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test Clause",
            text_content="Test Clause",
            level=2,
        )
        ptr_doc.clauses.append(ptr_clause)

        # Create report document
        report_doc = ReportDocument()
        table = InspectionTable()
        item = InspectionItem(
            sequence_number="2.1",
            standard_requirement="Test Clause",
        )
        table.items.append(item)
        report_doc.inspection_table = table

        # Compare
        comparator = ClauseComparator()
        results = comparator.compare_documents(ptr_doc, report_doc)

        assert len(results) == 1
        assert results[0].is_match is True

    def test_numeric_semantic_clause_comparison_should_match_report_result(self):
        """Numeric requirement clauses should compare against report result semantically."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.3.2"),
                full_text="2.3.2 还原物质不应超过2.0mL。",
                text_content="还原物质不应超过2.0mL。",
                level=3,
                clause_type="main_requirement",
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="160",
                inspection_project="化学性能",
                standard_clause="",
                standard_requirement="2.3.2 还原物质不应超过2.0mL。",
                test_result="0.4mL",
                item_conclusion="符合",
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH
        assert result.match_reason in {"numeric_semantic_match", "exact_normalized_match"}
        assert result.details["numeric_evidence"] == "0.4mL"

    def test_numeric_semantic_clause_comparison_should_tolerate_resistance_symbol_ocr_drift(self):
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.5.1"),
                full_text="2.5.1 直流电阻",
                text_content="直流电阻 各电极与连接器对应芯脚之间的导线的直流电阻值202。",
                level=3,
                clause_type="main_requirement",
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="57",
                inspection_project="直流电阻",
                standard_clause="2.5.1",
                standard_requirement="各电极与连接器对应芯脚之间的导线的直流电阻值≤20Ω。",
                test_result="≤20Ω",
                item_conclusion="符合",
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH
        assert result.match_reason in {"numeric_semantic_match", "exact_normalized_match"}

    def test_noisy_parent_group_clause_should_be_excluded_instead_of_differ(self):
        """Noisy parent clauses with compared descendants should not report text mismatch."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.extend(
            [
                PTRClause(
                    number=PTRClauseNumber.from_string("2.1"),
                    full_text="2.1 将测试系统按图1进行安装 图B1测试布图 注：箭头方向代表数据传输方向",
                    text_content="将测试系统按图1进行安装 图B1测试布图 注：箭头方向代表数据传输方向",
                    level=2,
                    clause_type="main_requirement",
                ),
                PTRClause(
                    number=PTRClauseNumber.from_string("2.1.1"),
                    full_text="2.1.1 外表面",
                    text_content="外表面",
                    level=3,
                    clause_type="main_requirement",
                ),
            ]
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="157",
                standard_clause="2.1",
                inspection_project="物理性能及结构",
                standard_requirement="2.1.1 外表面",
            )
        )
        report_doc.inspection_table = table

        results = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)
        result_map = {str(r.ptr_clause.number): r for r in results}
        assert result_map["2.1"].result == ComparisonResult.EXCLUDED
        assert result_map["2.1"].match_reason == "group_clause_with_children"
        assert result_map["2.1.1"].result == ComparisonResult.MATCH

    def test_parent_table_summary_clause_should_be_group_clause_without_sample_specific_rules(self):
        """Generic parent clauses that only introduce a parameter table should become group clauses."""
        ptr_doc = PTRDocument()
        parent = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 基本电性能指标及允许误差 见表1参数表",
            text_content="基本电性能指标及允许误差 见表1参数表",
            level=2,
            clause_type="main_requirement",
        )
        parent.table_references.append(PTRTableReference(table_number=1))
        child = PTRClause(
            number=PTRClauseNumber.from_string("2.1.1"),
            full_text="2.1.1 脉冲幅度",
            text_content="脉冲幅度应符合表1中的数值。",
            level=3,
            clause_type="main_requirement",
        )
        ptr_doc.clauses.extend([parent, child])

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="1",
                standard_clause="2.1.1",
                standard_requirement="脉冲幅度应符合表1中的数值。",
            )
        )
        report_doc.inspection_table = table

        results = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)
        result_map = {str(r.ptr_clause.number): r for r in results}
        assert result_map["2.1"].comparison_status == "group_clause"
        assert result_map["2.1"].result == ComparisonResult.EXCLUDED

    def test_measurement_bundle_clause_should_match_multiple_rows(self):
        """Multi-field size bundle should pass when each measurement row satisfies expectation."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.2.1"),
                full_text="2.1.2.1 导管尺寸要求",
                text_content="当用通用量具测量时，导管管身直径（外径）、电极宽度、电极间距、环形圈直径、有效长度应符合产品型号/规格及其划分说明表中尺寸要求。",
                level=4,
                clause_type="main_requirement",
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.extend(
            [
                InspectionItem(
                    sequence_number="157",
                    standard_requirement="2.1.2.1 当用通用量具测量时，导管尺寸应符合要求。",
                ),
                InspectionItem(standard_requirement="管身直径（外径）", test_result="2.5mm±0.1mm", item_conclusion="+0.03"),
                InspectionItem(standard_requirement="电极宽度", test_result="2.5mm±0.1mm", item_conclusion="-0.02～+0.06"),
                InspectionItem(standard_requirement="电极间距", test_result="4mm±0.5mm", item_conclusion="-0.4～-0.2"),
                InspectionItem(standard_requirement="环形圈最小直径", test_result="20mm±10%", item_conclusion="-5%～+3%"),
                InspectionItem(standard_requirement="环形圈最大直径", test_result="25mm±10%", item_conclusion="-6%～+2%"),
                InspectionItem(standard_requirement="有效长度", test_result="115cm±3cm", item_conclusion="+0～+1"),
                InspectionItem(standard_requirement="2.1.2.2 导管头端部分可调弯，调弯角度180±20°。"),
            ]
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH
        assert result.match_reason == "measurement_bundle_match"
        assert result.details["display_type"] == "measurement_bundle"
        assert result.details["display_title"] == "尺寸要求"
        assert len(result.details["structured_rows"]) == 6

    def test_segmented_threshold_bundle_should_match(self):
        """Segment threshold tables should pass when every measured interval satisfies the minimum."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.3"),
                full_text="2.1.3 断裂力",
                text_content="断裂力 各试验段的断裂力应符合下表的规定。",
                level=3,
                clause_type="main_requirement",
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.extend(
            [
                InspectionItem(sequence_number="续157", standard_clause="2.1", standard_requirement="2.1.3 断裂力 各试验段的断裂力应符合下表的规定。"),
                InspectionItem(standard_requirement="试验段", test_result="断裂力（N）"),
                InspectionItem(standard_requirement="环形圈头端与环形圈管身", test_result="≥10", item_conclusion="17～46"),
                InspectionItem(standard_requirement="环形圈管身与可调弯管身", test_result="≥15", item_conclusion="50～55"),
                InspectionItem(standard_requirement="可调弯管与外管管身", test_result="≥15", item_conclusion="37～57"),
                InspectionItem(standard_requirement="外管管身", test_result="≥15", item_conclusion="186～213"),
                InspectionItem(standard_requirement="外管管身与手柄", test_result="≥15", item_conclusion="173～228"),
                InspectionItem(standard_requirement="2.1.4 调节机构的操控性"),
            ]
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH
        assert result.match_reason == "segmented_threshold_bundle_match"
        assert result.details["display_type"] == "segmented_threshold_bundle"
        assert result.details["display_title"] == "断裂力"
        assert len(result.details["structured_rows"]) == 5

    def test_measurement_bundle_should_combine_base_value_and_tolerance_split_across_columns(self):
        """Rows like '连接线长度±0.05m' + '2m' + '+0.02' should still pass as one bundle."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.7.2"),
                full_text="2.7.2 连接线尺寸",
                text_content="尺寸 当用通用量具测量时，导管连接线外径、长度应符合导管连接线型号/规格表中尺寸要求。",
                level=3,
                clause_type="main_requirement",
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.extend(
            [
                InspectionItem(standard_requirement="2.7.2 尺寸 当用通用量具测量时，导管连接线外径、长度应符合导管连接线型号/规格表中尺寸要求。"),
                InspectionItem(standard_requirement="连接线长度±0.05m", test_result="2m 单位：m", item_conclusion="+0.02"),
                InspectionItem(standard_requirement="外径±0.5mm", test_result="6.5mm 单位：mm", item_conclusion="-0.2～+0.0"),
                InspectionItem(standard_requirement="2.7.3 连接牢固度"),
            ]
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH
        assert result.match_reason == "measurement_bundle_match"
        assert result.details["display_type"] == "measurement_bundle"
        assert [row["item"] for row in result.details["structured_rows"]] == ["连接线长度", "外径"]

    def test_out_of_scope_keyword_exclusion_should_not_be_reported_as_differ(self):
        """Named exclusions on third page should become out_of_scope_in_current_report."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.5.3"),
                full_text="2.5.3 电磁兼容应符合YY 9706.102-2021要求。",
                text_content="电磁兼容应符合YY 9706.102-2021要求。",
                level=3,
                clause_type="main_requirement",
            )
        )

        report_doc = ReportDocument()
        report_doc.third_page_fields = ThirdPageFields(
            inspection_items=["2.1～2.8（除生物相容性、电磁兼容性）"]
        )
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="161",
                inspection_project="安全要求",
                standard_requirement="2.5.3 电磁兼容应符合YY 9706.102-2021要求。",
                test_result="/",
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.EXCLUDED
        assert result.comparison_status == "out_of_scope_in_current_report"
        assert result.match_reason == "out_of_scope_third_page"
        assert result.details["display_type"] == "out_of_scope_notice"
        assert "范围外" in result.details["structured_notice"]

    def test_scope_rule_with_external_reference_should_not_be_treated_as_failure(self):
        """Coverage lines that route a clause to another report should yield external_reference."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.10"),
                full_text="2.10 电磁兼容",
                text_content="电磁兼容应符合标准要求。",
                level=2,
                clause_type="main_requirement",
            )
        )
        report_doc = ReportDocument(
            third_page_fields=ThirdPageFields(
                inspection_items=["2.10 见另一份报告 QW2025-1234"]
            )
        )
        report_doc.inspection_table = InspectionTable()

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH
        assert result.comparison_status == "external_reference"

    def test_scope_rule_with_pending_evidence_should_not_be_treated_as_failure(self):
        """Coverage lines with pending evidence wording should map to pending_evidence."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.11"),
                full_text="2.11 生物相容性",
                text_content="生物相容性应符合标准要求。",
                level=2,
                clause_type="main_requirement",
            )
        )
        report_doc = ReportDocument(
            third_page_fields=ThirdPageFields(
                inspection_items=["2.11 待补证，补充提供资料"]
            )
        )
        report_doc.inspection_table = InspectionTable()

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH
        assert result.comparison_status == "pending_evidence"

    def test_embedded_clause_reference_should_not_beat_row_start_clause_match(self):
        """Clause matching should prefer rows whose requirement starts with the target clause."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.6.1"),
                full_text="2.6.1 直流电阻应不大于10Ω。",
                text_content="直流电阻应不大于10Ω。",
                level=3,
                clause_type="main_requirement",
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.extend(
            [
                InspectionItem(
                    sequence_number="157",
                    inspection_project="机械性能",
                    standard_requirement="2.1.5 弯曲疲劳应符合2.6.1直流电阻的要求。",
                    test_result="符合要求",
                ),
                InspectionItem(
                    sequence_number="162",
                    inspection_project="电学性能",
                    standard_clause="2.6",
                    standard_requirement="2.6.1 直流电阻应不大于10Ω。\n单位：Ω",
                    item_conclusion="6",
                    remark="符合",
                ),
            ]
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]

        assert result.result == ComparisonResult.MATCH
        assert result.match_reason == "numeric_semantic_match"
        assert result.report_item == table.items[1]
        assert result.details["numeric_evidence"] == "6"

    def test_compare_single_clause_match_when_ptr_has_spaces_and_newlines(self):
        """PTR text spacing/newline noise should be ignored like report side."""
        ptr_doc = PTRDocument()
        ptr_clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test Clause",
            text_content="相间间隔\n相间间隔>=1 μ s 且<=100 μ s，误差不超过±10%。",
            level=2,
        )
        ptr_doc.clauses.append(ptr_clause)

        report_doc = ReportDocument()
        table = InspectionTable()
        item = InspectionItem(
            sequence_number="2.1",
            standard_requirement="相间间隔 相间间隔>=1μs且<=100μs，误差不超过±10%。",
        )
        table.items.append(item)
        report_doc.inspection_table = table

        comparator = ClauseComparator()
        results = comparator.compare_documents(ptr_doc, report_doc)

        assert len(results) == 1
        assert results[0].is_match is True
        assert results[0].result == ComparisonResult.MATCH

    def test_compare_single_clause_differ(self):
        """Test comparing a single differing clause."""
        # Create PTR document
        ptr_doc = PTRDocument()
        ptr_clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test Clause",
            text_content="Test Clause",
            level=2,
        )
        ptr_doc.clauses.append(ptr_clause)

        # Create report document with different text
        report_doc = ReportDocument()
        table = InspectionTable()
        item = InspectionItem(
            sequence_number="2.1",
            standard_requirement="Different Clause",
        )
        table.items.append(item)
        report_doc.inspection_table = table

        # Compare
        comparator = ClauseComparator()
        results = comparator.compare_documents(ptr_doc, report_doc)

        assert len(results) == 1
        assert results[0].is_match is False
        assert results[0].result == ComparisonResult.DIFFER

    def test_compare_missing_clause(self):
        """Test when clause is missing from report."""
        # Create PTR document
        ptr_doc = PTRDocument()
        ptr_clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test Clause",
            text_content="Test Clause",
            level=2,
        )
        ptr_doc.clauses.append(ptr_clause)

        # Create report document with no items at all
        report_doc = ReportDocument()
        table = InspectionTable()
        # No items added
        report_doc.inspection_table = table

        # Compare
        comparator = ClauseComparator()
        results = comparator.compare_documents(ptr_doc, report_doc)

        assert len(results) == 1
        assert results[0].result == ComparisonResult.MISSING

    def test_third_page_inspection_scope_should_exclude_out_of_scope_clauses(self):
        """Third-page inspection items define clause scope for PTR comparison."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.extend(
            [
                PTRClause(
                    number=PTRClauseNumber.from_string("2.1.2"),
                    full_text="2.1.2 参数A",
                    text_content="参数A应符合表1中的数值。",
                    level=3,
                ),
                PTRClause(
                    number=PTRClauseNumber.from_string("2.1.3"),
                    full_text="2.1.3 参数B",
                    text_content="参数B应符合表1中的数值。",
                    level=3,
                ),
                PTRClause(
                    number=PTRClauseNumber.from_string("2.2.1"),
                    full_text="2.2.1 参数C",
                    text_content="参数C应满足要求。",
                    level=3,
                ),
            ]
        )

        report_doc = ReportDocument(
            third_page_fields=ThirdPageFields(
                inspection_items=["2.1.2～2.1.3"],
            )
        )
        table = InspectionTable()
        table.items.extend(
            [
                InspectionItem(
                    sequence_number="1",
                    standard_clause="2.1.2",
                    standard_requirement="参数A应符合表1中的数值。",
                ),
                InspectionItem(
                    sequence_number="2",
                    standard_clause="2.1.3",
                    standard_requirement="参数B应符合表1中的数值。",
                ),
            ]
        )
        report_doc.inspection_table = table

        results = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)
        result_map = {str(r.ptr_clause.number): r for r in results}
        assert result_map["2.1.2"].result == ComparisonResult.MATCH
        assert result_map["2.1.3"].result == ComparisonResult.MATCH
        assert result_map["2.2.1"].result == ComparisonResult.EXCLUDED
        assert result_map["2.2.1"].comparison_status == "out_of_scope_in_current_report"

    def test_scope_should_include_clause_present_in_report_table_even_if_third_page_misses_it(self):
        """If report正文 contains clause, do not exclude it solely by third-page OCR range."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.2"),
                full_text="2.1.2 脉冲幅度",
                text_content="脉冲幅度应符合表1中的数值。",
                level=3,
            )
        )

        report_doc = ReportDocument(
            third_page_fields=ThirdPageFields(
                # Simulate OCR miss on third page (starts from 2.1.3)
                inspection_items=["2.1.3～2.1.15"],
            )
        )
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="38",
                standard_clause="2.1.2",
                standard_requirement="脉冲幅度应符合表1中的数值。",
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result != ComparisonResult.EXCLUDED

    def test_parameter_table_clause_equivalence_should_match(self):
        """Base '符合表1中的数值' requirement should match report rows with detail matrix."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.3"),
                full_text="2.1.3 脉冲宽度",
                text_content="脉冲宽度(ms):脉冲宽度应符合表1中的数值。",
                level=3,
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="39",
                standard_clause="2.1.3",
                standard_requirement=(
                    "脉冲宽度应符合表1中的数值。"
                    "脉冲宽度(ms)常规数值:0.1...0.5...1.5 标准设置:0.4 允许误差:±20μs"
                ),
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH

    def test_parameter_table_clause_equivalence_should_tolerate_table_spacing(self):
        """Should treat '表 1 中的数值' equivalent to '表1中的数值'."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.3"),
                full_text="2.1.3 脉冲宽度",
                text_content="脉冲宽度(ms)：脉冲宽度应符合表 1 中的数值。",
                level=3,
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="39",
                standard_clause="2.1.3",
                standard_requirement=(
                    "脉冲宽度应符合表1中的数值。"
                    "脉冲宽度(ms)常规数值:0.1...0.5...1.5 标准设置:0.4 允许误差:±20μs"
                ),
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH

    def test_parameter_table_clause_equivalence_should_not_match_wrong_topic(self):
        """Do not over-match unrelated topics even when both mention 表1数值."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.3"),
                full_text="2.1.3 脉冲宽度",
                text_content="脉冲宽度(ms):脉冲宽度应符合表1中的数值。",
                level=3,
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="39",
                standard_clause="2.1.3",
                standard_requirement=(
                    "基础频率应符合表1中的数值。"
                    "基础频率(bpm)常规数值:30...100...200 标准设置:60"
                ),
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.DIFFER

    def test_parameter_table_clause_equivalence_should_use_rhs_topic_after_colon(self):
        """When PTR uses 'A:B应符合表1...', matcher should compare topic B."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.7"),
                full_text="2.1.7 灵敏度",
                text_content="灵敏度(mV):心房感知灵敏度和心室感知灵敏度应符合表1中的数值。",
                level=3,
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="42",
                standard_clause="2.1.7",
                standard_requirement=(
                    "心房感知灵敏度和心室感知灵敏度应符合表1中的数值。"
                    "心房感知灵敏度(mV)常规数值:AUTO..."
                ),
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH

    def test_should_not_fallback_to_wrong_clause_when_clause_column_exists(self):
        """If report has parseable clause column, missing target should not hijack nearby clause."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.6"),
                full_text="2.1.6 干扰转复频率",
                text_content="干扰转复频率应符合表1中的数值。",
                level=3,
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.extend(
            [
                InspectionItem(
                    sequence_number="40",
                    standard_clause="2.1.4",
                    standard_requirement="基础频率应符合表1中的数值。",
                ),
                InspectionItem(
                    sequence_number="42",
                    standard_clause="2.1.7",
                    standard_requirement="灵敏度应符合表1中的数值。",
                ),
            ]
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MISSING
        assert result.report_item is None

    def test_sequence_index_should_not_hijack_clause_prefix_match(self):
        """Clause 2.1.1.1 should not match report row sequence '2' by prefix."""
        ptr_doc = PTRDocument()
        ptr_clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.1.1"),
            full_text="2.1.1.1 导管外观",
            text_content="导管外观",
            level=4,
        )
        ptr_doc.clauses.append(ptr_clause)

        report_doc = ReportDocument()
        table = InspectionTable()
        # Row-index style sequence "2": should NOT be used for clause-prefix matching.
        table.items.append(
            InspectionItem(
                sequence_number="2",
                standard_clause="4.2",
                standard_requirement="风险管理过程",
            )
        )
        # Actual textual match candidate.
        table.items.append(
            InspectionItem(
                sequence_number="157",
                standard_clause="2.1",
                standard_requirement="导管外观",
            )
        )
        report_doc.inspection_table = table

        results = ClauseComparator().compare_documents(ptr_doc, report_doc)
        assert len(results) == 1
        assert results[0].report_item is not None
        assert results[0].report_item.sequence_number == "157"

    def test_extract_clause_specific_report_text_for_display(self):
        """Display text should focus on target clause segment."""
        ptr_doc = PTRDocument()
        ptr_clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.1.1"),
            full_text="2.1.1.1 导管外观",
            text_content="导管外观 有效长度外表面应清洁",
            level=4,
        )
        ptr_doc.clauses.append(ptr_clause)

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="157",
                standard_clause="2.1",
                standard_requirement=(
                    "2.1.1. 外观\n"
                    "2.1.1.1. 导管外观 有效长度外表面应清洁\n"
                    "2.1.1.2. 导丝外观 表面应平整"
                ),
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator().compare_documents(ptr_doc, report_doc)[0]
        assert "导管外观 有效长度外表面应清洁" in result.report_text_for_display
        assert "2.1.1.2" not in result.report_text_for_display

    def test_shifted_requirement_text_in_sequence_column_should_be_usable(self):
        """When requirement text shifts into sequence column, matcher should still find it."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.1.2"),
                full_text="2.1.1.2 导丝外观",
                text_content="导丝外观 表面平整无缺陷",
                level=4,
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="157",
                standard_clause="2.1",
                inspection_project="物理性能",
                standard_requirement="2.1.1.1 导管外观 表面平整无缺陷",
            )
        )
        table.items.append(
            InspectionItem(
                # Shifted row: requirement text landed in sequence_number column.
                sequence_number="2.1.1.2 导丝外观 表面平整无缺陷",
                standard_clause="",
                inspection_project="符合要求",
                standard_requirement="",
            )
        )
        report_doc.inspection_table = table

        result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert result.result == ComparisonResult.MATCH

    def test_strict_mode_should_not_accept_soft_similarity(self):
        """Strict mode must reject high-similarity but non-identical text."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.append(
            PTRClause(
                number=PTRClauseNumber.from_string("2.1"),
                full_text="2.1 导管外观",
                text_content="导管外观 表面应清洁无杂质",
                level=2,
            )
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="2.1",
                standard_requirement="导管外观 表面应清洁无异物",
            )
        )
        report_doc.inspection_table = table

        strict_result = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)[0]
        assert strict_result.result == ComparisonResult.DIFFER

    def test_lenient_mode_can_promote_parent_clause_match(self):
        """Parent promotion is only allowed in lenient mode."""
        ptr_doc = PTRDocument()
        ptr_doc.clauses.extend(
            [
                PTRClause(
                    number=PTRClauseNumber.from_string("2.1"),
                    full_text="2.1 外观",
                    text_content="外观",
                    level=2,
                ),
                PTRClause(
                    number=PTRClauseNumber.from_string("2.1.1"),
                    full_text="2.1.1 导管外观",
                    text_content="导管外观",
                    level=3,
                ),
            ]
        )

        report_doc = ReportDocument()
        table = InspectionTable()
        table.items.append(
            InspectionItem(
                sequence_number="157",
                standard_clause="2.1",
                standard_requirement="2.1.1 导管外观",
            )
        )
        report_doc.inspection_table = table

        strict_results = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)
        strict_map = {str(r.ptr_clause.number): r for r in strict_results}
        assert strict_map["2.1"].result == ComparisonResult.DIFFER
        assert strict_map["2.1.1"].result == ComparisonResult.MATCH

        lenient_results = ClauseComparator(strict_mode=False).compare_documents(ptr_doc, report_doc)
        lenient_map = {str(r.ptr_clause.number): r for r in lenient_results}
        assert lenient_map["2.1"].result == ComparisonResult.MATCH


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_compare_ptr_and_report(self):
        """Test compare_ptr_and_report function."""
        ptr_doc = PTRDocument()
        report_doc = ReportDocument()

        results = compare_ptr_and_report(ptr_doc, report_doc)
        assert isinstance(results, list)

    def test_compare_texts_function(self):
        """Test compare_texts convenience function."""
        is_match, similarity, diffs = compare_texts("Test", "Test")

        assert is_match is True
        assert similarity == 1.0
        assert isinstance(diffs, list)


class TestEdgeCases:
    """Test edge cases."""

    def test_compare_empty_texts(self):
        """Test comparing empty texts."""
        is_match, similarity, diffs = compare_texts("", "")
        assert is_match is True
        assert similarity == 1.0

    def test_compare_one_empty_text(self):
        """Test comparing when one text is empty."""
        is_match, similarity, diffs = compare_texts("Test", "")
        assert is_match is False
        assert similarity == 0.0

    def test_compare_unicode_texts(self):
        """Test comparing texts with Unicode characters."""
        is_match, _, _ = compare_texts("测试文本", "测试文本")
        assert is_match is True

    def test_compare_mixed_scripts(self):
        """Test comparing texts with mixed scripts."""
        is_match, _, _ = compare_texts("Test测试", "Test测试")
        assert is_match is True

    def test_compare_with_line_breaks(self):
        """Test comparing texts with different line breaks."""
        is_match, _, _ = compare_texts("Line1\nLine2", "Line1 Line2")
        # Natural line breaks should be merged
        assert is_match is True or is_match is False

    def test_similarity_score_range(self):
        """Test that similarity scores are in valid range."""
        comparator = ClauseComparator()

        # Test various combinations
        test_cases = [
            ("Same", "Same"),
            ("Different", "Text"),
            ("", ""),
            ("A", ""),
        ]

        for text1, text2 in test_cases:
            sim = comparator._compute_similarity(text1, text2)
            assert 0.0 <= sim <= 1.0

    def test_compare_scientific_ocr_variants_should_match(self):
        """Known OCR variants from report formulas should still match."""
        lhs = "导丝兼容性可兼容0.038\"导丝。"
        rhs = "导丝兼容性可兼容0.038''导丝。"
        is_match, _, _ = compare_texts(lhs, rhs)
        assert is_match is True

        lhs = "还原物质检验液与同体积的同批空白对照液相比,高锰酸钾溶液[c(KMnO4)=0.002mol/L]的消耗量之差不超过2.0ml。"
        rhs = "还原物质检验液与同体积的同批空白对照液相比,高锰酸钾溶液[c(KMnO )=0.002mol/L]的消耗量之 4 差不超过2.0ml。"
        is_match, _, _ = compare_texts(lhs, rhs)
        assert is_match is True

        lhs = "重金属试验液呈现的颜色应不超过质量浓度为p(Pb2+)=1μg/mL的标准对照液。"
        rhs = "重金属试验液呈现的颜色应不超过质量浓度为ρ (Pb2+ )=1 µg/mL 的标准对照液。"
        is_match, _, _ = compare_texts(lhs, rhs)
        assert is_match is True

        lhs = "电阻值<=10Ω,电流>=0.5A。"
        rhs = "电阻值≦10Ω，电流≥0.5A。"
        is_match, _, _ = compare_texts(lhs, rhs)
        assert is_match is True


class TestDiffTypes:
    """Test different types of diffs."""

    def test_insertion_diff(self):
        """Test detection of insertions."""
        is_match, _, diffs = compare_texts("Test", "Test!")
        assert is_match is False
        assert any(d.type == "added" for d in diffs)

    def test_deletion_diff(self):
        """Test detection of deletions."""
        is_match, _, diffs = compare_texts("Test!", "Test")
        assert is_match is False
        assert any(d.type == "removed" for d in diffs)

    def test_replacement_diff(self):
        """Test detection of replacements."""
        is_match, _, diffs = compare_texts("Test", "Best")
        assert is_match is False
        # Should have both removed and added fragments

    def test_no_diff_for_same(self):
        """Test that identical texts have no diffs."""
        is_match, similarity, diffs = compare_texts("Identical", "Identical")
        assert is_match is True
        assert similarity == 1.0
        assert len(diffs) == 0
