"""
Report Clause Extractor.

Extracts inspection items, fields, and test results from inspection reports.
Handles complex table structures with merged cells and continuation markers.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from app.models.common_models import CellData, PDFDocument, PDFPage, TableData
from app.models.report_models import (
    InspectionItem,
    InspectionTable,
    ReportDocument,
    ReportField,
    ThirdPageFields,
)
from app.services.pdf_parser import PDFParser
from app.services.table_normalizer import TableNormalizer

logger = logging.getLogger(__name__)

# Regular expressions for report parsing
INSPECTION_ITEM_PATTERN: Final = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")

# Standard content exclusion pattern
STANDARD_CONTENT_PATTERN: Final = re.compile(
    r"标准的内容\s*[:：]\s*([^\n]+)"
)

# Standard range pattern: 2.1.1-2.1.5
STANDARD_RANGE_PATTERN: Final = re.compile(
    r"(\d+(?:\.\d+)*)\s*[-~至到]\s*(\d+(?:\.\d+)*)"
)

# Field name patterns for page 3
FIELD_PATTERNS: Final = {
    # Some reports use "字段: 值", others use "字段\\n值" in table-like layout.
    # Keep ":" optional to support both.
    "委托方": r"委\s*托\s*方\s*(?:[:：]\s*)?([^\n]+)",
    "样品名称": r"样\s*品\s*名\s*称\s*(?:[:：]\s*)?([^\n]+)",
    "型号规格": r"型\s*号\s*规\s*格\s*(?:[:：]\s*)?([^\n]+)",
    "检验项目": r"检\s*验\s*项\s*目\s*(?:[:：]\s*)?([^\n]+)",
    "生产日期": r"生\s*产\s*日\s*期\s*(?:[:：]\s*)?([^\n]+)",
    "产品编号/批号": r"(?:产\s*品\s*编\s*号\s*[/／]?\s*批\s*号|产品编号|批号)\s*(?:[:：]\s*)?([^\n]+)",
    "委托方地址": r"(?:委\s*托\s*方\s*地\s*址|委托方地址)\s*(?:[:：]\s*)?([^\n]+)",
}

# Table headers for inspection table
INSPECTION_HEADERS: Final = [
    "序号",
    "检验项目",
    "标准条款",
    "标准要求",
    "检验结果",
    "单项结论",
    "备注",
]


@dataclass
class ExtractionState:
    """State for report extraction process.

    Attributes:
        current_sequence: Current sequence number
        continued_sequence: Sequence being continued across pages
        merged_cell_value: Value from merged cell to propagate
    """

    current_sequence: str = ""
    continued_sequence: str = ""
    merged_cell_value: str = ""


class ReportExtractor:
    """Extracts inspection data from report documents."""

    def __init__(
        self,
        pdf_parser: PDFParser | None = None,
        use_ocr: bool = True,
    ):
        """Initialize report extractor.

        Args:
            pdf_parser: PDF parser instance (created if None)
            use_ocr: Whether to enable OCR fallback
        """
        self.pdf_parser = pdf_parser or PDFParser(ocr_fallback=use_ocr)
        self.use_ocr = use_ocr
        self.state = ExtractionState()
        self.table_normalizer = TableNormalizer()

    def extract_from_file(self, file_path: str | Path) -> ReportDocument:
        """Extract report content from a PDF file.

        Args:
            file_path: Path to report PDF file

        Returns:
            ReportDocument with all extracted data
        """
        file_path = Path(file_path)
        logger.info(f"Extracting report from: {file_path}")

        # Parse PDF
        pdf_doc = self.pdf_parser.parse(file_path)

        # Extract report content
        return self.extract_from_pdf_doc(pdf_doc)

    def extract_from_pdf_doc(self, pdf_doc: PDFDocument) -> ReportDocument:
        """Extract report content from a parsed PDF document.

        Args:
            pdf_doc: Parsed PDF document

        Returns:
            ReportDocument with all extracted data
        """
        report_doc = ReportDocument()
        report_doc.metadata = pdf_doc.metadata

        # Extract fields from page 1 (首页)
        if pdf_doc.pages:
            report_doc.first_page_fields = self._extract_first_page_fields(
                pdf_doc.pages[0]
            )

        # Extract fields from page 3 (检验报告首页)
        third_page = self._find_third_page(pdf_doc)
        if third_page:
            report_doc.third_page_fields = self._extract_third_page_fields(third_page)

        # Parse "标准的内容" exclusion ranges from page 4 explanation area.
        standard_ranges = self._extract_standard_exclusion_ranges(pdf_doc)
        if standard_ranges:
            if not report_doc.third_page_fields:
                report_doc.third_page_fields = ThirdPageFields()
            report_doc.third_page_fields.standard_ranges = standard_ranges
            report_doc.third_page_fields.standard_content = "parsed_from_page4"

        # Extract inspection table
        report_doc.inspection_table = self._extract_inspection_table(pdf_doc)

        logger.info(
            f"Extracted report with {report_doc.total_inspection_items} "
            f"inspection items"
        )

        return report_doc

    def _find_third_page(self, pdf_doc: PDFDocument) -> PDFPage | None:
        """Find the third page (检验报告首页).

        The third page is identified by the text "检验报告首页" in the header.

        Args:
            pdf_doc: Parsed PDF document

        Returns:
            PDFPage or None
        """
        for page in pdf_doc.pages:
            compact_text = re.sub(r"\s+", "", page.raw_text or "")
            if "检验报告首页" in compact_text:
                logger.debug(f"Found third page (检验报告首页) at page {page.page_number}")
                return page
        return None

    def _extract_first_page_fields(self, page: PDFPage) -> dict[str, str]:
        """Extract fields from the first page (report cover).

        Args:
            page: First page of report

        Returns:
            Dictionary of field names to values
        """
        fields: dict[str, str] = {}

        # 1) Colon-based extraction (e.g., "字段: 值")
        lines = page.raw_text.split("\n")
        for line in lines:
            line = line.strip()
            if ":" in line or "：" in line:
                parts = re.split(r"[:：]", line, maxsplit=1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        fields[key] = value

        # 2) Table-like extraction where field and value are on separate lines.
        # This pattern is common for cover-page keys used by C01.
        compact_text = page.raw_text or ""
        key_patterns = {
            "委托方": r"委\s*托\s*方\s*(?:[:：]\s*)?([^\n]+)",
            "样品名称": r"样\s*品\s*名\s*称\s*(?:[:：]\s*)?([^\n]+)",
            "型号规格": r"型\s*号\s*规\s*格\s*(?:[:：]\s*)?([^\n]+)",
        }
        alias_map = {
            "委托方": "client",
            "样品名称": "sample_name",
            "型号规格": "model_spec",
        }
        for display_name, pattern in key_patterns.items():
            match = re.search(pattern, compact_text)
            if not match:
                continue
            value = match.group(1).strip()
            if not value:
                continue
            fields[display_name] = value
            fields[alias_map[display_name]] = value

        return fields

    def _extract_third_page_fields(self, page: PDFPage) -> ThirdPageFields:
        """Extract fields from the third page.

        Args:
            page: Third page (检验报告首页)

        Returns:
            ThirdPageFields with extracted data
        """
        fields = ThirdPageFields()

        # Extract named fields
        for field_name, pattern in FIELD_PATTERNS.items():
            match = re.search(pattern, page.raw_text)
            if match:
                value = match.group(1).strip()
                if field_name == "委托方":
                    fields.client = value
                elif field_name == "样品名称":
                    fields.sample_name = value
                elif field_name == "型号规格":
                    fields.model_spec = value
                elif field_name == "检验项目":
                    # Parse comma-separated list
                    items = [item.strip() for item in re.split(r"[,，、]", value)]
                    fields.inspection_items = items
                elif field_name == "生产日期":
                    fields.production_date = value
                elif field_name == "产品编号/批号":
                    fields.product_id_batch = value
                elif field_name == "委托方地址":
                    fields.client_address = value

        # Some reports split address across multiple lines; merge until next field.
        multiline_address = self._extract_multiline_field_value(
            page.raw_text,
            label_pattern=r"委\s*托\s*方\s*地\s*址",
            stop_label_patterns=[
                r"产\s*品\s*编\s*号",
                r"批\s*号",
                r"生\s*产\s*单\s*位",
                r"受\s*检\s*单\s*位",
                r"抽\s*样\s*单\s*编\s*号",
                r"抽\s*样\s*单\s*位",
                r"抽\s*样\s*地\s*点",
                r"抽\s*样\s*日\s*期",
                r"到\s*样\s*日\s*期",
                r"检\s*验\s*项\s*目",
                r"检\s*验\s*日\s*期",
                r"检\s*验\s*地\s*点",
                r"样\s*品\s*数\s*量",
            ],
        )
        if multiline_address:
            fields.client_address = multiline_address

        logger.debug(
            f"Extracted third page fields: client={fields.client}, "
            f"sample={fields.sample_name}, model={fields.model_spec}"
        )

        return fields

    def _extract_multiline_field_value(
        self,
        text: str,
        label_pattern: str,
        stop_label_patterns: list[str],
    ) -> str:
        """Extract multiline field value from line-oriented third-page text."""
        lines = [line.strip() for line in (text or "").split("\n")]
        label_re = re.compile(label_pattern)
        stop_res = [re.compile(pattern) for pattern in stop_label_patterns]

        for idx, line in enumerate(lines):
            if not line or not label_re.search(line):
                continue

            parts: list[str] = []
            for next_idx in range(idx + 1, len(lines)):
                current = (lines[next_idx] or "").strip()
                if not current:
                    continue
                if any(stop_re.search(current) for stop_re in stop_res):
                    break
                parts.append(current)

            if parts:
                return "".join(parts).strip()

        return ""

    def _extract_standard_exclusion_ranges(
        self,
        pdf_doc: PDFDocument,
    ) -> list[tuple[int, int]]:
        """Extract standard-content exclusion sequence ranges from report text.

        PRD defines this in page-4 "型号规格或其他说明" section, usually with
        expressions like "序号 1～序号 118 ... 标准的内容".
        """
        if not pdf_doc.pages:
            return []

        # Prefer page 4 text if present; fallback to full document search.
        candidate_texts: list[str] = []
        if len(pdf_doc.pages) >= 4:
            candidate_texts.append(pdf_doc.pages[3].raw_text)
        candidate_texts.extend(page.raw_text for page in pdf_doc.pages)

        ranges: list[tuple[int, int]] = []
        pattern_range = re.compile(r"序号\s*(\d+)\s*[~～\-至到]+\s*序号\s*(\d+)")
        pattern_single = re.compile(r"序号\s*(\d+)")

        for text in candidate_texts:
            if "标准的内容" not in text:
                continue

            for m in pattern_range.finditer(text):
                start = int(m.group(1))
                end = int(m.group(2))
                if start > end:
                    start, end = end, start
                ranges.append((start, end))

            if not ranges:
                singles = [int(m.group(1)) for m in pattern_single.finditer(text)]
                if singles:
                    for num in singles:
                        ranges.append((num, num))

            if ranges:
                break

        return ranges

    def _parse_standard_ranges(self, text: str) -> list[tuple[int, int]]:
        """Parse standard exclusion ranges from text.

        Args:
            text: Text containing ranges like "2.1.1-2.1.5"

        Returns:
            List of (start, end) tuples
        """
        ranges: list[tuple[int, int]] = []

        for match in STANDARD_RANGE_PATTERN.finditer(text):
            try:
                start_str = match.group(1)
                end_str = match.group(2)

                # Use the last number part for range
                start_parts = start_str.split(".")
                end_parts = end_str.split(".")

                if len(start_parts) >= 2 and len(end_parts) >= 2:
                    start = int(start_parts[-1])
                    end = int(end_parts[-1])
                    ranges.append((start, end))
            except (ValueError, IndexError):
                pass

        return ranges

    def _extract_inspection_table(
        self, pdf_doc: PDFDocument
    ) -> InspectionTable | None:
        """Extract the main inspection table.

        Args:
            pdf_doc: Parsed PDF document

        Returns:
            InspectionTable or None
        """
        # Find pages with inspection tables
        table_pages: list[tuple[int, TableData]] = []

        for page in pdf_doc.pages:
            for table in page.tables:
                if self._is_inspection_table(table):
                    table_pages.append((page.page_number, table))

        if not table_pages:
            logger.warning("No inspection table found in document")
            return None

        # Merge tables from multiple pages
        table = InspectionTable()
        table.page_start = table_pages[0][0]
        table.page_end = table_pages[-1][0]

        # Set headers from first table
        first_table = table_pages[0][1]
        table.headers = first_table.headers or INSPECTION_HEADERS

        # Extract items from all tables
        self.state = ExtractionState()

        for page_num, table_data in table_pages:
            items = self._extract_items_from_table(page_num, table_data)
            table.items.extend(items)

        logger.debug(
            f"Extracted inspection table with {len(table.items)} items "
            f"from pages {table.page_start}-{table.page_end}"
        )

        return table

    def _is_inspection_table(self, table: TableData) -> bool:
        """Check if a table is the inspection table.

        Args:
            table: Table to check

        Returns:
            True if table appears to be inspection table
        """
        def _compact(text: str) -> str:
            return re.sub(r"\s+", "", text or "").lower()

        # Check headers
        if table.headers:
            header_text = _compact("".join(table.headers))
            required_keywords = ["序号", "检验项目", "检验结果", "单项结论"]
            return all(keyword in header_text for keyword in required_keywords)

        # Check first row
        if table.rows and table.rows[0]:
            first_row_text = _compact("".join(cell.text for cell in table.rows[0]))
            required_keywords = ["序号", "检验项目"]
            return all(keyword in first_row_text for keyword in required_keywords)

        return False

    def _extract_items_from_table(
        self, page_num: int, table: TableData
    ) -> list[InspectionItem]:
        """Extract inspection items from a table.

        Args:
            page_num: Page number
            table: Table data

        Returns:
            List of InspectionItem objects
        """
        items: list[InspectionItem] = []
        row_values, row_provenance, row_has_merge = self._prepare_rows_with_merge_semantics(table)

        for row_idx, cells in enumerate(row_values):
            if not cells:
                continue

            # Skip explicit header row when table already has separate headers.
            if row_idx == 0 and table.headers:
                continue

            # Skip fully empty rows produced by extraction noise.
            if not any((cell or "").strip() for cell in cells):
                continue

            sequence = (cells[0] if cells else "") or ""
            sequence = sequence.strip()
            is_continued = sequence.startswith("续")
            clean_sequence = sequence.replace("续", "").strip()

            item = InspectionItem(
                sequence_number=sequence,
                inspection_project=cells[1] if len(cells) > 1 else "",
                standard_clause=cells[2] if len(cells) > 2 else "",
                standard_requirement=cells[3] if len(cells) > 3 else "",
                test_result=cells[4] if len(cells) > 4 else "",
                item_conclusion=cells[5] if len(cells) > 5 else "",
                remark=cells[6] if len(cells) > 6 else "",
                is_continued=is_continued,
                is_merged=bool(row_has_merge.get(row_idx, False)),
                source_page=page_num,
                row_index_in_page=row_idx,
                field_provenance=self._build_field_provenance(
                    row_provenance.get(row_idx, {}),
                ),
            )

            if item.sequence_number:
                self.state.current_sequence = clean_sequence
                if item.is_merged and item.inspection_project:
                    self.state.merged_cell_value = item.inspection_project

            items.append(item)

        return items

    def _has_merged_cells(self, row: list) -> bool:
        """Check if row has merged cells.

        Args:
            row: Row of cell data

        Returns:
            True if any cell is merged
        """
        from app.models.common_models import CellData

        for cell in row:
            if isinstance(cell, CellData):
                if cell.is_merged():
                    return True
                source = str(getattr(cell, "source", "") or "").lower()
                if source in {"inferred", "merge_inferred"}:
                    return True
        return False

    def _prepare_rows_with_merge_semantics(
        self,
        table: TableData,
    ) -> tuple[list[list[str]], dict[int, dict[int, str]], dict[int, bool]]:
        """Build row texts with merged-cell propagation and provenance."""
        row_count = len(table.rows)
        col_count = max((len(row) for row in table.rows), default=0)

        values: list[list[str]] = [["" for _ in range(col_count)] for _ in range(row_count)]
        provenance: dict[int, dict[int, str]] = {idx: {} for idx in range(row_count)}
        merged_rows: dict[int, bool] = {}

        for row_idx, row in enumerate(table.rows):
            for col_idx in range(col_count):
                cell = row[col_idx] if col_idx < len(row) else None
                if not isinstance(cell, CellData):
                    continue
                text = (cell.text or "").strip()
                values[row_idx][col_idx] = text
                provenance[row_idx][col_idx] = "native"
                if cell.is_merged():
                    merged_rows[row_idx] = True

        # Native row-span propagation: anchor non-empty value fills merged block.
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row):
                if not isinstance(cell, CellData):
                    continue
                if cell.row_span <= 1:
                    continue
                anchor = (cell.text or "").strip()
                if not anchor:
                    # C08 rule: empty anchor means merged block remains empty.
                    continue
                for offset in range(1, cell.row_span):
                    target_row = row_idx + offset
                    if target_row >= row_count:
                        break
                    if values[target_row][col_idx]:
                        continue
                    values[target_row][col_idx] = anchor
                    provenance[target_row][col_idx] = "merge_inferred"
                    merged_rows[target_row] = True

        # Canonical inferred fill-down acts as backup when native span is absent.
        canonical = self.table_normalizer.normalize(table)
        for cell in canonical.cells:
            if cell.source != "inferred":
                continue
            row_idx = cell.row
            col_idx = cell.col
            if row_idx >= row_count or col_idx >= col_count:
                continue
            if values[row_idx][col_idx]:
                continue
            if not (cell.text or "").strip():
                continue
            values[row_idx][col_idx] = cell.text.strip()
            provenance[row_idx][col_idx] = "inferred"
            merged_rows[row_idx] = True

        return values, provenance, merged_rows

    def _build_field_provenance(self, row_provenance: dict[int, str]) -> dict[str, str]:
        field_map = {
            0: "sequence_number",
            1: "inspection_project",
            2: "standard_clause",
            3: "standard_requirement",
            4: "test_result",
            5: "item_conclusion",
            6: "remark",
        }
        result: dict[str, str] = {}
        for col_idx, field_name in field_map.items():
            source = row_provenance.get(col_idx)
            if source:
                result[field_name] = source
        return result


def extract_report(file_path: str | Path) -> ReportDocument:
    """Convenience function to extract report document.

    Args:
        file_path: Path to report PDF file

    Returns:
        ReportDocument with extracted content
    """
    extractor = ReportExtractor()
    return extractor.extract_from_file(file_path)


def extract_inspection_items_from_pdf(pdf_doc: PDFDocument) -> list[InspectionItem]:
    """Extract inspection items from an already parsed PDF.

    Args:
        pdf_doc: Parsed PDF document

    Returns:
        List of InspectionItem objects
    """
    extractor = ReportExtractor()
    report_doc = extractor.extract_from_pdf_doc(pdf_doc)
    return report_doc.inspection_table.items if report_doc.inspection_table else []
