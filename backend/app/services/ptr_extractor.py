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
from pathlib import Path
from typing import Final

import fitz

from app.config import settings
from app.models.common_models import PDFDocument
from app.models.ptr_models import (
    PTRClause,
    PTRClauseNumber,
    PTRDocument,
    PTRSubItem,
    PTRTable,
    PTRTableReference,
)
from app.services.llm_vision_service import create_vlm_service

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
            page_end=table_data.page,
            position=(
                (table_data.bbox.x0, table_data.bbox.y0)
                if table_data.bbox
                else None
            ),
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

    def _merge_continuation_tables(self, tables: list[PTRTable]) -> list[PTRTable]:
        """Merge cross-page continuation tables that lose table number/header context."""
        if not tables:
            return []

        def _sort_key(table: PTRTable) -> tuple[int, float]:
            y0 = float(table.position[1]) if table.position else 0.0
            return (table.page, y0)

        ordered = sorted(tables, key=_sort_key)
        merged: list[PTRTable] = []
        merged_end_pages: list[int] = []

        for source in ordered:
            table = self._normalize_table_cells(source)
            if not merged:
                merged.append(table)
                merged_end_pages.append(table.page)
                continue

            prev = merged[-1]
            prev_end_page = merged_end_pages[-1]
            if self._is_table_continuation(prev, table, prev_end_page):
                self._merge_table_into(prev, table)
                merged_end_pages[-1] = max(prev_end_page, table.page)
                continue

            merged.append(table)
            merged_end_pages.append(table.page)

        for table in merged:
            self._repair_parameter_table_rows(table)
        for idx, table in enumerate(merged):
            table.page_end = merged_end_pages[idx]

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
        page_gap = current.page - previous_end_page
        if page_gap < 0 or page_gap > 1:
            return False

        prev_cols = max(len(previous.headers), max((len(r) for r in previous.rows), default=0))
        curr_cols = max(len(current.headers), max((len(r) for r in current.rows), default=0))
        if prev_cols == 0 or curr_cols == 0:
            return False
        if abs(prev_cols - curr_cols) > 1:
            return False

        if previous.table_number and current.table_number and previous.table_number != current.table_number:
            return False

        if previous.table_number and current.table_number == previous.table_number:
            return True

        if current.table_number is not None:
            return False

        if not previous.table_number:
            return False

        if self._looks_like_parameter_table(previous) and not self._looks_like_new_table_start(current):
            return True
        if not self._looks_like_new_table_start(current):
            return True
        return False

    def _looks_like_new_table_start(self, table: PTRTable) -> bool:
        """Detect if table fragment likely starts a fresh table with explicit headers."""
        if table.table_number is not None:
            return True

        merged_header = " ".join(h for h in table.headers if h).strip()
        if not merged_header:
            return False

        header_keywords = ["参数", "参数名称", "型号", "标准设置", "允许误差", "数值", "单位"]
        hit_count = sum(1 for keyword in header_keywords if keyword in merged_header)
        if hit_count >= 2:
            return True

        first_header = (table.headers[0] or "").strip() if table.headers else ""
        if len(first_header) >= 25 and not any(k in first_header for k in header_keywords):
            return False
        return False

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

    def _is_duplicate_header_row(self, row: list[str], headers: list[str]) -> bool:
        if not row or not headers:
            return False
        row_text = re.sub(r"\s+", "", "|".join(str(v or "") for v in row))
        header_text = re.sub(r"\s+", "", "|".join(str(v or "") for v in headers))
        if not row_text or not header_text:
            return False
        return row_text == header_text

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
