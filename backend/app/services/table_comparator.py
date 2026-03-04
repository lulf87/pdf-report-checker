"""
Table Expansion Comparator.

Handles "见表X" references by expanding table content and comparing
parameter names and values.
"""

import logging
import re
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
        clause_number: PTR clause number that references this table
        parameters: List of parameter comparisons
        total_matches: Number of matching parameters
        total_parameters: Total number of parameters
    """

    table_number: int
    table_found: bool
    parameters: list[ParameterComparison] = field(default_factory=list)
    total_matches: int = 0
    total_parameters: int = 0
    clause_number: str = ""

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
            clause_number=str(clause.number),
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

        # Use multiple report columns to improve extraction robustness.
        report_text = "\n".join(
            part
            for part in [
                report_item.test_result or "",
                report_item.standard_requirement or "",
                report_item.inspection_project or "",
            ]
            if part and part.strip()
        )

        # Compare each row in PTR table
        for row in ptr_table.rows:
            if not row:
                continue

            # First column is typically parameter name
            param_name = row[0] if row else ""
            ptr_value = self._pick_ptr_value_from_row(row)

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
        compact_name = re.sub(r"\s+", "", norm_name)
        compact_text = re.sub(r"\s+", "", norm_text)

        # Try line-oriented matching first (better for OCR line breaks).
        lines = [line.strip() for line in report_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            normalized_line = self.normalizer.normalize(line)
            compact_line = re.sub(r"\s+", "", normalized_line)
            if compact_name and compact_name not in compact_line:
                continue

            # Pattern: 参数[:：=]值
            same_line = re.search(
                re.escape(norm_name) + r"\s*[:：=]\s*([^\n，,。；;]+)",
                normalized_line,
            )
            if same_line:
                return same_line.group(1).strip()

            # Pattern: 参数 值（同一行）
            same_line = re.search(
                re.escape(norm_name) + r"\s+([^\n，,。；;]+)",
                normalized_line,
            )
            if same_line:
                return same_line.group(1).strip()

            # Pattern: 参数在当前行，值在下一行
            if idx + 1 < len(lines):
                next_line = self.normalizer.normalize(lines[idx + 1]).strip()
                if next_line:
                    return next_line

        # Fallback: compact-text regex, tolerant to OCR spacing.
        compact_pattern = re.escape(compact_name) + r"(?:[:：=]|)([^，,。；;]{1,40})"
        compact_match = re.search(compact_pattern, compact_text)
        if compact_match:
            candidate = compact_match.group(1).strip()
            candidate = re.sub(r"^[=:：\-\s]+", "", candidate).strip()
            if candidate:
                return candidate

        # Last-resort: if parameter name appears, return nearby numeric expression.
        idx = compact_text.find(compact_name)
        if idx >= 0:
            window = compact_text[idx: idx + len(compact_name) + 60]
            numeric = self._extract_primary_numeric_token(window)
            if numeric:
                return numeric

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

        # Treat placeholders as empty equivalents.
        if self._is_placeholder(value1) and self._is_placeholder(value2):
            return True

        norm1 = self.normalizer.normalize(value1)
        norm2 = self.normalizer.normalize(value2)

        if self._is_placeholder(norm1) and self._is_placeholder(norm2):
            return True

        # Fast path: normalized exact match
        if norm1 == norm2:
            return True

        compact1 = re.sub(r"\s+", "", norm1)
        compact2 = re.sub(r"\s+", "", norm2)
        if compact1 == compact2:
            return True

        # Semantic numeric comparison
        if self._evaluate_numeric_constraint(expected=norm1, actual=norm2):
            return True

        if self._evaluate_numeric_constraint(expected=norm2, actual=norm1):
            return True

        # If both contain the same ordered numeric tokens, consider equal.
        nums1 = self._extract_all_numbers(norm1)
        nums2 = self._extract_all_numbers(norm2)
        if nums1 and nums2 and nums1 == nums2:
            return True

        # Unit-only differences that survive normalizer should not fail.
        unitless1 = re.sub(r"[A-Za-zμΩ/%]+", "", compact1)
        unitless2 = re.sub(r"[A-Za-zμΩ/%]+", "", compact2)
        if unitless1 and unitless1 == unitless2:
            return True

        return norm1 == norm2

    def _pick_ptr_value_from_row(self, row: list[str]) -> str:
        """Pick PTR expected value from table row."""
        if not row or len(row) < 2:
            return ""
        for cell in row[1:]:
            value = (cell or "").strip()
            if value:
                return value
        return ""

    def _is_placeholder(self, value: str) -> bool:
        """Whether value is placeholder/empty equivalent."""
        compact = re.sub(r"\s+", "", value or "")
        return compact in {"", "/", "／", "-", "—", "——", "N/A", "NA"}

    def _extract_all_numbers(self, text: str) -> list[str]:
        """Extract normalized numeric tokens from text."""
        if not text:
            return []
        return re.findall(r"[-+]?\d+(?:\.\d+)?", text)

    def _extract_primary_numeric_token(self, text: str) -> str:
        """Extract a likely primary numeric constraint/value token."""
        if not text:
            return ""
        token_pattern = re.compile(
            r"(?:<=|>=|<|>|≤|≥)?\s*[-+]?\d+(?:\.\d+)?(?:\s*±\s*[-+]?\d+(?:\.\d+)?%?)?"
        )
        match = token_pattern.search(text)
        return match.group(0).strip() if match else ""

    def _evaluate_numeric_constraint(self, expected: str, actual: str) -> bool:
        """Evaluate numeric constraint expressions.

        Supported expected patterns:
        - <=2.0, <2.0, >=, >
        - 20~350 / 20-350 / 20至350
        - 100±5 / 100±20%
        """
        expected_norm = self._normalize_math_symbols(expected)
        actual_norm = self._normalize_math_symbols(actual)

        actual_value = self._extract_single_numeric(actual_norm)
        if actual_value is None:
            return False

        # Range: a~b / a-b / a至b
        range_match = re.search(
            r"([-+]?\d+(?:\.\d+)?)\s*(?:~|～|至|到|-)\s*([-+]?\d+(?:\.\d+)?)",
            expected_norm,
        )
        if range_match:
            lo = float(range_match.group(1))
            hi = float(range_match.group(2))
            if lo > hi:
                lo, hi = hi, lo
            return lo <= actual_value <= hi

        # Comparator: <=x, <x, >=x, >x
        cmp_match = re.search(r"(<=|>=|<|>)\s*([-+]?\d+(?:\.\d+)?)", expected_norm)
        if cmp_match:
            op = cmp_match.group(1)
            threshold = float(cmp_match.group(2))
            if op == "<":
                return actual_value < threshold
            if op == "<=":
                return actual_value <= threshold
            if op == ">":
                return actual_value > threshold
            if op == ">=":
                return actual_value >= threshold

        # Tolerance: base±tol or base±pct%
        tol_match = re.search(
            r"([-+]?\d+(?:\.\d+)?)\s*±\s*([-+]?\d+(?:\.\d+)?)(%)?",
            expected_norm,
        )
        if tol_match:
            base = float(tol_match.group(1))
            tol = float(tol_match.group(2))
            if tol_match.group(3):
                tol = abs(base) * tol / 100.0
            return (base - tol) <= actual_value <= (base + tol)

        return False

    def _extract_single_numeric(self, text: str) -> float | None:
        """Extract first numeric value as float."""
        if not text:
            return None
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

    def _normalize_math_symbols(self, text: str) -> str:
        """Normalize math symbols for constraint parsing."""
        normalized = (text or "").strip()
        normalized = normalized.replace("≤", "<=").replace("≦", "<=").replace("＜", "<")
        normalized = normalized.replace("≥", ">=").replace("≧", ">=").replace("＞", ">")
        normalized = normalized.replace("—", "-").replace("–", "-").replace("−", "-")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized


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
