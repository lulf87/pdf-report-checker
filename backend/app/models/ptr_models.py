"""
Data models for PTR (Product Technical Requirements) document parsing.

Defines structures for clauses, hierarchies, and table references.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PTRClauseNumber:
    """Represents a hierarchical clause number in PTR.

    Examples:
        2
        2.1
        2.1.1
        2.1.1.1
    """

    parts: tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self):
        """Validate and normalize the clause number."""
        if not self.parts:
            self.parts = (0,)
        if self.parts[0] != 2:
            # PTR chapter 2 is the target
            pass

    @classmethod
    def from_string(cls, s: str) -> "PTRClauseNumber | None":
        """Parse clause number from string.

        Args:
            s: String like "2.1.1"

        Returns:
            PTRClauseNumber or None if invalid
        """
        try:
            parts = tuple(int(p.strip()) for p in s.split(".") if p.strip())
            if not parts:
                return None
            return cls(parts=parts)
        except (ValueError, AttributeError):
            return None

    def __str__(self) -> str:
        """String representation."""
        return ".".join(str(p) for p in self.parts)

    def __eq__(self, other: object) -> bool:
        """Compare clause numbers."""
        if not isinstance(other, PTRClauseNumber):
            return False
        return self.parts == other.parts

    def __lt__(self, other: "PTRClauseNumber") -> bool:
        """Compare for sorting."""
        return self.parts < other.parts

    @property
    def level(self) -> int:
        """Hierarchy level (1 for 2, 2 for 2.1, etc.)."""
        return len(self.parts)

    @property
    def is_chapter_2(self) -> bool:
        """Check if this is chapter 2 (main chapter)."""
        return self.parts == (2,)

    @property
    def parent(self) -> "PTRClauseNumber | None":
        """Get parent clause number."""
        if len(self.parts) <= 1:
            return None
        return PTRClauseNumber(parts=self.parts[:-1])


@dataclass
class PTRSubItem:
    """A sub-item within a clause (a, b, c or ——).

    Attributes:
        marker: The item marker (e.g., "a)", "b)", "——")
        text: The item text content
        position: Position in source (if available)
    """

    marker: str
    text: str
    position: int = 0

    def __str__(self) -> str:
        """String representation."""
        return f"{self.marker} {self.text}"


@dataclass
class PTRTableReference:
    """A reference to a table within a clause.

    Attributes:
        table_number: The referenced table number (e.g., 1 for "表1")
        context: Text surrounding the reference
        position: Position in clause text
    """

    table_number: int
    context: str = ""
    position: int = 0

    def __str__(self) -> str:
        """String representation."""
        return f"表{self.table_number}"


@dataclass
class PTRClause:
    """A clause from PTR Chapter 2.

    Attributes:
        number: Clause number (e.g., 2.1.1)
        full_text: Full clause text including number
        text_content: Clause text without the number prefix
        level: Hierarchy level (1-4 typically)
        parent_number: Parent clause number
        sub_items: List of sub-items (a, b, c, etc.)
        table_references: List of table references ("见表X")
        position: Page and position in document
        raw_text: Original raw text for reference
    """

    number: PTRClauseNumber
    full_text: str
    text_content: str
    level: int = 1
    parent_number: PTRClauseNumber | None = None
    sub_items: list[PTRSubItem] = field(default_factory=list)
    table_references: list[PTRTableReference] = field(default_factory=list)
    position: tuple[int, int] | None = None  # (page, offset)
    raw_text: str = ""
    clause_type: str = "main_requirement"

    def __str__(self) -> str:
        """String representation."""
        return f"{self.number} {self.text_content}"

    def has_table_references(self) -> bool:
        """Check if clause references any tables."""
        return len(self.table_references) > 0

    def has_sub_items(self) -> bool:
        """Check if clause has sub-items."""
        return len(self.sub_items) > 0

    def get_all_table_numbers(self) -> list[int]:
        """Get all referenced table numbers."""
        return [ref.table_number for ref in self.table_references]

    def is_standard_clause(self) -> bool:
        """Check if this is a standard clause (starts with 2)."""
        return self.number.parts[0] == 2


@dataclass
class PTRTable:
    """A table extracted from PTR document.

    Attributes:
        table_number: Table number (e.g., 1 for "表1")
        caption: Table caption/title
        headers: Column headers
        rows: Table rows (list of lists)
        page: Page number
        page_end: End page number for merged multi-page table
        position: Position on page
        bbox: Bounding box on source page (x0, y0, x1, y1)
    """

    table_number: int | None = None
    caption: str = ""
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    page: int = 1
    page_end: int | None = None
    position: tuple[int, int] | None = None
    bbox: tuple[float, float, float, float] | None = None
    header_rows: list[list[str]] = field(default_factory=list)
    column_paths: list[list[str]] = field(default_factory=list)
    structure_confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def num_rows(self) -> int:
        """Number of data rows."""
        return len(self.rows)

    @property
    def num_cols(self) -> int:
        """Number of columns."""
        return len(self.headers) if self.headers else 0

    def get_cell(self, row: int, col: int) -> str | None:
        """Get cell value."""
        if 0 <= row < self.num_rows and 0 <= col < self.num_cols:
            return self.rows[row][col]
        return None

    def find_row_by_header(self, header_text: str) -> list[str] | None:
        """Find a row by searching for header text in first column."""
        for row in self.rows:
            if row and header_text in row[0]:
                return row
        return None


@dataclass
class PTRDocument:
    """Complete parsed PTR document.

    Attributes:
        clauses: All clauses from Chapter 2
        tables: All tables referenced or in the document
        chapter2_start: Page where Chapter 2 starts
        chapter2_end: Page where Chapter 2 ends
        metadata: Document metadata
    """

    clauses: list[PTRClause] = field(default_factory=list)
    tables: list[PTRTable] = field(default_factory=list)
    chapter2_start: int | None = None
    chapter2_end: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_clause_by_number(self, number: PTRClauseNumber) -> PTRClause | None:
        """Find clause by number."""
        for clause in self.clauses:
            if clause.number == number:
                return clause
        return None

    def get_clause_by_string(self, number_str: str) -> PTRClause | None:
        """Find clause by string number."""
        number = PTRClauseNumber.from_string(number_str)
        if number:
            return self.get_clause_by_number(number)
        return None

    def get_table_by_number(self, table_number: int) -> PTRTable | None:
        """Find table by number."""
        for table in self.tables:
            if table.table_number == table_number:
                return table
        return None

    def get_tables_by_number(self, table_number: int) -> list[PTRTable]:
        """Find all tables by number (for multi-fragment/duplicate-number tables)."""
        return [table for table in self.tables if table.table_number == table_number]

    def get_clauses_at_level(self, level: int) -> list[PTRClause]:
        """Get all clauses at a specific hierarchy level."""
        return [c for c in self.clauses if c.level == level]

    def get_top_level_clauses(self) -> list[PTRClause]:
        """Get top-level clauses (direct children of Chapter 2)."""
        return [c for c in self.clauses if c.level == 2]

    def get_main_requirement_clauses(self) -> list[PTRClause]:
        """Get Chapter-2 clauses that should participate in main consistency checks."""
        return [c for c in self.clauses if c.clause_type == "main_requirement"]

    def has_table_references(self) -> bool:
        """Check if any clause references tables."""
        return any(c.has_table_references() for c in self.clauses)

    def get_all_referenced_table_numbers(self) -> list[int]:
        """Get all table numbers referenced in clauses."""
        numbers: set[int] = set()
        for clause in self.clauses:
            numbers.update(clause.get_all_table_numbers())
        return sorted(numbers)
