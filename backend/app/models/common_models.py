"""
Common data models for PDF parsing and text extraction.
Shared across PTR and report processing modules.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BoundingBox:
    """Bounding box for text or table elements in PDF coordinates.

    Attributes:
        x0: Left boundary (PDF coordinates, 0 at left)
        y0: Top boundary (PDF coordinates, 0 at top)
        x1: Right boundary
        y1: Bottom boundary
        page: Page number (1-indexed)
    """

    x0: float
    y0: float
    x1: float
    y1: float
    page: int

    @property
    def width(self) -> float:
        """Width of the bounding box."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Height of the bounding box."""
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        """Area of the bounding box."""
        return self.width * self.height


@dataclass
class TextBlock:
    """A block of text extracted from PDF with position information.

    Attributes:
        text: The actual text content
        bbox: Bounding box coordinates
        font_size: Font size in points
        font_name: Font family name
        is_bold: Whether text is bold
        block_type: Type of text block (header, body, footnote, etc.)
    """

    text: str
    bbox: BoundingBox
    font_size: float = 12.0
    font_name: str = ""
    is_bold: bool = False
    block_type: str = "body"

    def __len__(self) -> int:
        """Return the length of text content."""
        return len(self.text)

    def is_empty(self) -> bool:
        """Check if text block is empty or whitespace only."""
        return not self.text or self.text.isspace()


@dataclass
class CellData:
    """Data for a single table cell.

    Attributes:
        text: Cell text content
        row: Row index (0-indexed)
        col: Column index (0-indexed)
        row_span: Number of rows this cell spans (merged cells)
        col_span: Number of columns this cell spans (merged cells)
        bbox: Bounding box of the cell
    """

    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    bbox: BoundingBox | None = None

    def is_merged(self) -> bool:
        """Check if this cell is merged (spans multiple rows or columns)."""
        return self.row_span > 1 or self.col_span > 1


@dataclass
class TableData:
    """Structured table data extracted from PDF.

    Attributes:
        rows: List of rows, each row is a list of CellData
        headers: List of header text (first row content)
        bbox: Bounding box of the entire table
        page: Page number where table starts
        caption: Table caption text if found
        table_number: Extracted table number (e.g., 1 for "表1")
    """

    rows: list[list[CellData]] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    bbox: BoundingBox | None = None
    page: int = 1
    caption: str = ""
    table_number: int | None = None
    raw_rows: list[list[CellData]] = field(default_factory=list)
    source_engine: str = "pymupdf"
    extraction_meta: dict[str, Any] = field(default_factory=dict)

    @property
    def num_rows(self) -> int:
        """Number of rows in the table."""
        return len(self.rows)

    @property
    def num_cols(self) -> int:
        """Number of columns in the table."""
        return len(self.rows[0]) if self.rows else 0

    def get_cell(self, row: int, col: int) -> CellData | None:
        """Get cell data at specified position."""
        if 0 <= row < self.num_rows and 0 <= col < self.num_cols:
            return self.rows[row][col]
        return None

    def get_row_text(self, row: int) -> list[str]:
        """Get text content of all cells in a row."""
        if 0 <= row < self.num_rows:
            return [cell.text for cell in self.rows[row]]
        return []

    def is_empty(self) -> bool:
        """Check if table has no data."""
        return self.num_rows == 0


@dataclass
class PDFPage:
    """Represents a single page in the PDF document.

    Attributes:
        page_number: Page number (1-indexed)
        width: Page width in points
        height: Page height in points
        text_blocks: List of text blocks on this page
        tables: List of tables on this page
        raw_text: Raw text content of the page
        text_density: Characters per square inch (for scan detection)
        is_scanned: Whether page is detected as scanned document
    """

    page_number: int
    width: float
    height: float
    text_blocks: list[TextBlock] = field(default_factory=list)
    tables: list[TableData] = field(default_factory=list)
    raw_text: str = ""
    text_density: float = 0.0
    is_scanned: bool = False

    def has_text(self) -> bool:
        """Check if page has extractable text."""
        return bool(self.raw_text.strip())

    def has_tables(self) -> bool:
        """Check if page has any tables."""
        return len(self.tables) > 0


@dataclass
class PDFDocument:
    """Complete PDF document with all extracted data.

    Attributes:
        pages: List of pages in the document
        file_path: Original file path
        total_pages: Total number of pages
        is_scanned: Whether document is primarily scanned
        metadata: PDF metadata dictionary
    """

    pages: list[PDFPage] = field(default_factory=list)
    file_path: str = ""
    total_pages: int = 0
    is_scanned: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_page(self, page_number: int) -> PDFPage | None:
        """Get page by number (1-indexed)."""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def get_text_pages(self) -> list[PDFPage]:
        """Get all pages that have extractable text."""
        return [p for p in self.pages if p.has_text()]

    def get_scanned_pages(self) -> list[PDFPage]:
        """Get all pages detected as scanned."""
        return [p for p in self.pages if p.is_scanned]

    def get_all_tables(self) -> list[TableData]:
        """Get all tables from all pages."""
        tables: list[TableData] = []
        for page in self.pages:
            tables.extend(page.tables)
        return tables
