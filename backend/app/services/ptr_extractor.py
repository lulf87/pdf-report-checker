"""
PTR (Product Technical Requirements) Clause Extractor.

Extracts Chapter 2 clauses with hierarchy parsing, sub-item recognition,
and table reference detection.
"""

import asyncio
import logging
import re
import tempfile
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Final

import fitz

from app.config import settings
from app.models.common_models import PDFDocument, TableData, CellData
from app.models.ptr_models import (
    PTRClause,
    PTRClauseNumber,
    PTRDocument,
    PTRSubItem,
    PTRTable,
    PTRTableReference,
)
from app.models.table_models import CanonicalTable
from app.services.llm_vision_service import create_vlm_service
from app.services.table_normalizer import TableNormalizer

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
    r"(?:见\s*表|表)\s*(\d+)(?:\s*[-－—]\s*\d+)?",
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

    def __init__(self, strict: bool = False, enable_table_vlm: bool | None = None):
        """Initialize PTR extractor.

        Args:
            strict: If True, use strict parsing rules
            enable_table_vlm: Whether to enable VLM enhancement for complex PTR tables
        """
        self.strict = strict
        if enable_table_vlm is None:
            self.enable_table_vlm = bool(getattr(settings, "ptr_table_vlm_enabled", False))
        else:
            self.enable_table_vlm = bool(enable_table_vlm)
        self.table_normalizer = TableNormalizer()

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

        # Extract tables from all pages and merge continuation fragments.
        raw_tables: list[PTRTable] = []
        for page in pdf_doc.pages:
            for table_data in page.tables:
                ptr_table = self._convert_to_ptr_table(table_data)
                if ptr_table:
                    raw_tables.append(ptr_table)
        ptr_doc.tables = self._merge_continuation_tables(raw_tables)

        # Link table references to actual tables
        self._link_table_references(ptr_doc)

        if self.enable_table_vlm:
            self._enhance_parameter_tables_with_vlm(ptr_doc, pdf_doc.file_path)

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
            lines = page.raw_text.split("\n")
            found = False
            for line in lines[:12]:  # Prioritize headings near top
                line = line.strip()
                if re.match(r"^2\s*[\.、\s]", line) or re.match(
                    r"^2\s*[\u4e00-\u9fff]+", line
                ):
                    chapter2_pages.append(page.page_number)
                    found = True
                    break
            if found:
                continue

            # Fallback: scanned/OCR PTR may place 2.x clauses deep in page body.
            # Accept page when at least one explicit chapter-2 clause marker appears.
            for line in lines:
                text = line.strip()
                if re.match(r"^2\.\d+(?:\.\d+)*(?:[\.．、]?\s*[\u4e00-\u9fff])", text):
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
        existing = {ref.table_number for ref in clause.table_references}
        for match in matches:
            try:
                table_num = int(match)
                if table_num in existing:
                    continue
                ref = PTRTableReference(
                    table_number=table_num,
                    context=text,
                    position=clause.text_content.find(text),
                )
                clause.table_references.append(ref)
                existing.add(table_num)
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

        canonical = self.table_normalizer.normalize(table_data)
        legacy_headers = self.table_normalizer.to_legacy_headers(canonical)
        legacy_rows = self.table_normalizer.to_legacy_rows(canonical)
        structure_confidence = canonical.diagnostics.structure_confidence
        parameter_records = [
            {
                "parameter_name": record.parameter_name,
                "dimensions": record.dimensions,
                "values": record.values,
                "source_rows": record.source_rows,
            }
            for record in self.table_normalizer.to_parameter_records(canonical)
        ]

        if not legacy_rows and table_data.rows:
            logger.info(
                "PTR table fallback to legacy conversion: page=%s table=%s conf=%.2f",
                table_data.page,
                table_data.table_number,
                structure_confidence,
            )
            ptr_table = self._convert_to_ptr_table_legacy(table_data)
            ptr_table.structure_confidence = structure_confidence
            ptr_table.metadata.update(
                {
                    "normalizer": "hybrid_fallback",
                    "canonical_diagnostics": asdict(canonical.diagnostics),
                    "column_roles": [path.role for path in canonical.column_paths],
                    "needs_manual_review": bool(canonical.metadata.get("needs_manual_review", False)),
                    "canonical_available": True,
                    "canonical_low_confidence": bool(structure_confidence < 0.7),
                    "canonical_disabled_reason": "legacy_headers_empty",
                    "parameter_records": parameter_records,
                    "canonical_snapshot": self._build_canonical_snapshot(
                        canonical=canonical,
                        table_data=table_data,
                        headers=legacy_headers,
                        rows=legacy_rows,
                    ),
                }
            )
            return ptr_table

        return self._build_ptr_table_from_canonical(
            table_data=table_data,
            canonical=canonical,
            legacy_headers=legacy_headers,
            legacy_rows=legacy_rows,
            structure_confidence=structure_confidence,
            parameter_records=parameter_records,
            low_confidence=bool(structure_confidence < 0.7),
        )

    def _convert_to_ptr_table_legacy(self, table_data) -> PTRTable:
        """Legacy conversion fallback for low-confidence structure reconstruction."""
        headers = table_data.headers.copy()
        rows: list[list[str]] = []
        for row in table_data.rows:
            rows.append([cell.text for cell in row])

        return PTRTable(
            table_number=table_data.table_number,
            caption=table_data.caption,
            headers=headers,
            rows=rows,
            page=table_data.page,
            page_end=table_data.page,
            position=((table_data.bbox.x0, table_data.bbox.y0) if table_data.bbox else None),
            bbox=(
                (
                    float(table_data.bbox.x0),
                    float(table_data.bbox.y0),
                    float(table_data.bbox.x1),
                    float(table_data.bbox.y1),
                )
                if table_data.bbox
                else None
            ),
            structure_confidence=0.0,
            metadata={
                "normalizer": "legacy_fallback",
                "needs_manual_review": True,
            },
        )

    def _build_ptr_table_from_canonical(
        self,
        table_data: TableData,
        canonical: CanonicalTable,
        legacy_headers: list[str],
        legacy_rows: list[list[str]],
        structure_confidence: float,
        parameter_records: list[dict[str, object]],
        low_confidence: bool,
    ) -> PTRTable:
        ptr_table = PTRTable(
            table_number=table_data.table_number,
            caption=table_data.caption,
            headers=legacy_headers,
            rows=legacy_rows,
            page=table_data.page,
            page_end=table_data.page,
            position=((table_data.bbox.x0, table_data.bbox.y0) if table_data.bbox else None),
            bbox=(
                (
                    float(table_data.bbox.x0),
                    float(table_data.bbox.y0),
                    float(table_data.bbox.x1),
                    float(table_data.bbox.y1),
                )
                if table_data.bbox
                else None
            ),
            header_rows=self._build_header_rows(canonical),
            column_paths=[path.labels[:] for path in canonical.column_paths],
            structure_confidence=structure_confidence,
            metadata={
                "canonical_diagnostics": asdict(canonical.diagnostics),
                "column_roles": [path.role for path in canonical.column_paths],
                "normalizer": "canonical_v1",
                "needs_manual_review": bool(canonical.metadata.get("needs_manual_review", False)),
                "canonical_available": True,
                "canonical_low_confidence": low_confidence,
                "canonical_disabled_reason": None,
                "parameter_records": parameter_records,
                "canonical_snapshot": self._build_canonical_snapshot(
                    canonical=canonical,
                    table_data=table_data,
                    headers=legacy_headers,
                    rows=legacy_rows,
                ),
                "source_engine": table_data.source_engine,
            },
        )
        return ptr_table

    def _build_canonical_snapshot(
        self,
        canonical: CanonicalTable,
        table_data: TableData,
        headers: list[str],
        rows: list[list[str]],
    ) -> dict[str, object]:
        return {
            "table_number": table_data.table_number,
            "caption": table_data.caption,
            "headers": headers,
            "rows": rows,
            "header_rows": self._build_header_rows(canonical),
            "column_paths": [path.labels[:] for path in canonical.column_paths],
            "column_roles": [path.role for path in canonical.column_paths],
            "n_cols": canonical.n_cols,
            "n_rows": canonical.n_rows,
            "merged_from_pages": table_data.page,
            "source_engine": table_data.source_engine,
            "extraction_meta": dict(table_data.extraction_meta or {}),
            "page": table_data.page,
            "position": table_data.bbox and {
                "x0": table_data.bbox.x0,
                "y0": table_data.bbox.y0,
                "x1": table_data.bbox.x1,
                "y1": table_data.bbox.y1,
            },
        }

    def _build_header_rows(self, canonical) -> list[list[str]]:
        header_rows: list[list[str]] = []
        for row_idx in canonical.header_rows:
            row_values: list[str] = []
            for col_idx in range(canonical.n_cols):
                cell = canonical.get_cell(row_idx, col_idx)
                row_values.append(cell.text if cell else "")
            header_rows.append(row_values)
        return header_rows

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

    def _merge_continuation_tables(self, tables: list[PTRTable]) -> list[PTRTable]:
        """Merge cross-page continuation tables that lose table number/header context."""
        if not tables:
            return []

        def _sort_key(table: PTRTable) -> tuple[int, float]:
            y0 = float(table.position[1]) if table.position else 0.0
            return (table.page, y0)

        ordered = sorted(tables, key=_sort_key)
        merged: list[PTRTable] = []

        for source in ordered:
            table = self._normalize_table_cells(source)
            if not merged:
                merged.append(table)
                continue

            prev = merged[-1]
            prev_end_page = int(prev.page_end or prev.page)
            is_continuation, reason, evidence = self._assess_table_continuation(prev, table, prev_end_page)
            if is_continuation:
                self._merge_table_into(prev, table)
                if prev.metadata is None:
                    prev.metadata = {}
                prev.metadata.setdefault("continuation_merge_reasons", []).append(
                    {"page": table.page, "reason": reason}
                )
                prev.metadata["continuation_merge_reason"] = reason
                prev.metadata["continuation_reason"] = reason
                prev.metadata["continuation_evidence"] = evidence
                prev.metadata.setdefault("continuation_decisions", []).append(
                    {"page": table.page, "merged": True, "reason": reason, "evidence": evidence}
                )
                prev.page_end = max(prev_end_page, int(table.page_end or table.page))
                continue
            table.metadata = dict(table.metadata or {})
            table.metadata["continuation_reject_reason"] = reason
            table.metadata["continuation_reason"] = reason
            table.metadata["continuation_evidence"] = evidence

            merged.append(table)

        for table in merged:
            self._repair_parameter_table_rows(table)
            self._rebuild_merged_ptr_table_metadata(table)
            table.page_end = int(table.page_end or table.page)

        return merged

    def _normalize_table_cells(self, table: PTRTable) -> PTRTable:
        """Normalize table cells to a stable rectangular shape."""
        expected_cols = max(
            len(table.headers),
            max((len(row) for row in table.rows), default=0),
        )
        if expected_cols <= 0:
            return table

        normalized_headers = [str(cell or "").strip() for cell in table.headers]
        if len(normalized_headers) < expected_cols:
            normalized_headers.extend([""] * (expected_cols - len(normalized_headers)))
        elif len(normalized_headers) > expected_cols:
            normalized_headers = normalized_headers[:expected_cols]

        normalized_rows: list[list[str]] = []
        for row in table.rows:
            row_values = [str(cell or "").strip() for cell in row]
            if len(row_values) < expected_cols:
                row_values.extend([""] * (expected_cols - len(row_values)))
            elif len(row_values) > expected_cols:
                row_values = row_values[:expected_cols]
            normalized_rows.append(row_values)

        table.headers = normalized_headers
        table.rows = normalized_rows
        return table

    def _is_table_continuation(
        self,
        previous: PTRTable,
        current: PTRTable,
        previous_end_page: int,
    ) -> bool:
        """Whether current table is a continuation fragment of previous table."""
        return self._assess_table_continuation(previous, current, previous_end_page)[0]

    def _assess_table_continuation(
        self,
        previous: PTRTable,
        current: PTRTable,
        previous_end_page: int,
    ) -> tuple[bool, str, dict[str, object]]:
        """Assess continuation relationship and provide a short reason."""
        page_gap = current.page - previous_end_page
        evidence: dict[str, object] = {
            "page_gap": page_gap,
            "previous_page": previous.page,
            "current_page": current.page,
        }
        if page_gap < 0 or page_gap > 1:
            return False, "page_gap_invalid", evidence

        prev_cols = max(len(previous.headers), max((len(r) for r in previous.rows), default=0))
        curr_cols = max(len(current.headers), max((len(r) for r in current.rows), default=0))
        evidence["previous_column_count"] = prev_cols
        evidence["current_column_count"] = curr_cols
        if prev_cols == 0 or curr_cols == 0:
            return False, "empty_columns", evidence
        if abs(prev_cols - curr_cols) > 1:
            return False, "column_count_mismatch", evidence

        if previous.table_number and current.table_number and previous.table_number != current.table_number:
            return False, "table_number_conflict", evidence
        if previous.table_number and current.table_number == previous.table_number:
            return True, "same_table_number", evidence

        if current.table_number is not None:
            return False, "current_has_table_number", evidence

        structure_similarity = self._table_structure_similarity(previous, current)
        header_overlap = self._table_header_text_overlap_ratio(previous, current)
        path_overlap = self._table_column_path_overlap_ratio(previous, current)
        overlap_signal = max(header_overlap, path_overlap)
        current_top = self._is_top_of_page(current)
        previous_bottom = self._is_bottom_of_page(previous)
        position_bridge = current_top and previous_bottom
        parameter_signal, parameter_reason = self._is_likely_parameter_continuation(
            previous=previous,
            current=current,
        )

        evidence.update(
            {
                "structure_similarity": round(structure_similarity, 4),
                "header_overlap": round(header_overlap, 4),
                "column_path_overlap": round(path_overlap, 4),
                "overlap_signal": round(overlap_signal, 4),
                "previous_bottom": previous_bottom,
                "current_top": current_top,
                "position_bridge": position_bridge,
                "parameter_continuation_signal": parameter_signal,
                "parameter_continuation_reason": parameter_reason,
            }
        )

        accept_high_structure = structure_similarity >= 0.88
        accept_high_structure_with_overlap = structure_similarity >= 0.78 and overlap_signal >= 0.55
        accept_top_bottom_overlap = position_bridge and overlap_signal >= 0.55 and structure_similarity >= 0.4
        accept_parameter_joint = (
            position_bridge and parameter_signal and overlap_signal >= 0.45 and structure_similarity >= 0.35
        )
        accept_top_bottom_path = position_bridge and path_overlap >= 0.7 and structure_similarity >= 0.35
        strong_evidence = any(
            (
                accept_high_structure,
                accept_high_structure_with_overlap,
                accept_top_bottom_overlap,
                accept_parameter_joint,
                accept_top_bottom_path,
            )
        )

        evidence.update(
            {
                "accept_high_structure": accept_high_structure,
                "accept_high_structure_with_overlap": accept_high_structure_with_overlap,
                "accept_top_bottom_overlap": accept_top_bottom_overlap,
                "accept_parameter_joint": accept_parameter_joint,
                "accept_top_bottom_path": accept_top_bottom_path,
                "strong_evidence": strong_evidence,
            }
        )

        missing_table_numbers = previous.table_number is None and current.table_number is None
        if missing_table_numbers:
            evidence["missing_table_numbers"] = True
            evidence["strong_missing_number_evidence"] = strong_evidence
            if not strong_evidence:
                return False, "missing_table_number_without_strong_evidence", evidence
        elif previous.table_number is None:
            return False, "previous_missing_table_number", evidence

        if accept_high_structure:
            return True, "high_structure_similarity", evidence
        if accept_high_structure_with_overlap:
            return True, "high_structure_with_overlap", evidence
        if accept_top_bottom_overlap:
            return True, "top_bottom_with_header_or_path_overlap", evidence
        if accept_parameter_joint:
            return True, "parameter_continuation_with_joint_evidence", evidence
        if accept_top_bottom_path:
            return True, "top_bottom_with_path_overlap", evidence

        if structure_similarity < 0.35 and overlap_signal < 0.35 and not position_bridge:
            return False, "rejected: low_similarity", evidence
        if overlap_signal < 0.3:
            return False, "rejected: no_header_path_overlap", evidence
        if parameter_signal and overlap_signal < 0.45:
            return False, "rejected: weak_parameter_signal", evidence
        if position_bridge and overlap_signal < 0.45:
            return False, "rejected: top_bottom_without_overlap", evidence
        if not position_bridge and structure_similarity < 0.78:
            return False, "rejected: insufficient_position_evidence", evidence
        return False, "rejected: insufficient_joint_evidence", evidence

    def _is_likely_parameter_continuation(self, previous: PTRTable, current: PTRTable) -> tuple[bool, str]:
        """Detect continuation fragments for parameter tables in loose form.

        This captures cases where continuation fragments lose first-column parameters
        or header rows, while still staying close to the previous page and table
        layout (same width, same page range proximity, same parameter-table
        context).
        """
        if not current.rows:
            return False, "missing_rows"

        if max(len(previous.headers), max((len(r) for r in previous.rows), default=0)) != max(
            len(current.headers), max((len(r) for r in current.rows), default=0)
        ):
            return False, "column_count_mismatch"

        if not self._looks_like_parameter_table(previous):
            return False, "previous_not_parameter_table"

        first_row = self._first_data_row(current.rows)
        if not first_row:
            return False, "missing_first_data_row"

        first_cell = (first_row[0] or "").strip()
        second_cell = (first_row[1] or "").strip() if len(first_row) > 1 else ""
        has_payload = any((value or "").strip() for value in first_row[2:])
        current_parameter_like = (
            self._looks_like_parameter_table(current)
            or bool(current.column_paths)
            or self._has_parameter_like_body(current)
        )
        if not current_parameter_like:
            return False, "current_not_parameter_like"

        if self._is_duplicate_header_row(first_row, previous.headers):
            return True, "repeated_header_row"
        if not first_cell and self._looks_like_model_cell(second_cell) and has_payload:
            return True, "blank_first_col_with_model_payload"
        if first_cell and self._looks_like_parameter_cell(first_cell) and has_payload:
            return True, "parameter_like_first_col_with_payload"
        if first_cell and self._looks_like_model_cell(first_cell) and has_payload:
            return True, "model_in_first_col_with_payload"
        return False, "weak_signal_only"

    def _table_header_text_overlap_ratio(self, previous: PTRTable, current: PTRTable) -> float:
        """Compute overlap ratio from visible header text only."""
        previous_tokens = {
            re.sub(r"\s+", "", str(header or ""))
            for header in previous.headers
            if re.sub(r"\s+", "", str(header or ""))
        }
        current_tokens = {
            re.sub(r"\s+", "", str(header or ""))
            for header in current.headers
            if re.sub(r"\s+", "", str(header or ""))
        }
        return self._overlap_ratio(previous_tokens, current_tokens)

    def _table_column_path_overlap_ratio(self, previous: PTRTable, current: PTRTable) -> float:
        """Compute overlap ratio from canonical column paths when present."""
        previous_tokens = {
            re.sub(r"\s+", "", "/".join(path))
            for path in previous.column_paths
            if isinstance(path, list) and re.sub(r"\s+", "", "/".join(path))
        }
        current_tokens = {
            re.sub(r"\s+", "", "/".join(path))
            for path in current.column_paths
            if isinstance(path, list) and re.sub(r"\s+", "", "/".join(path))
        }
        return self._overlap_ratio(previous_tokens, current_tokens)

    @staticmethod
    def _overlap_ratio(previous_tokens: set[str], current_tokens: set[str]) -> float:
        """Return normalized overlap ratio for two token sets."""
        if not previous_tokens or not current_tokens:
            return 0.0
        overlap = len(previous_tokens & current_tokens)
        return overlap / min(len(previous_tokens), len(current_tokens))

    @staticmethod
    def _first_data_row(rows: list[list[str]]) -> list[str]:
        """Return first row with any non-empty value."""
        for row in rows:
            if not row:
                continue
            if any((cell or "").strip() for cell in row):
                return row
        return []

    def _looks_like_parameter_cell(self, text: str) -> bool:
        """Heuristic for parameter-like first column values."""
        compact = re.sub(r"\s+", "", text or "")
        if not compact:
            return False
        if self._looks_like_model_cell(compact):
            return False
        keywords = [
            "参数",
            "指标",
            "脉冲",
            "频率",
            "间期",
            "电流",
            "电压",
            "电阻",
            "阻抗",
            "阈值",
            "幅值",
            "检验",
            "心室",
            "房室",
            "腔室",
        ]
        if any(keyword in compact for keyword in keywords):
            return True
        return False

    def _is_top_of_page(self, table: PTRTable) -> bool:
        """Whether a table starts near a page top in continuation scenarios."""
        if table.position is None:
            return False
        return float(table.position[1]) <= 150.0

    def _is_bottom_of_page(self, table: PTRTable) -> bool:
        """Whether a table ends near a page bottom in continuation scenarios."""
        if table.position is None:
            return False
        return float(table.position[1]) >= 450.0

    def _table_header_overlap_ratio(self, previous: PTRTable, current: PTRTable) -> float:
        """Compute header/path token overlap ratio between two tables."""
        prev_tokens = self._table_tokens(previous)
        curr_tokens = self._table_tokens(current)
        if not prev_tokens or not curr_tokens:
            return 0.0

        overlap = len(prev_tokens & curr_tokens)
        return overlap / min(len(prev_tokens), len(curr_tokens))

    def _table_tokens(self, table: PTRTable) -> set[str]:
        """Extract canonical-ish structural tokens from headers/paths."""
        tokens: set[str] = set()
        if table.column_paths:
            for path in table.column_paths:
                if isinstance(path, list):
                    compact = re.sub(r"\s+", "", "".join(path))
                else:
                    compact = re.sub(r"\s+", "", str(path))
                if compact:
                    tokens.add(compact)

        if not tokens:
            for header in table.headers:
                compact = re.sub(r"\s+", "", str(header or ""))
                if compact:
                    tokens.add(compact)

        if not tokens and table.rows:
            for value in table.rows[0]:
                compact = re.sub(r"\s+", "", str(value or ""))
                if compact:
                    tokens.add(compact)

        return tokens

    def _looks_like_new_table_start(self, table: PTRTable) -> bool:
        """Detect if table fragment likely starts a fresh table with explicit headers."""
        if table.table_number is not None:
            return True

        merged_header = " ".join(h for h in table.headers if h).strip()
        if not merged_header:
            return False

        header_keywords = ["参数", "参数名称", "型号", "标准设置", "允许误差", "数值", "单位"]
        hit_count = sum(1 for keyword in header_keywords if keyword in merged_header)
        if hit_count >= 2 and not self._has_parameter_like_body(table):
            return True

        first_header = (table.headers[0] or "").strip() if table.headers else ""
        if len(first_header) >= 25 and not any(k in first_header for k in header_keywords):
            return False
        return False

    def _has_parameter_like_body(self, table: PTRTable) -> bool:
        if not table.rows:
            return False
        sample_rows = table.rows[:3]
        for row in sample_rows:
            joined = "".join((cell or "").strip() for cell in row)
            if any(token in joined for token in ["脉冲", "频率", "灵敏度", "不应期", "间期", "阻抗"]):
                return True
        return False

    def _table_structure_similarity(self, previous: PTRTable, current: PTRTable) -> float:
        prev_sig = self._table_structure_signature(previous)
        curr_sig = self._table_structure_signature(current)
        if not prev_sig or not curr_sig:
            return 0.0

        if prev_sig == curr_sig:
            return 1.0

        prev_tokens = set(prev_sig.split("|"))
        curr_tokens = set(curr_sig.split("|"))
        if not prev_tokens or not curr_tokens:
            return 0.0
        overlap = len(prev_tokens & curr_tokens)
        union = len(prev_tokens | curr_tokens)
        return overlap / union if union else 0.0

    def _table_structure_signature(self, table: PTRTable) -> str:
        col_count = max(len(table.headers), max((len(r) for r in table.rows), default=0))
        header_paths = []
        if table.column_paths:
            for path in table.column_paths:
                compact = re.sub(r"\s+", "", "/".join(path))
                if compact:
                    header_paths.append(compact)
        if not header_paths:
            header_paths = [re.sub(r"\s+", "", h or "") for h in table.headers if (h or "").strip()]
        if not header_paths and table.rows:
            header_paths = [re.sub(r"\s+", "", value or "") for value in table.rows[0] if (value or "").strip()]

        key_fields = [f"cols:{col_count}", *header_paths[:8]]
        return "|".join(field for field in key_fields if field)

    def _looks_like_parameter_table(self, table: PTRTable) -> bool:
        merged_header = " ".join(h for h in table.headers if h)
        return "参数" in merged_header and (
            "标准设置" in merged_header or "允许误差" in merged_header or "常规数值" in merged_header
        )

    def _merge_table_into(self, base: PTRTable, fragment: PTRTable) -> None:
        """Append fragment rows into base table, skipping duplicated headers."""
        if base.table_number is None and fragment.table_number is not None:
            base.table_number = fragment.table_number

        base.page_end = max(int(base.page_end or base.page), int(fragment.page_end or fragment.page))

        if not base.headers and fragment.headers:
            base.headers = fragment.headers.copy()
        if not base.header_rows and fragment.header_rows:
            base.header_rows = [row[:] for row in fragment.header_rows]
        if not base.column_paths and fragment.column_paths:
            base.column_paths = [path[:] for path in fragment.column_paths]
        if (
            (base.structure_confidence is None or base.structure_confidence < 0.6)
            and fragment.structure_confidence is not None
        ):
            base.structure_confidence = fragment.structure_confidence
        if not base.metadata:
            base.metadata = {}
        merged_from_pages = base.metadata.setdefault("merged_from_pages", [])
        if isinstance(merged_from_pages, list) and fragment.page not in merged_from_pages:
            merged_from_pages.append(fragment.page)

        if base.bbox and fragment.bbox and fragment.page == base.page:
            base.bbox = (
                min(base.bbox[0], fragment.bbox[0]),
                min(base.bbox[1], fragment.bbox[1]),
                max(base.bbox[2], fragment.bbox[2]),
                max(base.bbox[3], fragment.bbox[3]),
            )
        elif not base.bbox and fragment.bbox:
            base.bbox = fragment.bbox

        rows_to_add = fragment.rows
        if rows_to_add and self._is_duplicate_header_row(rows_to_add[0], base.headers):
            rows_to_add = rows_to_add[1:]

        base.rows.extend(rows_to_add)
        base.metadata.setdefault("merged_row_counts", []).append(
            {"from_page": fragment.page, "rows_added": len(rows_to_add)}
        )

    def _is_duplicate_header_row(self, row: list[str], headers: list[str]) -> bool:
        if not row or not headers:
            return False
        row_text = re.sub(r"\s+", "", "|".join(str(v or "") for v in row))
        header_text = re.sub(r"\s+", "", "|".join(str(v or "") for v in headers))
        if not row_text or not header_text:
            return False
        return row_text == header_text

    def _rebuild_merged_ptr_table_metadata(self, table: PTRTable) -> None:
        """Rebuild canonical metadata for a merged PTRTable from merged legacy rows."""
        metadata = table.metadata or {}
        if not table.rows:
            return

        snapshot = metadata.get("canonical_snapshot") if isinstance(metadata, dict) else None

        # Keep continuation lineage even if snapshot structure changed.
        merged_from_pages = metadata.get("merged_from_pages")
        if isinstance(merged_from_pages, list):
            merged_from_pages_values = list(merged_from_pages)
        else:
            merged_from_pages_values = [table.page]
        if table.page not in merged_from_pages_values:
            merged_from_pages_values.append(table.page)
        if isinstance(snapshot, dict) and isinstance(snapshot.get("merged_from_pages"), list):
            for page_no in snapshot.get("merged_from_pages"):
                if isinstance(page_no, int) and page_no not in merged_from_pages_values:
                    merged_from_pages_values.append(page_no)
        elif isinstance(snapshot, dict) and isinstance(snapshot.get("page"), int):
            if snapshot.get("page") not in merged_from_pages_values:
                merged_from_pages_values.append(snapshot.get("page"))

        source_headers = [str(value or "") for value in table.headers]
        source_rows = [list(row) for row in table.rows]

        snapshot_headers = snapshot.get("headers") if isinstance(snapshot, dict) else table.headers
        snapshot_rows = snapshot.get("rows") if isinstance(snapshot, dict) else table.rows
        if not isinstance(snapshot_headers, list):
            snapshot_headers = source_headers
        if not isinstance(snapshot_rows, list):
            snapshot_rows = source_rows

        # If snapshot rows are stale (for example missing continuation rows),
        # prefer current merged rows.
        if len(snapshot_rows) < len(source_rows):
            snapshot_headers = source_headers
            snapshot_rows = source_rows

        if not snapshot_headers or not snapshot_rows:
            return

        source_engine = "pymupdf"
        extraction_meta = {}
        if isinstance(snapshot, dict):
            source_engine = str(snapshot.get("source_engine", source_engine))
            extraction_meta = snapshot.get("extraction_meta", {})
            if snapshot.get("table_number") is not None:
                try:
                    table.table_number = int(snapshot.get("table_number"))  # type: ignore[assignment]
                except (TypeError, ValueError):
                    table.table_number = table.table_number
            if "caption" in snapshot:
                table.caption = str(snapshot.get("caption") or "")
            if "caption" in snapshot and snapshot.get("caption") is not None:
                table.caption = str(snapshot.get("caption"))

        table_data = self._build_table_data_from_ptr_table_snapshot(
            table,
            rows=[list(row) for row in snapshot_rows],
            headers=[str(value or "") for value in snapshot_headers],
            source_engine=source_engine,
            extraction_meta=extraction_meta if isinstance(extraction_meta, dict) else {},
            page=int(snapshot.get("page", table.page)) if isinstance(snapshot, dict) and isinstance(snapshot.get("page"), int) else table.page,
            table_number=table.table_number,
        )
        canonical = self.table_normalizer.normalize(table_data)
        legacy_headers = self.table_normalizer.to_legacy_headers(canonical)
        legacy_rows = self.table_normalizer.to_legacy_rows(canonical)

        # Prefer reconstructed canonical headers/rows only when the rebuild does not
        # shrink the body. Continuation merges often start from an incomplete
        # snapshot (old base table only), and canonical normalization may mis-detect
        # the first body row as a header for value-heavy tables.
        use_rebuilt = bool(legacy_rows) and len(legacy_rows) == len(source_rows)
        fallback_headers = source_headers
        fallback_rows = source_rows
        if use_rebuilt:
            fallback_headers = legacy_headers
            fallback_rows = legacy_rows

        parameter_records = self._collect_parameter_records_from_canonical_rows(
            canonical_headers=fallback_headers,
            canonical_rows=fallback_rows,
        )

        table.headers = fallback_headers
        table.rows = fallback_rows
        table.header_rows = self._build_header_rows(canonical)
        table.column_paths = (
            [path.labels[:] for path in canonical.column_paths]
            if canonical.column_paths
            else [[header] if header else [] for header in table.headers]
        )
        table.structure_confidence = canonical.diagnostics.structure_confidence
        table.metadata = {
            **metadata,
            "canonical_diagnostics": asdict(canonical.diagnostics),
            "column_roles": [path.role for path in canonical.column_paths],
            "canonical_available": True,
            "canonical_low_confidence": canonical.diagnostics.structure_confidence < 0.7,
            "needs_manual_review": bool(canonical.metadata.get("needs_manual_review", False)),
            "parameter_records": parameter_records,
            "canonical_snapshot": self._build_canonical_snapshot(
                canonical=canonical,
                table_data=table_data,
                headers=table.headers,
                rows=table.rows,
            ),
            "merged_from_pages": merged_from_pages_values,
        }

    def _collect_parameter_records_from_canonical_rows(
        self,
        canonical_headers: list[str],
        canonical_rows: list[list[str]],
    ) -> list[dict[str, object]]:
        """Fallback parameter-record extraction for merged tables without reliable headers."""
        if not canonical_headers or not canonical_rows:
            return []

        roles: list[str] = []
        for index, header in enumerate(canonical_headers):
            if index == 0:
                roles.append("parameter")
                continue
            roles.append(self.table_normalizer.semantics.infer_column_role(header))

        parameter_col = 0
        for idx, role in enumerate(roles):
            if role == "parameter":
                parameter_col = idx
                break

        model_cols = [
            idx
            for idx, role in enumerate(roles)
            if role in {"model", "group"} and idx != parameter_col
        ]
        value_cols = [idx for idx, role in enumerate(roles) if role in {"value", "default", "tolerance", "remark"}]
        if not value_cols:
            value_cols = [idx for idx in range(len(roles)) if idx not in {parameter_col, *model_cols}]

        records: list[dict[str, object]] = []
        for row_idx, row in enumerate(canonical_rows):
            if not row:
                continue
            values = list(row) + ["" for _ in range(len(canonical_headers) - len(row))]
            parameter_name = str(values[parameter_col] if parameter_col < len(values) else "").strip()
            if not parameter_name:
                continue

            dimensions: dict[str, str] = {}
            for col_idx in model_cols:
                value = str(values[col_idx]).strip() if col_idx < len(values) else ""
                if not value:
                    continue
                dimensions[canonical_headers[col_idx] if canonical_headers[col_idx] else f"col_{col_idx}"] = value

            value_cells: dict[str, str] = {}
            for col_idx in value_cols:
                value = str(values[col_idx]).strip() if col_idx < len(values) else ""
                if not value:
                    continue
                key = canonical_headers[col_idx] if col_idx < len(canonical_headers) else f"col_{col_idx}"
                value_cells[key] = value

            records.append(
                {
                    "parameter_name": parameter_name,
                    "dimensions": dimensions,
                    "values": value_cells,
                    "source_rows": [row_idx],
                }
            )
        return records

    def _build_table_data_from_ptr_table_snapshot(
        self,
        table: PTRTable,
        rows: list[list[str]] | None = None,
        headers: list[str] | None = None,
        table_number: int | None = None,
        caption: str | None = None,
        page: int | None = None,
        source_engine: str | None = None,
        extraction_meta: dict[str, object] | None = None,
    ) -> TableData:
        """Reconstruct a TableData object from flattened PTR table values."""
        row_values = rows if rows is not None else table.rows
        header_values = headers if headers is not None else table.headers
        if not row_values:
            row_values = table.rows
        if not header_values:
            header_values = table.headers
        target_page = page if page is not None else table.page
        target_table_number = table.table_number if table_number is None else table_number
        target_caption = table.caption if caption is None else caption
        source = source_engine or (table.metadata.get("source_engine", "pymupdf") if isinstance(table.metadata, dict) else "pymupdf")
        extraction_payload = extraction_meta if extraction_meta is not None else (
            table.metadata.get("extraction_meta", {})
            if isinstance(table.metadata, dict)
            else {}
        )

        normalized_rows: list[list[CellData]] = []
        for row_idx, row in enumerate(row_values):
            cell_row: list[CellData] = []
            for col_idx, value in enumerate(row):
                cell_row.append(
                    CellData(
                        text=str(value or ""),
                        row=row_idx,
                        col=col_idx,
                        row_span=1,
                        col_span=1,
                    )
                )
            normalized_rows.append(cell_row)

        return TableData(
            rows=normalized_rows,
            headers=header_values[:],
            page=target_page,
            caption=target_caption,
            table_number=target_table_number,
            raw_rows=normalized_rows,
            source_engine=source,
            extraction_meta=extraction_payload,
        )

    def _repair_parameter_table_rows(self, table: PTRTable) -> None:
        """Repair row-shift artifacts caused by row-spans in complex parameter tables."""
        if not self._looks_like_parameter_table(table):
            return
        if not table.rows:
            return

        expected_cols = max(len(table.headers), max((len(r) for r in table.rows), default=0))
        if expected_cols < 4:
            return

        last_parameter = ""
        repaired_rows: list[list[str]] = []
        for row in table.rows:
            values = [str(cell or "").strip() for cell in row]
            if len(values) < expected_cols:
                values.extend([""] * (expected_cols - len(values)))
            elif len(values) > expected_cols:
                values = values[:expected_cols]

            if self._is_duplicate_header_row(values, table.headers):
                repaired_rows.append(values)
                continue

            first_cell = values[0]
            if first_cell:
                if self._looks_like_model_cell(first_cell) and last_parameter:
                    # Continuation row with lost parameter column: shift right.
                    values = [last_parameter] + values[: expected_cols - 1]
                else:
                    last_parameter = first_cell
            elif last_parameter and any(values[1:]):
                values[0] = last_parameter

            repaired_rows.append(values)

        table.rows = repaired_rows

    def _looks_like_model_cell(self, text: str) -> bool:
        compact = re.sub(r"\s+", "", text or "")
        if not compact:
            return False
        if "全部型号" in compact:
            return True
        if "Edora" in compact:
            return True
        if re.search(r"(SR|DR)(?:-T)?$", compact, re.IGNORECASE):
            return True
        return False

    def _enhance_parameter_tables_with_vlm(self, ptr_doc: PTRDocument, pdf_path: str) -> None:
        """Optionally enhance complex parameter tables via VLM image extraction."""
        if not pdf_path:
            return
        path = Path(pdf_path)
        if not path.exists():
            return

        candidates = [table for table in ptr_doc.tables if self._should_vlm_enhance_table(table)]
        if not candidates:
            return

        service = create_vlm_service(model_override=str(getattr(settings, "vlm_primary_model", "") or "").strip() or None)
        if service is None:
            logger.warning("PTR table VLM enhancement skipped: VLM not configured")
            return

        try:
            self._run_coroutine_blocking(
                self._enhance_parameter_tables_with_vlm_async(
                    service=service,
                    pdf_path=path,
                    candidates=candidates,
                )
            )
        except Exception as e:
            logger.warning(f"PTR table VLM enhancement failed: {e}")
        finally:
            try:
                self._run_coroutine_blocking(service.close())
            except Exception:
                pass

    async def _enhance_parameter_tables_with_vlm_async(
        self,
        service,
        pdf_path: Path,
        candidates: list[PTRTable],
    ) -> None:
        max_pages = max(1, int(getattr(settings, "ptr_table_vlm_max_pages", 4) or 4))

        with fitz.open(str(pdf_path)) as fitz_doc:
            for table in candidates:
                start_page = int(table.page or 1)
                end_page = int(table.page_end or table.page or 1)
                if end_page < start_page:
                    end_page = start_page
                if end_page - start_page + 1 > max_pages:
                    end_page = start_page + max_pages - 1

                merged_rows: list[list[str]] = []
                inferred_headers = [str(v or "").strip() for v in table.headers]
                confidence_values: list[float] = []

                for page_number in range(start_page, end_page + 1):
                    image_path = self._render_table_image_for_page(
                        fitz_doc=fitz_doc,
                        table=table,
                        page_number=page_number,
                    )
                    if image_path is None:
                        continue
                    try:
                        vlm_result = await service.extract_ptr_table_from_image(
                            image_path=image_path,
                            headers_hint=inferred_headers,
                            base_rows=table.rows[:12],
                            table_number=table.table_number,
                            page_number=page_number,
                        )
                    except Exception as e:
                        logger.debug(
                            "VLM extraction failed for table=%s page=%s: %s",
                            table.table_number,
                            page_number,
                            e,
                        )
                        continue
                    finally:
                        image_path.unlink(missing_ok=True)

                    rows = vlm_result.get("rows", [])
                    if not isinstance(rows, list) or not rows:
                        continue
                    headers = vlm_result.get("headers", [])
                    if isinstance(headers, list):
                        normalized_headers = [str(v or "").strip() for v in headers]
                        if normalized_headers and sum(1 for v in normalized_headers if v) >= 2:
                            inferred_headers = normalized_headers

                    try:
                        confidence_values.append(float(vlm_result.get("confidence", 0.0) or 0.0))
                    except (TypeError, ValueError):
                        confidence_values.append(0.0)
                    merged_rows.extend(self._normalize_rows_from_vlm(rows))

                if not merged_rows:
                    continue

                repaired_rows = self._dedupe_rows(merged_rows, inferred_headers or table.headers)
                if len(repaired_rows) < max(len(table.rows) * 0.7, 8):
                    # Guardrail: skip replacement when VLM drops too much content.
                    continue
                avg_conf = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
                if avg_conf < 0.45 and len(repaired_rows) <= len(table.rows):
                    continue

                table.headers = self._align_headers(inferred_headers or table.headers, repaired_rows)
                table.rows = self._normalize_rows_to_width(repaired_rows, len(table.headers))
                self._repair_parameter_table_rows(table)
                logger.info(
                    "Enhanced PTR table %s via VLM: rows %s -> %s (avg_conf=%.2f)",
                    table.table_number,
                    len(merged_rows),
                    len(table.rows),
                    avg_conf,
                )

    def _should_vlm_enhance_table(self, table: PTRTable) -> bool:
        if not self._looks_like_parameter_table(table):
            return False

        min_rows = max(8, int(getattr(settings, "ptr_table_vlm_min_rows", 20) or 20))
        row_count = len(table.rows)
        page_span = int(table.page_end or table.page or 1) - int(table.page or 1) + 1

        if page_span >= 2:
            return True
        if row_count >= min_rows:
            return True

        noisy_rows = 0
        for row in table.rows:
            text = " ".join(str(v or "") for v in row)
            if re.search(r"[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]", text):
                noisy_rows += 1
            if "μ" not in text and "u g/mL" in text:
                noisy_rows += 1
        return noisy_rows >= 3

    def _render_table_image_for_page(
        self,
        fitz_doc: fitz.Document,
        table: PTRTable,
        page_number: int,
    ) -> Path | None:
        page_index = page_number - 1
        if page_index < 0 or page_index >= fitz_doc.page_count:
            return None
        page = fitz_doc[page_index]
        clip: fitz.Rect | None = None

        if table.bbox:
            x0, y0, x1, y1 = table.bbox
            margin = 8.0
            if page_number == table.page:
                clip = fitz.Rect(
                    max(0.0, x0 - margin),
                    max(0.0, y0 - margin),
                    min(page.rect.width, x1 + margin),
                    min(page.rect.height, y1 + margin),
                )
            else:
                # Continuation pages often keep same horizontal table bounds.
                clip = fitz.Rect(
                    max(0.0, x0 - margin),
                    0.0,
                    min(page.rect.width, x1 + margin),
                    page.rect.height,
                )

        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=clip, alpha=False)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_path = Path(tmp.name)
        pix.save(str(temp_path))
        return temp_path

    def _normalize_rows_from_vlm(self, rows: list[object]) -> list[list[str]]:
        normalized: list[list[str]] = []
        for row in rows:
            if not isinstance(row, list):
                continue
            values = [str(v or "").strip() for v in row]
            if not any(values):
                continue
            normalized.append(values)
        return normalized

    def _align_headers(self, headers: list[str], rows: list[list[str]]) -> list[str]:
        max_width = max((len(row) for row in rows), default=0)
        if max_width <= 0:
            return [str(v or "").strip() for v in headers]
        aligned = [str(v or "").strip() for v in headers]
        if len(aligned) < max_width:
            aligned.extend([""] * (max_width - len(aligned)))
        elif len(aligned) > max_width:
            aligned = aligned[:max_width]
        return aligned

    def _normalize_rows_to_width(self, rows: list[list[str]], width: int) -> list[list[str]]:
        normalized: list[list[str]] = []
        for row in rows:
            values = [str(v or "").strip() for v in row]
            if len(values) < width:
                values.extend([""] * (width - len(values)))
            elif len(values) > width:
                values = values[:width]
            normalized.append(values)
        return normalized

    def _dedupe_rows(self, rows: list[list[str]], headers: list[str]) -> list[list[str]]:
        deduped: list[list[str]] = []
        seen: set[str] = set()
        header_key = re.sub(r"\s+", "", "|".join(str(v or "") for v in headers))
        for row in rows:
            key = re.sub(r"\s+", "", "|".join(str(v or "") for v in row))
            if not key:
                continue
            if key == header_key:
                continue
            if key in seen:
                continue
            seen.add(key)
            deduped.append([str(v or "").strip() for v in row])
        return deduped

    def _run_coroutine_blocking(self, coroutine):
        """Run coroutine from sync context, even when current thread already has event loop."""
        try:
            asyncio.get_running_loop()
            has_running_loop = True
        except RuntimeError:
            has_running_loop = False

        if not has_running_loop:
            return asyncio.run(coroutine)

        result_box: dict[str, object] = {}
        error_box: dict[str, BaseException] = {}

        def _runner() -> None:
            try:
                result_box["value"] = asyncio.run(coroutine)
            except BaseException as exc:  # noqa: BLE001
                error_box["error"] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()
        if "error" in error_box:
            raise error_box["error"]
        return result_box.get("value")


def extract_ptr(pdf_doc: PDFDocument) -> PTRDocument:
    """Convenience function to extract PTR structure.

    Args:
        pdf_doc: Parsed PDF document

    Returns:
        PTRDocument with extracted clauses and tables
    """
    extractor = PTRExtractor()
    return extractor.extract(pdf_doc)
