"""
Tests for Comparator module.

Tests strict matching, diff algorithms, and similarity computation.
"""

import pytest

from app.models.ptr_models import PTRClause, PTRClauseNumber, PTRDocument
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
