"""
Canonical table models for multidimensional table preservation.
"""

from dataclasses import dataclass, field
from typing import Literal

from app.models.common_models import BoundingBox

CellSource = Literal["native", "inferred", "vlm"]
CellRole = Literal["header", "body", "stub", "value", "unknown"]
ColumnRole = Literal[
    "parameter",
    "model",
    "group",
    "value",
    "default",
    "tolerance",
    "remark",
    "unknown",
]


@dataclass
class CanonicalCell:
    """Canonical cell with provenance and inferred metadata."""

    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    bbox: BoundingBox | None = None
    is_header: bool = False
    source: CellSource = "native"
    role: CellRole = "unknown"
    propagated_from: tuple[int, int] | None = None
    confidence: float | None = None


@dataclass
class ColumnPath:
    """Semantic path of one leaf column from multi-row headers."""

    leaf_col: int
    labels: list[str] = field(default_factory=list)
    role: ColumnRole = "unknown"

    @property
    def key(self) -> str:
        return " / ".join([label for label in self.labels if label])


@dataclass
class CanonicalTableDiagnostics:
    """Normalizer diagnostics for explainability and fallback routing."""

    header_row_count: int = 0
    inferred_rowspans: int = 0
    inferred_colspans: int = 0
    repeated_header_removed: int = 0
    continuation_merged: bool = False
    structure_confidence: float = 1.0
    notes: list[str] = field(default_factory=list)


@dataclass
class CanonicalTable:
    """Canonical structured table representation."""

    page_start: int
    page_end: int
    caption: str = ""
    table_number: int | None = None
    n_rows: int = 0
    n_cols: int = 0
    cells: list[CanonicalCell] = field(default_factory=list)
    header_rows: list[int] = field(default_factory=list)
    body_rows: list[int] = field(default_factory=list)
    column_paths: list[ColumnPath] = field(default_factory=list)
    diagnostics: CanonicalTableDiagnostics = field(default_factory=CanonicalTableDiagnostics)
    metadata: dict[str, object] = field(default_factory=dict)

    def get_cell(self, row: int, col: int) -> CanonicalCell | None:
        """Get canonical cell at row/col."""
        for cell in self.cells:
            if cell.row == row and cell.col == col:
                return cell
        return None


@dataclass
class ParameterRecord:
    """Semantic parameter-level view extracted from canonical table."""

    parameter_name: str
    dimensions: dict[str, str] = field(default_factory=dict)
    values: dict[str, str] = field(default_factory=dict)
    source_rows: list[int] = field(default_factory=list)
