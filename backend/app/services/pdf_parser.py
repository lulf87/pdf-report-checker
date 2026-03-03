"""
Unified PDF Parser with intelligent OCR switching.

Supports:
- Electronic PDF text extraction using PyMuPDF/fitz
- Table extraction from electronic PDFs
- Scanned document detection (text density threshold)
- Automatic OCR fallback for scanned pages
"""

import logging
import tempfile
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF

from app.models.common_models import (
    BoundingBox,
    CellData,
    PDFDocument,
    PDFPage,
    TableData,
    TextBlock,
)
from app.services.ocr_service import OCRService

logger = logging.getLogger(__name__)

# Constants
TEXT_DENSITY_THRESHOLD = 50  # Characters per page - below this, consider scanned
DEFAULT_DPI = 72  # PDF default DPI for calculations


class PDFParser:
    """Unified PDF parser with intelligent electronic/OCR switching."""

    def __init__(
        self,
        ocr_fallback: bool = True,
        text_density_threshold: int = TEXT_DENSITY_THRESHOLD,
    ):
        """Initialize PDF parser.

        Args:
            ocr_fallback: Whether to use OCR for low-text-density pages
            text_density_threshold: Threshold for detecting scanned pages (chars/page)
        """
        self.ocr_fallback = ocr_fallback
        self.text_density_threshold = text_density_threshold
        self._use_ocr = False
        self._ocr_service: OCRService | None = None

    def parse(self, file_path: str | Path) -> PDFDocument:
        """Parse PDF document and extract all content.

        Args:
            file_path: Path to PDF file

        Returns:
            PDFDocument with all extracted data
        """
        file_path = Path(file_path)
        logger.info(f"Parsing PDF: {file_path}")

        doc = fitz.open(str(file_path))
        pdf_doc = PDFDocument(
            file_path=str(file_path),
            total_pages=doc.page_count,
            metadata=self._extract_metadata(doc),
        )

        # First pass: extract text and detect scanned pages
        scanned_count = 0
        for page_num in range(doc.page_count):
            page = doc[page_num]
            pdf_page = self._parse_page(page, page_num + 1)
            pdf_doc.pages.append(pdf_page)

            # Check if page is scanned
            if self._is_page_scanned(pdf_page):
                pdf_page.is_scanned = True
                scanned_count += 1

        # Determine if document is primarily scanned
        pdf_doc.is_scanned = scanned_count > len(pdf_doc.pages) / 2

        # OCR fallback for scanned pages: recover raw_text for scanned/image PDFs.
        if self.ocr_fallback and scanned_count > 0:
            recovered_count = 0
            for page_idx, parsed_page in enumerate(pdf_doc.pages):
                if not parsed_page.is_scanned:
                    continue
                ocr_text = self._extract_text_with_ocr(doc[page_idx], parsed_page.page_number)
                if ocr_text and ocr_text.strip():
                    parsed_page.raw_text = ocr_text
                    parsed_page.text_density = len(ocr_text)
                    recovered_count += 1

            if recovered_count > 0:
                logger.info(
                    f"OCR fallback recovered text for {recovered_count} scanned pages"
                )

        # Second pass: extract tables (only from non-scanned pages)
        for page_num in range(doc.page_count):
            if not pdf_doc.pages[page_num].is_scanned:
                tables = self._extract_tables(doc[page_num], page_num + 1)
                pdf_doc.pages[page_num].tables = tables

        doc.close()
        logger.info(
            f"Parsed {pdf_doc.total_pages} pages, "
            f"{scanned_count} detected as scanned"
        )

        return pdf_doc

    def _extract_metadata(self, doc: fitz.Document) -> dict[str, object]:
        """Extract PDF metadata."""
        metadata = {}
        meta = doc.metadata
        if meta:
            metadata["title"] = meta.get("title", "")
            metadata["author"] = meta.get("author", "")
            metadata["subject"] = meta.get("subject", "")
            metadata["keywords"] = meta.get("keywords", "")
            metadata["creator"] = meta.get("creator", "")
            metadata["producer"] = meta.get("producer", "")
        return metadata

    def _parse_page(self, page: fitz.Page, page_number: int) -> PDFPage:
        """Parse a single page and extract text blocks.

        Args:
            page: PyMuPDF page object
            page_number: 1-indexed page number

        Returns:
            PDFPage with extracted content
        """
        # Get page dimensions
        rect = page.rect
        width, height = rect.width, rect.height

        # Extract raw text
        raw_text = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        # Extract text blocks with position information
        text_blocks = []
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)[
            "blocks"
        ]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"]
                    if not text.strip():
                        continue

                    # Create bounding box
                    bbox = BoundingBox(
                        x0=span["origin"][0],
                        y0=span["origin"][1],
                        x1=span["origin"][0] + span["size"],
                        y1=span["origin"][1] - span["size"],
                        page=page_number,
                    )

                    # Detect text properties
                    font_flags = span.get("flags", 0)
                    is_bold = bool(font_flags & 2**4)  # Bold flag in fitz

                    text_block = TextBlock(
                        text=text,
                        bbox=bbox,
                        font_size=span["size"],
                        font_name=span.get("font", ""),
                        is_bold=is_bold,
                    )
                    text_blocks.append(text_block)

        # Calculate text density
        text_density = len(raw_text) if raw_text else 0

        return PDFPage(
            page_number=page_number,
            width=width,
            height=height,
            text_blocks=text_blocks,
            raw_text=raw_text,
            text_density=text_density,
        )

    def _is_page_scanned(self, page: PDFPage) -> bool:
        """Determine if a page is scanned based on text density.

        Args:
            page: PDFPage to check

        Returns:
            True if page appears to be scanned
        """
        # Check text density
        if page.text_density < self.text_density_threshold:
            logger.debug(
                f"Page {page.page_number} text density {page.text_density} "
                f"below threshold {self.text_density_threshold}, marking as scanned"
            )
            return True

        # Additional check: if text blocks are very sparse
        if page.text_blocks:
            # Calculate average font size
            avg_font_size = sum(b.font_size for b in page.text_blocks) / len(
                page.text_blocks
            )
            # Very small font sizes might indicate noise from scan
            if avg_font_size < 3:
                logger.debug(
                    f"Page {page.page_number} average font size {avg_font_size:.2f} "
                    f"suspiciously small, marking as scanned"
                )
                return True

        return False

    def _extract_tables(self, page: fitz.Page, page_number: int) -> list[TableData]:
        """Extract tables from a page using PyMuPDF's table detection.

        Args:
            page: PyMuPDF page object
            page_number: 1-indexed page number

        Returns:
            List of TableData objects
        """
        tables = []

        try:
            # Use find_tables to detect tables
            table_finder = page.find_tables()
            found_tables = table_finder.tables

            for i, table in enumerate(found_tables):
                if not table.header:
                    continue

                # Extract table data
                rows: list[list[CellData]] = []
                headers = []

                # PyMuPDF table API changed across versions:
                # - header is now a TableHeader object (use `header.names`)
                # - table bbox / row cell bboxes are tuples instead of fitz.Rect
                header_names = getattr(table.header, "names", None)
                if isinstance(header_names, list):
                    headers = [str(name) if name is not None else "" for name in header_names]
                else:
                    try:
                        headers = [str(cell) if cell is not None else "" for cell in table.header]
                    except TypeError:
                        headers = []

                extracted_rows = table.extract() if hasattr(table, "extract") else []
                if extracted_rows is None:
                    extracted_rows = []

                row_count = max(len(extracted_rows), int(getattr(table, "row_count", 0) or 0))
                max_row_len = max((len(r) for r in extracted_rows if isinstance(r, list)), default=0)
                col_count = max(int(getattr(table, "col_count", 0) or 0), len(headers), max_row_len)

                table_rows = getattr(table, "rows", []) or []
                for row_idx in range(row_count):
                    row_cells: list[CellData] = []
                    row_texts = extracted_rows[row_idx] if row_idx < len(extracted_rows) else []
                    row_bboxes = (
                        getattr(table_rows[row_idx], "cells", []) if row_idx < len(table_rows) else []
                    )

                    for col_idx in range(col_count):
                        raw_cell = row_texts[col_idx] if col_idx < len(row_texts) else ""
                        cell_text = str(raw_cell) if raw_cell is not None else ""

                        bbox = None
                        if col_idx < len(row_bboxes):
                            cell_box = row_bboxes[col_idx]
                            if cell_box and len(cell_box) >= 4:
                                bbox = BoundingBox(
                                    x0=float(cell_box[0]),
                                    y0=float(cell_box[1]),
                                    x1=float(cell_box[2]),
                                    y1=float(cell_box[3]),
                                    page=page_number,
                                )

                        row_cells.append(
                            CellData(
                                text=cell_text,
                                row=row_idx,
                                col=col_idx,
                                bbox=bbox,
                            )
                        )

                    rows.append(row_cells)

                # Calculate table bounding box
                raw_table_bbox = table.bbox
                if isinstance(raw_table_bbox, fitz.Rect):
                    table_rect = raw_table_bbox
                else:
                    table_rect = fitz.Rect(*raw_table_bbox)

                table_bbox = BoundingBox(
                    x0=table_rect.x0,
                    y0=table_rect.y0,
                    x1=table_rect.x1,
                    y1=table_rect.y1,
                    page=page_number,
                )

                # Detect table number from caption or context
                table_number = self._detect_table_number(page, table_rect)

                table_data = TableData(
                    rows=rows,
                    headers=headers,
                    bbox=table_bbox,
                    page=page_number,
                    table_number=table_number,
                )
                tables.append(table_data)

                logger.debug(
                    f"Extracted table {i + 1} on page {page_number}: "
                    f"{len(rows)} rows x {len(headers)} cols"
                )

        except Exception as e:
            logger.warning(f"Error extracting tables from page {page_number}: {e}")

        return tables

    def _extract_text_with_ocr(self, page: fitz.Page, page_number: int) -> str:
        """Extract page text via OCR by rendering page image."""
        try:
            if self._ocr_service is None:
                self._ocr_service = OCRService()

            matrix = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=matrix, alpha=False)

            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    temp_path = Path(tmp.name)
                pix.save(str(temp_path))

                ocr_result = self._ocr_service.process_image(
                    image_path=temp_path,
                    extract_fields=False,
                )
                if ocr_result.success:
                    return ocr_result.raw_text or ""
                return ""
            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.warning(f"OCR fallback failed on page {page_number}: {e}")
            return ""

    def _detect_table_number(
        self, page: fitz.Page, table_bbox: fitz.Rect
    ) -> int | None:
        """Attempt to detect table number (e.g., "表1", "Table 1").

        Args:
            page: PyMuPDF page object
            table_bbox: Bounding box of the table

        Returns:
            Table number if found, None otherwise
        """
        # Search for table caption above the table
        search_area = fitz.Rect(
            table_bbox.x0,
            max(0, table_bbox.y0 - 50),
            table_bbox.x1,
            table_bbox.y0,
        )

        text = page.get_text("text", clip=search_area)

        # Look for patterns like "表1", "Table 1", "表 1"
        import re

        patterns = [
            r"表\s*(\d+)",
            r"Table\s*(\d+)",
            r"附表\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    pass

        return None

    def needs_ocr(self, doc: PDFDocument) -> bool:
        """Check if document needs OCR processing.

        Args:
            doc: PDFDocument to check

        Returns:
            True if OCR is recommended
        """
        return doc.is_scanned and self.ocr_fallback

    def get_scanned_page_numbers(self, doc: PDFDocument) -> list[int]:
        """Get list of page numbers that need OCR.

        Args:
            doc: PDFDocument to check

        Returns:
            List of page numbers (1-indexed)
        """
        return [p.page_number for p in doc.get_scanned_pages()]


def parse_pdf(file_path: str | Path, use_ocr: bool = True) -> PDFDocument:
    """Convenience function to parse a PDF file.

    Args:
        file_path: Path to PDF file
        use_ocr: Whether to enable OCR fallback

    Returns:
        PDFDocument with extracted content
    """
    parser = PDFParser(ocr_fallback=use_ocr)
    return parser.parse(file_path)


def is_scanned_pdf(file_path: str | Path) -> bool:
    """Quick check if PDF is primarily scanned.

    Args:
        file_path: Path to PDF file

    Returns:
        True if PDF appears to be scanned
    """
    parser = PDFParser()
    doc = parser.parse(file_path)
    return doc.is_scanned
