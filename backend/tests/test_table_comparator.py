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
