"""
Table Expansion Comparator.

Handles "见表X" references by expanding table content and comparing
parameter names and values.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from app.models.ptr_models import PTRClause, PTRDocument, PTRTable
from app.models.report_models import InspectionItem
from app.services.text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)


@dataclass
class ParameterComparison:
    """Result of comparing a single parameter.

    Attributes:
        parameter_name: Name of the parameter
        ptr_value: Value from PTR table
        report_value: Value from report
        matches: Whether values match
        is_expanded: Whether this was from a "见表X" expansion
    """

    parameter_name: str
    ptr_value: str
    report_value: str
    matches: bool
    is_expanded: bool = False


@dataclass
class TableExpansionResult:
    """Result of table expansion and comparison.

    Attributes:
        table_number: Table number that was expanded
        table_found: Whether the table was found in PTR
        parameters: List of parameter comparisons
        total_matches: Number of matching parameters
        total_parameters: Total number of parameters
    """

    table_number: int
    table_found: bool
    parameters: list[ParameterComparison] = field(default_factory=list)
    total_matches: int = 0
    total_parameters: int = 0

    @property
    def all_match(self) -> bool:
        """Check if all parameters match."""
        return self.total_matches == self.total_parameters and self.total_parameters > 0

    @property
    def match_rate(self) -> float:
        """Calculate match rate."""
        if self.total_parameters == 0:
            return 0.0
        return self.total_matches / self.total_parameters


class TableComparator:
    """Compares table-referenced content between PTR and report."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
    ):
        """Initialize table comparator.

        Args:
            normalizer: Text normalizer instance (created if None)
        """
        self.normalizer = normalizer or TextNormalizer()

    def compare_table_references(
        self,
        ptr_doc: PTRDocument,
        report_items: list[InspectionItem],
    ) -> list[TableExpansionResult]:
        """Compare all table-referenced clauses.

        Args:
            ptr_doc: PTR document
            report_items: List of inspection items from report

        Returns:
            List of table expansion results
        """
        results: list[TableExpansionResult] = []

        # Find clauses with table references
        for clause in ptr_doc.clauses:
            if not clause.has_table_references():
                continue

            for table_ref in clause.table_references:
                result = self._compare_table_reference(
                    table_ref.table_number,
                    clause,
                    ptr_doc,
                    report_items,
                )
                results.append(result)

        return results

    def _compare_table_reference(
        self,
        table_number: int,
        clause: PTRClause,
        ptr_doc: PTRDocument,
        report_items: list[InspectionItem],
    ) -> TableExpansionResult:
        """Compare a single table reference.

        Args:
            table_number: Table number to expand
            clause: Clause containing the reference
            ptr_doc: PTR document
            report_items: Report items to compare against

        Returns:
            TableExpansionResult
        """
        result = TableExpansionResult(
            table_number=table_number,
            table_found=False,
        )

        # Find table in PTR
        ptr_table = ptr_doc.get_table_by_number(table_number)
        if not ptr_table:
            logger.warning(f"Table {table_number} not found in PTR document")
            return result

        result.table_found = True

        # Find matching report item
        report_item = self._find_matching_report_item(clause, report_items)
        if not report_item:
            logger.info(f"No matching report item for clause {clause.number}")
            return result

        # Compare parameters
        result.parameters = self._compare_table_parameters(
            ptr_table,
            report_item,
        )

        # Calculate statistics
        result.total_parameters = len(result.parameters)
        result.total_matches = sum(1 for p in result.parameters if p.matches)

        return result

    def _find_matching_report_item(
        self,
        clause: PTRClause,
        report_items: list[InspectionItem],
    ) -> InspectionItem | None:
        """Find the report item matching a clause.

        Args:
            clause: PTR clause
            report_items: List of inspection items

        Returns:
            Matching item or None
        """
        clause_num_str = str(clause.number)

        # Prefer report standard clause column.
        for item in report_items:
            std_clause = self._extract_clause_number(item.standard_clause)
            if std_clause and std_clause == clause_num_str:
                return item

        # Try exact match on sequence number
        for item in report_items:
            if item.sequence_number == clause_num_str:
                return item

        # Try partial match
        for item in report_items:
            if item.sequence_number.startswith(clause_num_str):
                return item

        # Try text match
        clause_text = self.normalizer.normalize(clause.text_content)
        for item in report_items:
            item_text = self.normalizer.normalize(item.inspection_project)
            if clause_text in item_text or item_text in clause_text:
                return item

        return None

    def _extract_clause_number(self, text: str) -> str:
        """Extract normalized clause number from report standard clause text."""
        if not text:
            return ""
        import re

        match = re.search(r"(\d+(?:\.\d+)+)", text)
        return match.group(1) if match else ""

    def _compare_table_parameters(
        self,
        ptr_table: PTRTable,
        report_item: InspectionItem,
    ) -> list[ParameterComparison]:
        """Compare parameters from PTR table with report item.

        Args:
            ptr_table: PTR table
            report_item: Report inspection item

        Returns:
            List of parameter comparisons
        """
        comparisons: list[ParameterComparison] = []

        # Get report test result (may contain parameter values)
        report_text = report_item.test_result

        # Compare each row in PTR table
        for row in ptr_table.rows:
            if not row:
                continue

            # First column is typically parameter name
            param_name = row[0] if row else ""
            ptr_value = row[1] if len(row) > 1 else ""

            if not param_name:
                continue

            # Try to find this parameter in report text
            report_value = self._extract_parameter_value(param_name, report_text)

            # Compare values
            matches = self._compare_values(ptr_value, report_value)

            comparison = ParameterComparison(
                parameter_name=param_name,
                ptr_value=ptr_value,
                report_value=report_value,
                matches=matches,
                is_expanded=True,
            )
            comparisons.append(comparison)

        return comparisons

    def _extract_parameter_value(
        self,
        param_name: str,
        report_text: str,
    ) -> str:
        """Extract parameter value from report text.

        Args:
            param_name: Name of parameter to find
            report_text: Report test result text

        Returns:
            Extracted value or empty string
        """
        if not param_name or not report_text:
            return ""

        # Normalize for comparison
        norm_name = self.normalizer.normalize(param_name)
        norm_text = self.normalizer.normalize(report_text)

        # Look for parameter name followed by value
        # Common patterns: "参数：值", "参数: 值", "参数 值"
        import re

        # Try pattern: parameter name followed by colon and value
        pattern = re.escape(norm_name) + r"[:：]\s*([^\n，,。.]+)"
        match = re.search(pattern, norm_text)
        if match:
            return match.group(1).strip()

        # Try pattern: parameter name followed by space and value
        pattern = re.escape(norm_name) + r"\s+([^\n，,。.]+?)(?:\s|[,，。.]|$)"
        match = re.search(pattern, norm_text)
        if match:
            return match.group(1).strip()

        return ""

    def _compare_values(self, value1: str, value2: str) -> bool:
        """Compare two parameter values.

        Args:
            value1: First value
            value2: Second value

        Returns:
            True if values match
        """
        if not value1 and not value2:
            return True

        norm1 = self.normalizer.normalize(value1)
        norm2 = self.normalizer.normalize(value2)

        return norm1 == norm2


def compare_table_expansions(
    ptr_doc: PTRDocument,
    report_items: list[InspectionItem],
) -> list[TableExpansionResult]:
    """Convenience function to compare table expansions.

    Args:
        ptr_doc: PTR document
        report_items: List of inspection items

    Returns:
        List of table expansion results
    """
    comparator = TableComparator()
    return comparator.compare_table_references(ptr_doc, report_items)


def get_table_expansion_summary(
    results: list[TableExpansionResult],
) -> dict[str, Any]:
    """Get summary of table expansion comparisons.

    Args:
        results: List of table expansion results

    Returns:
        Summary dictionary
    """
    total_tables = len(results)
    found_tables = sum(1 for r in results if r.table_found)
    total_params = sum(r.total_parameters for r in results)
    total_matches = sum(r.total_matches for r in results)

    return {
        "total_tables": total_tables,
        "found_tables": found_tables,
        "total_parameters": total_params,
        "total_matches": total_matches,
        "match_rate": total_matches / total_params if total_params > 0 else 0.0,
    }
