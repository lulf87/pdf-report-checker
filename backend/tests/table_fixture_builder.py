"""Synthetic table fixtures for multidimensional table tests."""

from __future__ import annotations

from app.models.common_models import BoundingBox, CellData, TableData


def build_cell(
    text: str,
    row: int,
    col: int,
    row_span: int = 1,
    col_span: int = 1,
    page: int = 1,
) -> CellData:
    """Build a CellData with deterministic bbox for synthetic tests."""
    return CellData(
        text=text,
        row=row,
        col=col,
        row_span=row_span,
        col_span=col_span,
        bbox=BoundingBox(
            x0=float(col * 100),
            y0=float(row * 20),
            x1=float((col + 1) * 100),
            y1=float((row + 1) * 20),
            page=page,
        ),
    )


def build_table(
    rows: list[list[str]],
    page: int = 1,
    caption: str = "",
    table_number: int | None = None,
    spans: dict[tuple[int, int], tuple[int, int]] | None = None,
    headers: list[str] | None = None,
) -> TableData:
    """Build TableData from text matrix and optional span map.

    Args:
        rows: 2D text matrix
        page: source page number
        caption: table caption
        table_number: parsed table number
        spans: optional map {(row, col): (row_span, col_span)}
        headers: optional legacy header list
    """
    spans = spans or {}
    cell_rows: list[list[CellData]] = []
    for row_idx, row in enumerate(rows):
        cell_row: list[CellData] = []
        for col_idx, value in enumerate(row):
            row_span, col_span = spans.get((row_idx, col_idx), (1, 1))
            cell_row.append(
                build_cell(
                    text=value,
                    row=row_idx,
                    col=col_idx,
                    row_span=row_span,
                    col_span=col_span,
                    page=page,
                )
            )
        cell_rows.append(cell_row)

    width = max((len(r) for r in rows), default=1)
    height = max(len(rows), 1)
    bbox = BoundingBox(
        x0=0.0,
        y0=0.0,
        x1=float(width * 100),
        y1=float(height * 20),
        page=page,
    )

    return TableData(
        rows=cell_rows,
        headers=list(headers or []),
        bbox=bbox,
        page=page,
        caption=caption,
        table_number=table_number,
    )
