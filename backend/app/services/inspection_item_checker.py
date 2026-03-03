"""
Inspection Item Checker for Report Self-Check (C07-C10).

Handles single item conclusion logic check, non-empty field check,
sequence continuity check, and continuation marker check.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.models.report_models import InspectionItem, InspectionTable
from app.services.text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class CheckStatus(str, Enum):
    """Status of a check result."""

    PASS = "pass"
    ERROR = "error"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a single check.

    Attributes:
        check_id: Check identifier (e.g., C07, C08, C09, C10)
        status: Check status
        message: Human-readable result message
        details: Additional details about the check
        warnings: List of warning messages
    """

    check_id: str
    status: CheckStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        if self.status == CheckStatus.PASS:
            self.status = CheckStatus.WARNING


@dataclass
class C07Result(CheckResult):
    """Result of C07: Single item conclusion check.

    Attributes:
        sequence_number: Sequence number of the item
        inspection_project: Name of the inspection project
        actual_conclusion: Actual conclusion from the report
        expected_conclusion: Expected conclusion based on test results
        test_result: Test result text
    """

    sequence_number: str = ""
    inspection_project: str = ""
    actual_conclusion: str = ""
    expected_conclusion: str = ""
    test_result: str = ""

    def __post_init__(self) -> None:
        """Set check_id if not provided."""
        if not self.check_id:
            object.__setattr__(self, 'check_id', "C07")


@dataclass
class C08Result(CheckResult):
    """Result of C08: Non-empty field check.

    Attributes:
        sequence_number: Sequence number of the item
        inspection_project: Name of the inspection project
        empty_fields: List of field names that are empty
        field_values: Dictionary of field names to their values
    """

    sequence_number: str = ""
    inspection_project: str = ""
    empty_fields: list[str] = field(default_factory=list)
    field_values: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set check_id if not provided."""
        if not self.check_id:
            object.__setattr__(self, 'check_id', "C08")


@dataclass
class C09Result(CheckResult):
    """Result of C09: Sequence continuity check.

    Attributes:
        first_number: First sequence number
        last_number: Last sequence number
        missing_numbers: List of missing sequence numbers
        duplicate_numbers: List of duplicate sequence numbers
        blank_positions: List of positions with blank sequence numbers
    """

    first_number: int = 0
    last_number: int = 0
    missing_numbers: list[int] = field(default_factory=list)
    duplicate_numbers: list[int] = field(default_factory=list)
    blank_positions: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Set check_id if not provided."""
        if not self.check_id:
            object.__setattr__(self, 'check_id', "C09")


@dataclass
class C10Result(CheckResult):
    """Result of C10: Continuation marker check.

    Attributes:
        missing_markers: List of positions missing "续" marker
        wrong_markers: List of positions with wrong "续" marker placement
        extra_markers: List of positions with unexpected "续" marker
    """

    missing_markers: list[tuple[int, str]] = field(default_factory=list)
    wrong_markers: list[int] = field(default_factory=list)
    extra_markers: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Set check_id if not provided."""
        if not self.check_id:
            object.__setattr__(self, 'check_id', "C10")


class InspectionItemChecker:
    """Checker for inspection item validation (C07-C10).

    Performs checks for:
    - C07: Single item conclusion logic check
    - C08: Non-empty field check
    - C09: Sequence continuity check
    - C10: Continuation marker check
    """

    # Empty value indicators for C08.
    # Per PRD C08, placeholders like "/" and "——" are non-empty values.
    EMPTY_VALUES = {"", "　"}
    NON_DATA_SEQUENCE_MARKERS = {"此处空白", "以下空白"}
    VALID_CONCLUSIONS = {"符合", "不符合", "/", "——"}

    def __init__(self, normalizer: TextNormalizer | None = None):
        """Initialize inspection item checker.

        Args:
            normalizer: Text normalizer for text comparison
        """
        self.normalizer = normalizer or TextNormalizer()

    def _is_empty_value(self, value: str) -> bool:
        """Check if value is considered empty.

        Args:
            value: Value to check

        Returns:
            True if value is empty or equivalent to empty
        """
        if value is None:
            return True
        stripped = str(value).strip()
        if not stripped or stripped in self.EMPTY_VALUES:
            return True
        return False

    def _normalize_for_comparison(self, text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""
        return self.normalizer.normalize(text).strip()

    def _extract_sequence_number(self, sequence_str: str) -> int | None:
        """Extract numeric sequence number from string.

        Args:
            sequence_str: Sequence string (may contain "续" prefix)

        Returns:
            Numeric sequence number or None
        """
        if not sequence_str:
            return None

        # Remove "续" prefix if present
        cleaned = sequence_str.replace("续", "").strip()

        try:
            return int(cleaned)
        except ValueError:
            return None

    def _is_non_data_sequence_marker(self, sequence_str: str) -> bool:
        """Whether sequence cell contains decorative non-data marker text."""
        compact = (sequence_str or "").strip().replace(" ", "")
        return any(marker in compact for marker in self.NON_DATA_SEQUENCE_MARKERS)

    def _is_structural_continuation_row(self, item: InspectionItem) -> bool:
        """Whether a blank-sequence row is likely a merged/continuation row.

        For merged table layouts, follow-up rows under the same sequence often keep
        sequence/project blank and only continue requirement/result text.
        """
        if (item.sequence_number or "").strip():
            return False

        # If project name appears without sequence, it's likely an abnormal blank row
        # (should be counted as C09 blank sequence issue).
        if (item.inspection_project or "").strip():
            return False

        return any(
            (value or "").strip()
            for value in (
                item.standard_clause,
                item.standard_requirement,
                item.test_result,
                item.item_conclusion,
                item.remark,
            )
        )

    def _get_sequence_first_rows(self, table: InspectionTable) -> list[InspectionItem]:
        """Get first non-continued row for each sequence.

        C07/C08 are sequence-level checks; merged/continued rows are attachment rows.
        """
        first_rows: dict[int, InspectionItem] = {}
        ordered_sequences: list[int] = []

        for item in table.items:
            seq_num = self._extract_sequence_number(item.sequence_number)
            if seq_num is None or item.is_continued:
                continue
            if seq_num not in first_rows:
                first_rows[seq_num] = item
                ordered_sequences.append(seq_num)

        return [first_rows[seq_num] for seq_num in ordered_sequences]

    def _get_sequence_groups(
        self, table: InspectionTable
    ) -> list[tuple[InspectionItem, list[InspectionItem]]]:
        """Group table rows by logical sequence number.

        Includes explicit sequence rows and subsequent blank-sequence continuation rows.
        """
        groups: dict[int, list[InspectionItem]] = {}
        first_rows: dict[int, InspectionItem] = {}
        ordered_sequences: list[int] = []
        current_seq: int | None = None

        for item in table.items:
            seq_num = self._extract_sequence_number(item.sequence_number)

            if seq_num is not None:
                current_seq = seq_num
                if seq_num not in groups:
                    groups[seq_num] = []
                    ordered_sequences.append(seq_num)
                groups[seq_num].append(item)
                # Prefer non-continued row as sequence first row.
                if seq_num not in first_rows or (first_rows[seq_num].is_continued and not item.is_continued):
                    first_rows[seq_num] = item
                continue

            if current_seq is None:
                continue
            if self._is_non_data_sequence_marker(item.sequence_number):
                continue

            # Attach blank-sequence rows carrying continuation content to current sequence.
            if not (item.sequence_number or "").strip():
                has_payload = any(
                    (value or "").strip()
                    for value in (
                        item.inspection_project,
                        item.standard_clause,
                        item.standard_requirement,
                        item.test_result,
                        item.item_conclusion,
                        item.remark,
                    )
                )
                if has_payload:
                    groups[current_seq].append(item)

        result: list[tuple[InspectionItem, list[InspectionItem]]] = []
        for seq in ordered_sequences:
            rows = groups.get(seq, [])
            if not rows:
                continue
            first = first_rows.get(seq, rows[0])
            result.append((first, rows))
        return result

    def _calculate_expected_conclusion(self, group_rows: list[InspectionItem]) -> str:
        """Calculate expected conclusion for a grouped sequence."""
        normalized_results = self._collect_group_result_tokens(group_rows)

        if any(("不符合要求" in r or r == "不符合") for r in normalized_results):
            return "不符合"

        if normalized_results and all(r in {"——", "/", "-"} for r in normalized_results):
            return "/"

        if any(r for r in normalized_results):
            return "符合"

        # When no reliable test-result token can be parsed, but placeholder markers
        # exist in adjacent columns due table-column shift, treat as "/".
        has_placeholder_marker = any(
            self._is_placeholder_token(value)
            for row in group_rows
            for value in (row.test_result, row.item_conclusion, row.remark)
        )
        if has_placeholder_marker:
            return "/"

        return "不符合"

    def _normalize_token(self, value: str) -> str:
        """Normalize a short token for rule evaluation."""
        return (value or "").strip().replace("／", "/")

    def _is_placeholder_token(self, value: str) -> bool:
        """Whether token is placeholder-like marker (/ or dashes)."""
        token = self._normalize_token(value)
        if not token:
            return False
        return bool(re.fullmatch(r"[—\-_/]+", token))

    def _is_result_like_token(self, value: str) -> bool:
        """Heuristic check whether a token looks like test-result content."""
        token = self._normalize_token(value)
        if not token:
            return False
        if self._is_placeholder_token(token):
            return True
        if "符合要求" in token or "不符合要求" in token:
            return True
        if token in {"符合", "不符合"}:
            return True
        if re.search(r"[≤≥＜＞<>]", token):
            return True
        if re.fullmatch(r"\d+(?:\.\d+)?", token):
            return True
        if re.search(r"\d", token) and re.search(r"(mA|A|V|W|Ω|℃|%|Hz|kHz|MHz)", token, re.IGNORECASE):
            return True
        return False

    def _should_accept_textual_result_token(self, token: str, row: InspectionItem) -> bool:
        """Accept descriptive test-result text when row conclusion is explicit."""
        normalized_token = self._normalize_token(token)
        if not normalized_token:
            return False
        normalized_conclusion = self._normalize_token(row.item_conclusion)
        if normalized_conclusion in {"符合", "不符合", "符合要求", "不符合要求"}:
            return True
        return False

    def _is_group_structured(self, group_rows: list[InspectionItem]) -> bool:
        """Whether sequence group likely has merged/shifted multi-row structure."""
        if len(group_rows) > 1:
            return True
        if any(not (row.sequence_number or "").strip() for row in group_rows):
            return True
        return False

    def _collect_group_result_tokens(self, group_rows: list[InspectionItem]) -> list[str]:
        """Collect normalized test-result tokens for a sequence group.

        Handles merged-table column shifts by checking adjacent columns when
        the test-result cell is empty.
        """
        tokens: list[str] = []
        structured = self._is_group_structured(group_rows)

        for row in group_rows:
            # Primary source: test_result column.
            raw_test = (row.test_result or "").strip()
            accepted_from_test = False
            if raw_test:
                parts = [
                    self._normalize_token(token)
                    for token in re.split(r"[；;]", raw_test)
                    if token and token.strip()
                ] or [self._normalize_token(raw_test)]
                for part in parts:
                    if self._is_result_like_token(part) or self._should_accept_textual_result_token(part, row):
                        tokens.append(part)
                        accepted_from_test = True

                # For structured rows, test_result may contain nested-table text while
                # true result token drifts to adjacent columns.
                if structured and not accepted_from_test:
                    for neighbor in (row.item_conclusion, row.remark):
                        neighbor_tokens = [
                            self._normalize_token(token)
                            for token in re.split(r"[；;]", (neighbor or "").strip())
                            if token and token.strip()
                        ] or [self._normalize_token((neighbor or "").strip())]
                        for token in neighbor_tokens:
                            if self._is_result_like_token(token) or self._should_accept_textual_result_token(token, row):
                                tokens.append(token)
                continue

            # Fallback for shifted columns: only accept placeholder markers
            # from adjacent columns (never accept non-placeholder text here).
            for neighbor in (row.item_conclusion, row.remark):
                marker = self._normalize_token(neighbor)
                if self._is_placeholder_token(marker):
                    tokens.append(marker)
                elif structured and (
                    self._is_result_like_token(marker)
                    or self._should_accept_textual_result_token(marker, row)
                ):
                    tokens.append(marker)

        return tokens

    def _get_logical_test_result_value(self, group_rows: list[InspectionItem]) -> str:
        """Get first meaningful logical test-result value in a sequence group."""
        structured = self._is_group_structured(group_rows)
        for row in group_rows:
            token = self._normalize_token(row.test_result)
            if self._is_result_like_token(token) or self._should_accept_textual_result_token(token, row):
                return token
            if not token or structured:
                for neighbor in (row.item_conclusion, row.remark):
                    neighbor_token = self._normalize_token(neighbor)
                    if self._is_placeholder_token(neighbor_token):
                        return neighbor_token
                    if structured and (
                        self._is_result_like_token(neighbor_token)
                        or self._should_accept_textual_result_token(neighbor_token, row)
                    ):
                        return neighbor_token
        return ""

    def _get_logical_item_conclusion_value(self, group_rows: list[InspectionItem]) -> str:
        """Get logical item-conclusion (supports shifted-column fallback)."""
        for row in group_rows:
            for candidate in (row.item_conclusion, row.remark):
                token = self._normalize_token(candidate)
                if token == "——":
                    token = "/"
                if token in self.VALID_CONCLUSIONS:
                    return token
        return ""

    def _get_logical_remark_value(self, group_rows: list[InspectionItem]) -> str:
        """Get first non-empty remark value in a sequence group."""
        for row in group_rows:
            value = (row.remark or "").strip()
            if value:
                return value
        return ""

    def _get_actual_conclusion(self, group_rows: list[InspectionItem]) -> str:
        """Get actual conclusion for a grouped sequence (prefer first non-empty)."""
        if not group_rows:
            return ""

        def _normalize_conclusion(value: str) -> str:
            normalized = (value or "").strip().replace("／", "/")
            if normalized == "——":
                return "/"
            return normalized

        first_row = group_rows[0]

        first_test = _normalize_conclusion(first_row.test_result)
        first_item = _normalize_conclusion(first_row.item_conclusion)
        first_remark = _normalize_conclusion(first_row.remark)
        group_tokens = self._collect_group_result_tokens(group_rows)
        all_tokens_placeholder = bool(group_tokens) and all(
            self._is_placeholder_token(token) for token in group_tokens
        )

        # Heuristic 1: result is placeholder, remark is placeholder, and item-conclusion
        # holds "符合/不符合" due shifted columns -> true conclusion should be "/".
        if (
            all_tokens_placeholder
            and
            self._is_placeholder_token(first_test)
            and self._is_placeholder_token(first_remark)
            and first_item in {"符合", "不符合"}
        ):
            return "/"

        # Heuristic 2: when item-conclusion column has placeholder but remark has
        # explicit conclusion (shifted), prefer remark conclusion.
        if (
            (not first_test or self._is_placeholder_token(first_test))
            and self._is_placeholder_token(first_item)
            and first_remark in {"符合", "不符合"}
        ):
            return first_remark

        if first_item in {"符合要求", "不符合要求"}:
            return "符合" if first_item == "符合要求" else "不符合"

        for candidate in (first_row.item_conclusion, first_row.remark):
            normalized = _normalize_conclusion(candidate)
            if normalized in {"符合要求", "不符合要求"}:
                return "符合" if normalized == "符合要求" else "不符合"
            if normalized in self.VALID_CONCLUSIONS:
                return normalized if normalized != "——" else "/"

        for row in group_rows:
            normalized = _normalize_conclusion(row.item_conclusion)
            if normalized in self.VALID_CONCLUSIONS:
                return normalized if normalized != "——" else "/"

        for row in group_rows:
            normalized = _normalize_conclusion(row.remark)
            if normalized in self.VALID_CONCLUSIONS:
                return normalized if normalized != "——" else "/"

        for row in group_rows:
            conclusion = (row.item_conclusion or "").strip()
            if conclusion:
                return conclusion
        return ""

    def check_c07_conclusion_logic(
        self, table: InspectionTable
    ) -> list[C07Result]:
        """Check C07: Single item conclusion logic.

        Verifies that each item's conclusion matches the expected conclusion
        based on test results using 3-priority rule:
        1. Any "不符合要求" or empty -> 不符合
        2. All "——" or "/" -> /
        3. Any "符合要求" or non-empty -> 符合

        Args:
            table: Inspection table to check

        Returns:
            List of C07Result for each item with mismatched conclusion
        """
        results: list[C07Result] = []

        for first_item, group_rows in self._get_sequence_groups(table):
            expected = self._calculate_expected_conclusion(group_rows)
            actual = self._get_actual_conclusion(group_rows)

            # Compare
            if expected == actual:
                continue  # Skip if matches

            # Mismatch found
            results.append(
                C07Result(
                    check_id="C07",
                    status=CheckStatus.ERROR,
                    message=(
                        f"序号{first_item.sequence_number} '{first_item.inspection_project}': "
                        f"结论不一致 - 期望'{expected}'，实际'{actual}'"
                    ),
                    sequence_number=first_item.sequence_number,
                    inspection_project=first_item.inspection_project,
                    actual_conclusion=actual,
                    expected_conclusion=expected,
                    test_result="；".join(
                        (row.test_result or "").strip()
                        for row in group_rows
                        if (row.test_result or "").strip()
                    ),
                    details={
                        "match": False,
                        "expected": expected,
                        "actual": actual,
                    },
                )
            )

        return results

    def check_c08_non_empty_fields(
        self, table: InspectionTable
    ) -> list[C08Result]:
        """Check C08: Non-empty field check.

        Verifies that test_result, item_conclusion, and remark fields
        are not empty for each item.

        Args:
            table: Inspection table to check

        Returns:
            List of C08Result for each item with empty fields
        """
        results: list[C08Result] = []

        fields_to_check = {
            "检验结果": "test_result",
            "单项结论": "item_conclusion",
            "备注": "remark",
        }

        for first_item, group_rows in self._get_sequence_groups(table):
            empty_fields: list[str] = []
            field_values: dict[str, str] = {
                "检验结果": self._get_logical_test_result_value(group_rows),
                "单项结论": self._get_logical_item_conclusion_value(group_rows),
                "备注": self._get_logical_remark_value(group_rows),
            }

            for display_name in fields_to_check:
                if self._is_empty_value(field_values.get(display_name, "")):
                    empty_fields.append(display_name)

            if empty_fields:
                results.append(
                    C08Result(
                        check_id="C08",
                        status=CheckStatus.ERROR,
                        message=(
                            f"序号{first_item.sequence_number} '{first_item.inspection_project}': "
                            f"字段为空 - {', '.join(empty_fields)}"
                        ),
                        sequence_number=first_item.sequence_number,
                        inspection_project=first_item.inspection_project,
                        empty_fields=empty_fields,
                        field_values=field_values,
                        details={
                            "empty_fields": empty_fields,
                            "field_values": field_values,
                        },
                    )
                )

        return results

    def check_c09_sequence_continuity(
        self, table: InspectionTable
    ) -> C09Result:
        """Check C09: Sequence number continuity.

        Verifies that sequence numbers start from 1 and are continuous
        without gaps, duplicates, or blanks.

        Args:
            table: Inspection table to check

        Returns:
            C09Result with continuity check details
        """
        result = C09Result(check_id="C09", status=CheckStatus.PASS)

        sequence_numbers: list[int] = []
        seen_sequences: dict[int, list[int]] = {}  # sequence -> list of positions
        blank_positions: list[int] = []

        for idx, item in enumerate(table.items):
            seq_num = self._extract_sequence_number(item.sequence_number)

            if seq_num is None:
                if self._is_non_data_sequence_marker(item.sequence_number):
                    continue
                if self._is_structural_continuation_row(item):
                    # Merged follow-up row; does not count as sequence blank.
                    continue
                blank_positions.append(idx + 1)
                continue

            if item.is_continued:
                # "续X" belongs to previous sequence and is validated in C10.
                continue

            sequence_numbers.append(seq_num)

            if seq_num not in seen_sequences:
                seen_sequences[seq_num] = []
            seen_sequences[seq_num].append(idx + 1)

        if not sequence_numbers:
            result.status = CheckStatus.ERROR
            result.message = "检验项目表格为空或所有序号无效"
            result.blank_positions = blank_positions
            return result

        # Sort unique sequence numbers
        unique_sequences = sorted(set(sequence_numbers))

        result.first_number = unique_sequences[0]
        result.last_number = unique_sequences[-1]

        # Check if starting from 1
        if result.first_number != 1:
            result.status = CheckStatus.ERROR
            result.message = f"序号未从1开始，起始序号为{result.first_number}"

        # Check for missing numbers
        expected = set(range(result.first_number, result.last_number + 1))
        missing = sorted(expected - set(unique_sequences))
        result.missing_numbers = missing

        if missing:
            result.status = CheckStatus.ERROR
            if result.message:
                result.message += f"；存在跳号: {missing}"
            else:
                result.message = f"存在跳号: {missing}"

        # Check for duplicates
        duplicates = [
            seq for seq, positions in seen_sequences.items() if len(positions) > 1
        ]
        result.duplicate_numbers = duplicates

        if duplicates:
            result.status = CheckStatus.ERROR
            if result.message:
                result.message += f"；存在重复序号: {duplicates}"
            else:
                result.message = f"存在重复序号: {duplicates}"

        # Check for blanks
        result.blank_positions = blank_positions
        if blank_positions:
            result.status = CheckStatus.ERROR
            if result.message:
                result.message += f"；存在空白序号(位置): {blank_positions}"
            else:
                result.message = f"存在空白序号(位置): {blank_positions}"

        # Set success message if no errors
        if result.status == CheckStatus.PASS:
            result.message = (
                f"序号连续完整: {result.first_number} ~ {result.last_number}，"
                f"共{len(unique_sequences)}项"
            )

        return result

    def check_c10_continuation_markers(
        self, table: InspectionTable
    ) -> C10Result:
        """Check C10: Continuation marker correctness.

        Verifies that:
        1. When a sequence continues across pages, the first row of the new page
           must have "续" prefix
        2. "续" marker should only appear on the first row of a page

        Args:
            table: Inspection table to check

        Returns:
            C10Result with continuation marker check details
        """
        result = C10Result(check_id="C10", status=CheckStatus.PASS)

        # Build page -> first row index map (data rows only)
        page_first_row: dict[int, int] = {}
        for item in table.items:
            page = item.source_page or 0
            row = item.row_index_in_page or 0
            if page <= 0:
                continue
            if page not in page_first_row:
                page_first_row[page] = row
            else:
                page_first_row[page] = min(page_first_row[page], row)

        # Group by numeric sequence and preserve global order position.
        sequence_groups: dict[int, list[tuple[int, InspectionItem]]] = {}
        for position, item in enumerate(table.items, start=1):
            seq_num = self._extract_sequence_number(item.sequence_number)
            if seq_num is None:
                continue
            sequence_groups.setdefault(seq_num, []).append((position, item))

        # Rule checks:
        # 1) First appearance of a sequence must not have "续".
        # 2) If same sequence appears on a later page, first row on that page must have "续".
        # 3) "续" can only appear on first data row of a page.
        for _, occurrences in sequence_groups.items():
            for idx, (position, item) in enumerate(occurrences):
                has_marker = item.sequence_number.startswith("续") or item.is_continued
                page = item.source_page or 0
                row = item.row_index_in_page or 0
                is_page_first_row = (
                    page > 0
                    and page in page_first_row
                    and row == page_first_row[page]
                )

                if idx == 0:
                    if has_marker:
                        result.extra_markers.append(position)
                        result.status = CheckStatus.ERROR
                    continue

                prev_item = occurrences[idx - 1][1]
                curr_page = item.source_page or 0
                prev_page = prev_item.source_page or 0
                page_changed = curr_page != prev_page
                no_page_info = curr_page == 0 and prev_page == 0

                if (page_changed or no_page_info) and not has_marker:
                    result.missing_markers.append((position, item.sequence_number))
                    result.status = CheckStatus.ERROR

                if has_marker and not is_page_first_row:
                    result.wrong_markers.append(position)
                    result.status = CheckStatus.ERROR

        # Build message
        error_parts: list[str] = []

        if result.missing_markers:
            error_parts.append(
                f"缺少续表标记 {len(result.missing_markers)}处"
            )
        if result.extra_markers:
            error_parts.append(
                f"多余续表标记 {len(result.extra_markers)}处"
            )
        if result.wrong_markers:
            error_parts.append(
                f"续字位置错误 {len(result.wrong_markers)}处"
            )

        if error_parts:
            result.message = "；".join(error_parts)
        else:
            result.message = "续表标记全部正确"

        return result

    def run_all_checks(
        self, table: InspectionTable
    ) -> dict[str, list[CheckResult] | CheckResult]:
        """Run all C07-C10 checks.

        Args:
            table: Inspection table to check

        Returns:
            Dictionary with check_id as key and results as value
        """
        results: dict[str, list[CheckResult] | CheckResult] = {
            "C07": [],
            "C08": [],
            "C09": None,
            "C10": None,
        }

        # C07: Conclusion logic check
        c07_results = self.check_c07_conclusion_logic(table)
        results["C07"] = c07_results

        # C08: Non-empty fields check
        c08_results = self.check_c08_non_empty_fields(table)
        results["C08"] = c08_results

        # C09: Sequence continuity check
        c09_result = self.check_c09_sequence_continuity(table)
        results["C09"] = c09_result

        # C10: Continuation marker check
        c10_result = self.check_c10_continuation_markers(table)
        results["C10"] = c10_result

        return results

    def get_summary(self, results: dict[str, list[CheckResult] | CheckResult]) -> dict[str, Any]:
        """Get summary of all check results.

        Args:
            results: Results from run_all_checks

        Returns:
            Summary dictionary with counts and status
        """
        summary: dict[str, Any] = {
            "total_items": 0,
            "c07_errors": 0,
            "c08_errors": 0,
            "c09_status": CheckStatus.PASS,
            "c10_status": CheckStatus.PASS,
            "overall_status": CheckStatus.PASS,
        }

        # Count C07 errors
        c07_results = results.get("C07", [])
        if isinstance(c07_results, list):
            summary["c07_errors"] = len(c07_results)

        # Count C08 errors
        c08_results = results.get("C08", [])
        if isinstance(c08_results, list):
            summary["c08_errors"] = len(c08_results)

        # Get C09 status
        c09_result = results.get("C09")
        if isinstance(c09_result, CheckResult):
            summary["c09_status"] = c09_result.status

        # Get C10 status
        c10_result = results.get("C10")
        if isinstance(c10_result, CheckResult):
            summary["c10_status"] = c10_result.status

        # Determine overall status
        if (
            summary["c07_errors"] > 0
            or summary["c08_errors"] > 0
            or summary["c09_status"] == CheckStatus.ERROR
            or summary["c10_status"] == CheckStatus.ERROR
        ):
            summary["overall_status"] = CheckStatus.ERROR
        elif (
            summary["c09_status"] == CheckStatus.WARNING
            or summary["c10_status"] == CheckStatus.WARNING
        ):
            summary["overall_status"] = CheckStatus.WARNING

        return summary


def create_inspection_item_checker(
    normalizer: TextNormalizer | None = None,
) -> InspectionItemChecker:
    """Create inspection item checker instance.

    Args:
        normalizer: Optional text normalizer

    Returns:
        InspectionItemChecker instance
    """
    return InspectionItemChecker(normalizer=normalizer)
