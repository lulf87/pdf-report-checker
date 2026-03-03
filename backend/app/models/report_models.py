"""
Data models for Report document parsing.

Defines structures for report clauses, inspection items, and test results.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InspectionItem:
    """A single inspection item from the report.

    Attributes:
        sequence_number: Serial number (序号)
        inspection_project: Test item name (检验项目)
        standard_clause: Reference standard clause (标准条款)
        standard_requirement: Required standard (标准要求)
        test_result: Actual test result (检验结果)
        item_conclusion: Single item conclusion (单项结论)
        remark: Notes (备注)
        is_continued: Whether this is a continued row from previous page
        is_merged: Whether this row has merged cells
    """

    sequence_number: str = ""
    inspection_project: str = ""
    standard_clause: str = ""
    standard_requirement: str = ""
    test_result: str = ""
    item_conclusion: str = ""
    remark: str = ""
    is_continued: bool = False
    is_merged: bool = False
    source_page: int = 0
    row_index_in_page: int = 0

    @property
    def is_complete(self) -> bool:
        """Check if all required fields are non-empty."""
        return bool(
            self.sequence_number
            and self.inspection_project
            and self.test_result
            and self.item_conclusion
            and self.remark
        )

    @property
    def expected_conclusion(self) -> str:
        """Calculate expected conclusion based on test results."""
        # Rule 1: Any "不符合要求" or empty -> 不符合
        if "不符合要求" in self.test_result or not self.test_result.strip():
            return "不符合"

        # Rule 2: All "——" or "/" -> /
        results = self.test_result.split("；") if self.test_result else []
        if all(r.strip() in ["——", "/", ""] for r in results):
            return "/"

        # Rule 3: Any "符合要求" or non-empty -> 符合
        return "符合"

    @property
    def conclusion_matches(self) -> bool:
        """Check if actual conclusion matches expected."""
        return self.item_conclusion == self.expected_conclusion


@dataclass
class InspectionTable:
    """A complete inspection table from the report.

    Attributes:
        items: List of inspection items
        page_start: Starting page number
        page_end: Ending page number
        table_number: Table number (if multiple)
        headers: Table headers
    """

    items: list[InspectionItem] = field(default_factory=list)
    page_start: int = 1
    page_end: int = 1
    table_number: int | None = None
    headers: list[str] = field(default_factory=list)

    @property
    def num_items(self) -> int:
        """Number of inspection items."""
        return len(self.items)

    def get_item_by_sequence(self, seq: str) -> InspectionItem | None:
        """Find item by sequence number."""
        for item in self.items:
            # Handle "续X" prefix
            clean_seq = item.sequence_number.replace("续", "").strip()
            if clean_seq == seq.replace("续", "").strip():
                return item
        return None

    def check_sequence_continuity(self) -> list[str]:
        """Check for gaps or duplicates in sequence numbers.

        Returns:
            List of error messages
        """
        errors: list[str] = []
        sequences = []

        for item in self.items:
            # Extract numeric part
            seq_str = item.sequence_number.replace("续", "").strip()
            try:
                seq_num = int(seq_str)
                sequences.append(seq_num)
            except ValueError:
                errors.append(f"Invalid sequence number: {item.sequence_number}")

        # Check for gaps
        if sequences:
            sequences = sorted(set(sequences))  # Remove duplicates and sort
            for i in range(1, len(sequences)):
                if sequences[i] != sequences[i - 1] + 1:
                    errors.append(
                        f"Sequence gap: {sequences[i - 1]} -> {sequences[i]}"
                    )

        return errors

    def check_continuation_markers(self) -> list[str]:
        """Check proper use of '续' markers across pages.

        Returns:
            List of error messages
        """
        errors: list[str] = []

        for i, item in enumerate(self.items):
            if item.is_continued:
                # First item with this sequence should not have "续"
                seq = item.sequence_number.replace("续", "").strip()
                if i == 0:
                    errors.append(f"First item marked as continued: {seq}")
                else:
                    prev_item = self.items[i - 1]
                    prev_seq = prev_item.sequence_number.replace("续", "").strip()
                    if prev_seq != seq:
                        errors.append(
                            f"Continuation marker without matching previous: {seq}"
                        )

        return errors


@dataclass
class ReportField:
    """A field extracted from the report (e.g., from page 3).

    Attributes:
        field_name: Name of the field
        value: Field value
        source_page: Page number where found
        position: Position on page
    """

    field_name: str
    value: str
    source_page: int = 1
    position: tuple[int, int] | None = None


@dataclass
class ThirdPageFields:
    """Fields extracted from the report's third page (检验报告首页).

    Attributes:
        client: 委托方
        sample_name: 样品名称
        model_spec: 型号规格
        inspection_items: 检验项目 (list)
        standard_content: 标准的内容
        standard_ranges: Excluded standard ranges for comparison
    """

    client: str = ""
    sample_name: str = ""
    model_spec: str = ""
    production_date: str = ""
    product_id_batch: str = ""
    client_address: str = ""
    inspection_items: list[str] = field(default_factory=list)
    standard_content: str = ""
    standard_ranges: list[tuple[int, int]] = field(default_factory=list)

    @property
    def has_standard_content_exclusion(self) -> bool:
        """Check if there's a standard content exclusion."""
        return bool(self.standard_content)

    def is_sequence_excluded(self, seq_str: str) -> bool:
        """Check if a sequence number is in excluded range.

        Args:
            seq_str: Sequence number like "2.1.1" or "3"

        Returns:
            True if excluded from comparison
        """
        if not self.standard_ranges:
            return False

        # Parse the sequence number
        try:
            parts = seq_str.split(".")
            # Handle both "2.1.1" and "1" formats
            if len(parts) >= 1:
                last_num = int(parts[-1])
                # Check if any range includes this number
                for start, end in self.standard_ranges:
                    if start <= last_num <= end:
                        return True
        except (ValueError, IndexError):
            pass

        return False


@dataclass
class ReportDocument:
    """Complete parsed report document.

    Attributes:
        inspection_table: Main inspection table
        third_page_fields: Fields from page 3
        first_page_fields: Fields from page 1
        metadata: Document metadata
    """

    inspection_table: InspectionTable | None = None
    third_page_fields: ThirdPageFields | None = None
    first_page_fields: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_inspection_item(self, seq: str) -> InspectionItem | None:
        """Get inspection item by sequence number."""
        if self.inspection_table:
            return self.inspection_table.get_item_by_sequence(seq)
        return None

    def get_excluded_sequences(self) -> list[str]:
        """Get list of excluded sequence numbers."""
        excluded: list[str] = []

        if self.third_page_fields and self.inspection_table:
            for item in self.inspection_table.items:
                if self.third_page_fields.is_sequence_excluded(
                    item.sequence_number
                ):
                    excluded.append(item.sequence_number)

        return excluded

    @property
    def total_inspection_items(self) -> int:
        """Total number of inspection items."""
        return self.inspection_table.num_items if self.inspection_table else 0

    @property
    def valid_inspection_items(self) -> list[InspectionItem]:
        """Get inspection items that are not excluded."""
        if not self.inspection_table:
            return []

        if not self.third_page_fields:
            return self.inspection_table.items

        return [
            item
            for item in self.inspection_table.items
            if not self.third_page_fields.is_sequence_excluded(item.sequence_number)
        ]
