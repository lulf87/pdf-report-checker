"""
PTR (Product Technical Requirements) Clause Extractor.

Extracts Chapter 2 clauses with hierarchy parsing, sub-item recognition,
and table reference detection.
"""

import logging
import re
from pathlib import Path
from typing import Final

from app.models.common_models import PDFDocument
from app.models.ptr_models import (
    PTRClause,
    PTRClauseNumber,
    PTRDocument,
    PTRSubItem,
    PTRTable,
    PTRTableReference,
)

logger = logging.getLogger(__name__)

# Regex patterns for clause detection
# Matches: "2." "2.1" "2.1.1" etc.
CLAUSE_NUMBER_PATTERN: Final = re.compile(
    r"^(2?(?:\.\d+)*)\s+(.+)$",
    re.MULTILINE,
)

# Matches sub-items: "a)" "b)" "c)" or "a." "b." "c." or "——"
SUB_ITEM_PATTERN_ALPHA: Final = re.compile(
    r"^([a-z])[\.)]\s*(.+)$",
    re.MULTILINE,
)

SUB_ITEM_PATTERN_DASH: Final = re.compile(
    r"^(——+|—+)\s*(.+)$",
    re.MULTILINE,
)

# Matches table references: "见表1" "见表 1" "见表1-2" "见表X"
TABLE_REF_PATTERN: Final = re.compile(
    r"(?:见表|表)(\d+)(?:-\d+)?",
    re.MULTILINE,
)

# Chapter 2 marker (flexible chapter naming)
# Note: Python re doesn't support \p{Han}, using unicode range instead
CHAPTER2_MARKER: Final = re.compile(
    r"^2\s*[\u4e00-\u9fff]+",  # "2" followed by Chinese characters
    re.MULTILINE,
)


class PTRExtractor:
    """Extracts clauses and structure from PTR documents."""

    def __init__(self, strict: bool = False):
        """Initialize PTR extractor.

        Args:
            strict: If True, use strict parsing rules
        """
        self.strict = strict

    def extract(self, pdf_doc: PDFDocument) -> PTRDocument:
        """Extract PTR structure from PDF document.

        Args:
            pdf_doc: Parsed PDF document

        Returns:
            PTRDocument with all clauses and tables
        """
        ptr_doc = PTRDocument()

        # Find Chapter 2 boundaries
        chapter2_pages = self._find_chapter2_pages(pdf_doc)
        if not chapter2_pages:
            logger.warning("Chapter 2 not found in document")
            return ptr_doc

        ptr_doc.chapter2_start = min(chapter2_pages)
        ptr_doc.chapter2_end = max(chapter2_pages)

        # Extract clauses from Chapter 2 pages
        for page_num in range(ptr_doc.chapter2_start, ptr_doc.chapter2_end + 1):
            page = pdf_doc.get_page(page_num)
            if page:
                clauses = self._extract_clauses_from_page(page)
                ptr_doc.clauses.extend(clauses)

        # Scanned PTR OCR may repeat chapter headings across pages.
        ptr_doc.clauses = self._deduplicate_clauses(ptr_doc.clauses)

        # Extract tables from all pages
        for page in pdf_doc.pages:
            for table_data in page.tables:
                ptr_table = self._convert_to_ptr_table(table_data)
                if ptr_table:
                    ptr_doc.tables.append(ptr_table)

        # Link table references to actual tables
        self._link_table_references(ptr_doc)

        logger.info(
            f"Extracted {len(ptr_doc.clauses)} clauses "
            f"and {len(ptr_doc.tables)} tables from PTR"
        )

        return ptr_doc

    def _deduplicate_clauses(self, clauses: list[PTRClause]) -> list[PTRClause]:
        """Deduplicate clauses by number, preferring richer text content.

        OCR on scanned documents may emit repeated chapter/section headings.
        For a repeated clause number, keep the item with longer normalized text.
        """
        if not clauses:
            return clauses

        best_by_number: dict[str, PTRClause] = {}
        order: list[str] = []

        def _score(clause: PTRClause) -> int:
            text = re.sub(r"\s+", "", clause.text_content or "")
            return len(text)

        for clause in clauses:
            key = str(clause.number)
            if key not in best_by_number:
                best_by_number[key] = clause
                order.append(key)
                continue
            if _score(clause) > _score(best_by_number[key]):
                best_by_number[key] = clause

        return [best_by_number[key] for key in order]

    def _find_chapter2_pages(self, pdf_doc: PDFDocument) -> list[int]:
        """Find pages containing Chapter 2.

        Args:
            pdf_doc: Parsed PDF document

        Returns:
            List of page numbers containing Chapter 2
        """
        chapter2_pages = []

        for page in pdf_doc.pages:
            # Look for "2." pattern at the start of a line
            # This is the main chapter marker
            lines = page.raw_text.split("\n")
            for line in lines[:10]:  # Check first 10 lines only
                line = line.strip()
                if re.match(r"^2\s*[\.、\s]", line) or re.match(
                    r"^2\s*[\u4e00-\u9fff]+", line
                ):
                    chapter2_pages.append(page.page_number)
                    break

        return chapter2_pages

    def _extract_clauses_from_page(
        self, page
    ) -> list[PTRClause]:  # page: PDFPage
        """Extract clauses from a single page.

        Args:
            page: PDFPage to extract from

        Returns:
            List of PTRClause objects
        """
        clauses: list[PTRClause] = []
        lines = page.raw_text.split("\n")

        current_clause: PTRClause | None = None
        buffer: list[str] = []

        for line_num, line in enumerate(lines):
            line = line.rstrip()
            if not line:
                continue
            # Ignore page counters like "2/8" that OCR may put into text stream.
            if re.match(r"^\d+\s*/\s*\d+$", line.strip()):
                continue

            # Check if this line starts a new clause
            # OCR text often collapses delimiter/space, e.g.:
            # "2．性能指标", "2.1.1.1.导管外观", "2.3.4酸碱度"
            clause_match = re.match(
                r"^(\d+(?:\.\d+)*)(?:[\.．、。]?\s*)(.+)$",
                line,
            )

            if clause_match:
                # Save previous clause
                if current_clause:
                    current_clause.text_content = "\n".join(buffer).strip()
                    clauses.append(current_clause)

                # Start new clause
                number_str = clause_match.group(1)
                number = PTRClauseNumber.from_string(number_str)

                if number and number.parts[0] == 2:  # Must be Chapter 2
                    content = clause_match.group(2)
                    current_clause = PTRClause(
                        number=number,
                        full_text=line,
                        text_content=content,
                        level=number.level,
                        parent_number=number.parent,
                        position=(page.page_number, line_num),
                        raw_text=line,
                    )
                    buffer = [content]

                    # Check for table references in the first line
                    self._extract_table_references(current_clause, line)
                else:
                    current_clause = None
                    buffer = []
            elif current_clause:
                # Continuation of current clause
                buffer.append(line)
                current_clause.raw_text += "\n" + line

                # Check for table references in continuation
                self._extract_table_references(current_clause, line)

                # Check for sub-items
                self._extract_sub_items(current_clause, line)

        # Don't forget the last clause
        if current_clause:
            current_clause.text_content = "\n".join(buffer).strip()
            clauses.append(current_clause)

        return clauses

    def _extract_table_references(self, clause: PTRClause, text: str) -> None:
        """Extract table references from clause text.

        Args:
            clause: Clause to update
            text: Text to search for references
        """
        matches = TABLE_REF_PATTERN.findall(text)
        for match in matches:
            try:
                table_num = int(match)
                ref = PTRTableReference(
                    table_number=table_num,
                    context=text,
                    position=clause.text_content.find(text),
                )
                clause.table_references.append(ref)
            except (ValueError, IndexError):
                pass

    def _extract_sub_items(self, clause: PTRClause, text: str) -> None:
        """Extract sub-items from clause text.

        Args:
            clause: Clause to update
            text: Text to search for sub-items
        """
        # Try alpha pattern first: a) b) c)
        match = SUB_ITEM_PATTERN_ALPHA.match(text.strip())
        if match:
            marker = match.group(1) + ")"
            item_text = match.group(2)
            sub_item = PTRSubItem(
                marker=marker,
                text=item_text,
            )
            clause.sub_items.append(sub_item)
            return

        # Try dash pattern: —— or —
        match = SUB_ITEM_PATTERN_DASH.match(text.strip())
        if match:
            marker = match.group(1)
            item_text = match.group(2)
            sub_item = PTRSubItem(
                marker=marker,
                text=item_text,
            )
            clause.sub_items.append(sub_item)

    def _convert_to_ptr_table(self, table_data) -> PTRTable | None:
        """Convert common TableData to PTRTable.

        Args:
            table_data: TableData from PDF parser

        Returns:
            PTRTable or None
        """
        if table_data.is_empty():
            return None

        # Extract table number from caption or data
        table_number = table_data.table_number

        # Get headers
        headers = table_data.headers.copy()

        # Extract rows as text
        rows: list[list[str]] = []
        for row in table_data.rows:
            row_text = [cell.text for cell in row]
            rows.append(row_text)

        return PTRTable(
            table_number=table_number,
            caption=table_data.caption,
            headers=headers,
            rows=rows,
            page=table_data.page,
            position=(
                (table_data.bbox.x0, table_data.bbox.y0)
                if table_data.bbox
                else None
            ),
        )

    def _link_table_references(self, ptr_doc: PTRDocument) -> None:
        """Link table references to actual tables.

        Args:
            ptr_doc: PTRDocument to update
        """
        # This is for future enhancement - validate that referenced
        # tables actually exist in the document
        referenced = set(ptr_doc.get_all_referenced_table_numbers())
        available = {t.table_number for t in ptr_doc.tables if t.table_number}

        missing = referenced - available
        if missing:
            logger.warning(
                f"Referenced tables not found in document: {sorted(missing)}"
            )


def extract_ptr(pdf_doc: PDFDocument) -> PTRDocument:
    """Convenience function to extract PTR structure.

    Args:
        pdf_doc: Parsed PDF document

    Returns:
        PTRDocument with extracted clauses and tables
    """
    extractor = PTRExtractor()
    return extractor.extract(pdf_doc)
