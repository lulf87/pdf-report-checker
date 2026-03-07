"""
Canonical table normalizer for multidimensional tables.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict

from app.models.common_models import CellData, TableData
from app.models.table_models import (
    CanonicalCell,
    CanonicalTable,
    CanonicalTableDiagnostics,
    ColumnPath,
    ParameterRecord,
)
from app.services.table_semantics import TableSemantics


class TableNormalizer:
    """Normalize raw table grids into canonical structured tables."""

    MAX_HEADER_SCAN_ROWS = 4

    def __init__(self) -> None:
        self.semantics = TableSemantics(logger=logging.getLogger(__name__))

    def normalize(self, table_data: TableData) -> CanonicalTable:
        """Normalize a table while preserving structure/provenance."""
        self.semantics.reset()
        source_rows = table_data.raw_rows or table_data.rows or []
        dense_rows = self._to_dense_matrix(source_rows)
        n_rows = len(dense_rows)
        n_cols = max((len(row) for row in dense_rows), default=0)

        diagnostics = CanonicalTableDiagnostics()
        canonical = CanonicalTable(
            page_start=table_data.page,
            page_end=table_data.page,
            caption=table_data.caption or "",
            table_number=table_data.table_number,
            n_rows=n_rows,
            n_cols=n_cols,
            diagnostics=diagnostics,
            metadata={
                "source_engine": table_data.source_engine,
                "extraction_meta": dict(table_data.extraction_meta or {}),
            },
        )

        if n_rows == 0 or n_cols == 0:
            diagnostics.structure_confidence = 0.0
            canonical.metadata["needs_manual_review"] = True
            return canonical

        canonical.header_rows = self._detect_header_rows(dense_rows)
        diagnostics.header_row_count = len(canonical.header_rows)
        canonical.body_rows = [idx for idx in range(n_rows) if idx not in canonical.header_rows]

        header_labels, inferred_colspans = self._materialize_header_labels(
            dense_rows=dense_rows,
            header_rows=canonical.header_rows,
            n_cols=n_cols,
        )
        diagnostics.inferred_colspans = inferred_colspans
        canonical.column_paths = self._build_column_paths(
            header_labels=header_labels,
            n_cols=n_cols,
            fallback_headers=table_data.headers,
        )
        canonical.metadata["unknown_role_count"] = self.semantics.unknown_role_count

        self._fill_down_dimension_cells(canonical=canonical, dense_rows=dense_rows)
        self._remove_repeated_header_rows(canonical=canonical, dense_rows=dense_rows)
        self._rebuild_cells(canonical=canonical, dense_rows=dense_rows)
        self._compute_structure_confidence(canonical=canonical)
        canonical.metadata["needs_manual_review"] = canonical.diagnostics.structure_confidence < 0.7

        return canonical

    def to_legacy_headers(self, canonical: CanonicalTable) -> list[str]:
        """Flatten column paths into legacy header labels."""
        if not canonical.column_paths:
            return []
        headers: list[str] = []
        for idx, path in enumerate(canonical.column_paths):
            key = path.key.strip()
            if key:
                headers.append(key)
            else:
                headers.append(f"列{idx + 1}")
        return headers

    def to_legacy_rows(self, canonical: CanonicalTable) -> list[list[str]]:
        """Export body rows as legacy 2D table strings."""
        if not canonical.body_rows:
            return []
        rows: list[list[str]] = []
        for row_idx in canonical.body_rows:
            row: list[str] = []
            for col_idx in range(canonical.n_cols):
                cell = canonical.get_cell(row_idx, col_idx)
                row.append(cell.text if cell else "")
            rows.append(row)
        return rows

    def to_parameter_records(self, canonical: CanonicalTable) -> list[ParameterRecord]:
        """Build semantic parameter records from canonical rows."""
        if not canonical.body_rows or not canonical.column_paths:
            return []

        roles = [path.role for path in canonical.column_paths]
        if not roles:
            roles = self._infer_column_roles(canonical.column_paths)

        parameter_col = self._find_first_role(canonical.column_paths, {"parameter"}, default=0)
        # Explicit row-level dimension columns are still useful, especially for model-type columns.
        explicit_dimension_cols = self._find_role_indexes(canonical.column_paths, {"model", "group"})
        value_cols = self._find_role_indexes(canonical.column_paths, {"value", "default", "tolerance", "remark"})
        if not value_cols:
            value_cols = [idx for idx in range(canonical.n_cols) if idx not in {parameter_col, *explicit_dimension_cols}]

        # Build records keyed by (parameter, dimensions) to avoid siblings (e.g. 心房 vs 心室) merging.
        records_by_key: dict[tuple[str, tuple[tuple[str, str], ...]], ParameterRecord] = {}

        for row_idx in canonical.body_rows:
            parameter_cell = canonical.get_cell(row_idx, parameter_col)
            parameter_name = (parameter_cell.text if parameter_cell else "").strip()
            if not parameter_name:
                continue

            base_dimensions: dict[str, str] = {}
            # 1) explicit dimension columns (型号/分组/组别...)
            for col_idx in explicit_dimension_cols:
                cell = canonical.get_cell(row_idx, col_idx)
                value = (cell.text if cell else "").strip()
                if not value:
                    continue
                base_dimensions[self._format_dimension_key(canonical.column_paths[col_idx])] = value

            # 2) path-derived dimensions (e.g., "心房" in ["心房","常规数值"]).
            for col_idx in value_cols:
                cell = canonical.get_cell(row_idx, col_idx)
                value = (cell.text if cell else "").strip()
                if not value:
                    continue

                path = canonical.column_paths[col_idx] if col_idx < len(canonical.column_paths) else ColumnPath(leaf_col=col_idx)
                dimension_labels, _, _ = self.semantics.split_path_semantics(path.labels)
                dimensions = dict(base_dimensions)
                if dimension_labels:
                    for axis_idx, axis_label in enumerate(dimension_labels, start=1):
                        key = f"axis_{axis_idx}"
                        if axis_label:
                            dimensions.setdefault(key, axis_label)

                role = roles[col_idx] if col_idx < len(roles) else path.role
                leaf_key = self.semantics.infer_value_leaf_label(path.key, role=role)
                if not leaf_key:
                    leaf_key = path.key

                key = (parameter_name, tuple(sorted(dimensions.items())))
                record = records_by_key.get(key)
                if record is None:
                    record = ParameterRecord(
                        parameter_name=parameter_name,
                        dimensions=dimensions,
                        values={},
                        source_rows=[row_idx],
                    )
                    records_by_key[key] = record
                elif row_idx not in record.source_rows:
                    record.source_rows.append(row_idx)

                if value:
                    record.values.setdefault(leaf_key, value)

        return list(records_by_key.values())

    def _infer_column_roles(self, column_paths: list[ColumnPath]) -> list[str]:
        labels = [path.labels for path in column_paths]
        return self.semantics.infer_column_roles(labels)

    @staticmethod
    def _format_dimension_key(path: ColumnPath) -> str:
        if path.key:
            return path.key
        return f"dim_{path.leaf_col}"

    def _to_dense_matrix(self, rows: list[list[CellData]]) -> list[list[CanonicalCell]]:
        n_rows = len(rows)
        n_cols = max((len(row) for row in rows), default=0)
        dense: list[list[CanonicalCell]] = []
        for row_idx in range(n_rows):
            dense_row: list[CanonicalCell] = []
            source_row = rows[row_idx] if row_idx < len(rows) else []
            for col_idx in range(n_cols):
                source_cell: CellData | None = source_row[col_idx] if col_idx < len(source_row) else None
                text = ""
                row_span = 1
                col_span = 1
                bbox = None
                if source_cell is not None:
                    text = str(source_cell.text or "")
                    row_span = int(source_cell.row_span or 1)
                    col_span = int(source_cell.col_span or 1)
                    bbox = source_cell.bbox
                dense_row.append(
                    CanonicalCell(
                        text=text.strip(),
                        row=row_idx,
                        col=col_idx,
                        row_span=row_span,
                        col_span=col_span,
                        bbox=bbox,
                        source="native",
                    )
                )
            dense.append(dense_row)
        return dense

    def _detect_header_rows(self, dense_rows: list[list[CanonicalCell]]) -> list[int]:
        max_scan = min(self.MAX_HEADER_SCAN_ROWS, len(dense_rows))
        header_rows: list[int] = []
        for row_idx in range(max_scan):
            row_texts = [cell.text for cell in dense_rows[row_idx]]
            if self._is_header_like_row(row_texts=row_texts, row_idx=row_idx):
                header_rows.append(row_idx)
                continue
            if header_rows:
                break
        return header_rows

    def _is_header_like_row(self, row_texts: list[str], row_idx: int) -> bool:
        compact_values = [re.sub(r"\s+", "", text or "") for text in row_texts]
        non_empty = [value for value in compact_values if value]
        if not non_empty:
            return False

        merged = "".join(non_empty)
        strong_keyword_hits = sum(
            1
            for keyword in [
                "参数",
                "常规数值",
                "标准设置",
                "允许误差",
                "检验结果",
                "单项结论",
                "备注",
            ]
            if keyword in merged
        )
        weak_keyword_hits = sum(
            1 for keyword in ["型号", "项目"] if keyword in merged
        )
        numeric_like = sum(1 for value in non_empty if self._is_numeric_like(value))
        numeric_ratio = numeric_like / len(non_empty) if non_empty else 1.0

        if strong_keyword_hits > 0:
            return True
        if row_idx == 0 and weak_keyword_hits > 0:
            return True
        if weak_keyword_hits >= 2 and numeric_ratio <= 0.2 and all(len(v) <= 10 for v in non_empty):
            return True
        if row_idx == 0 and numeric_ratio <= 0.35 and len(non_empty) >= 2:
            return True
        if row_idx in (1, 2) and numeric_ratio <= 0.2 and any(not value for value in compact_values):
            return True
        return False

    def _materialize_header_labels(
        self,
        dense_rows: list[list[CanonicalCell]],
        header_rows: list[int],
        n_cols: int,
    ) -> tuple[list[list[str]], int]:
        if not header_rows:
            return [], 0

        labels: list[list[str]] = []
        inferred_colspans = 0

        for row_idx in header_rows:
            row_labels: list[str] = []
            last_non_empty = ""
            for col_idx in range(n_cols):
                value = dense_rows[row_idx][col_idx].text.strip()
                if value:
                    last_non_empty = value
                    row_labels.append(value)
                    continue
                inherited = ""
                if last_non_empty and self._should_inherit_header_label(
                    dense_rows=dense_rows,
                    header_rows=header_rows,
                    row_idx=row_idx,
                    col_idx=col_idx,
                ):
                    inherited = last_non_empty
                    inferred_colspans += 1
                row_labels.append(inherited)
            labels.append(row_labels)
        return labels, inferred_colspans

    def _should_inherit_header_label(
        self,
        dense_rows: list[list[CanonicalCell]],
        header_rows: list[int],
        row_idx: int,
        col_idx: int,
    ) -> bool:
        # Inherit if lower header rows or body rows have non-empty content in this column.
        for next_row in range(row_idx + 1, len(dense_rows)):
            if dense_rows[next_row][col_idx].text.strip():
                return True
            if next_row not in header_rows:
                break
        return False

    def _build_column_paths(
        self,
        header_labels: list[list[str]],
        n_cols: int,
        fallback_headers: list[str] | None,
    ) -> list[ColumnPath]:
        if not header_labels:
            return self._build_fallback_paths(n_cols=n_cols, fallback_headers=fallback_headers or [])

        paths: list[ColumnPath] = []
        for col_idx in range(n_cols):
            labels: list[str] = []
            for row_labels in header_labels:
                label = (row_labels[col_idx] if col_idx < len(row_labels) else "").strip()
                if not label:
                    continue
                if labels and labels[-1] == label:
                    continue
                labels.append(label)
            role = self.semantics.infer_column_role(labels)
            paths.append(ColumnPath(leaf_col=col_idx, labels=labels, role=role))
        return paths

    def _build_fallback_paths(self, n_cols: int, fallback_headers: list[str]) -> list[ColumnPath]:
        paths: list[ColumnPath] = []
        for col_idx in range(n_cols):
            label = fallback_headers[col_idx].strip() if col_idx < len(fallback_headers) else ""
            labels = [label] if label else []
            role = self.semantics.infer_column_role(label) if label else ("parameter" if col_idx == 0 else "unknown")
            paths.append(ColumnPath(leaf_col=col_idx, labels=labels, role=role))
        return paths

    def _fill_down_dimension_cells(
        self,
        canonical: CanonicalTable,
        dense_rows: list[list[CanonicalCell]],
    ) -> None:
        if not canonical.body_rows:
            return

        dimension_cols = self._find_role_indexes(canonical.column_paths, {"parameter", "model", "group"})
        if not dimension_cols and canonical.n_cols > 0:
            dimension_cols = [0]
            canonical.column_paths[0].role = "parameter"

        value_cols = self._find_role_indexes(
            canonical.column_paths,
            {"value", "default", "tolerance", "remark"},
        )
        if not value_cols:
            value_cols = [idx for idx in range(canonical.n_cols) if idx not in dimension_cols]

        last_non_empty_by_col: dict[int, tuple[int, str]] = {}

        for row_idx in canonical.body_rows:
            row_has_value = any(
                dense_rows[row_idx][col_idx].text.strip()
                for col_idx in value_cols
                if col_idx < canonical.n_cols
            )
            for col_idx in dimension_cols:
                cell = dense_rows[row_idx][col_idx]
                text = cell.text.strip()
                if text:
                    last_non_empty_by_col[col_idx] = (row_idx, text)
                    continue
                if not row_has_value:
                    continue
                source = last_non_empty_by_col.get(col_idx)
                if not source:
                    continue
                source_row, source_text = source
                dense_rows[row_idx][col_idx] = CanonicalCell(
                    text=source_text,
                    row=row_idx,
                    col=col_idx,
                    row_span=1,
                    col_span=1,
                    bbox=cell.bbox,
                    source="inferred",
                    propagated_from=(source_row, col_idx),
                )
                canonical.diagnostics.inferred_rowspans += 1

    def _remove_repeated_header_rows(
        self,
        canonical: CanonicalTable,
        dense_rows: list[list[CanonicalCell]],
    ) -> None:
        if not canonical.body_rows or not canonical.column_paths:
            return
        header_signature = re.sub(
            r"\s+",
            "",
            "|".join(label for label in self.to_legacy_headers(canonical)),
        )
        filtered_body_rows: list[int] = []
        for row_idx in canonical.body_rows:
            row_signature = re.sub(
                r"\s+",
                "",
                "|".join(dense_rows[row_idx][col_idx].text for col_idx in range(canonical.n_cols)),
            )
            if header_signature and row_signature == header_signature:
                canonical.diagnostics.repeated_header_removed += 1
                continue
            filtered_body_rows.append(row_idx)
        canonical.body_rows = filtered_body_rows

    def _rebuild_cells(
        self,
        canonical: CanonicalTable,
        dense_rows: list[list[CanonicalCell]],
    ) -> None:
        cells: list[CanonicalCell] = []
        header_row_set = set(canonical.header_rows)
        for row_idx, row in enumerate(dense_rows):
            for col_idx in range(canonical.n_cols):
                cell = row[col_idx]
                role = self._cell_role_from_column(canonical, col_idx, row_idx in header_row_set)
                cells.append(
                    CanonicalCell(
                        text=cell.text,
                        row=row_idx,
                        col=col_idx,
                        row_span=cell.row_span,
                        col_span=cell.col_span,
                        bbox=cell.bbox,
                        is_header=row_idx in header_row_set,
                        source=cell.source,
                        role=role,
                        propagated_from=cell.propagated_from,
                        confidence=cell.confidence,
                    )
                )
        canonical.cells = cells

    def _cell_role_from_column(self, canonical: CanonicalTable, col_idx: int, is_header: bool) -> str:
        if is_header:
            return "header"
        role = canonical.column_paths[col_idx].role if col_idx < len(canonical.column_paths) else "unknown"
        if role in {"parameter", "model", "group"}:
            return "stub"
        if role in {"value", "default", "tolerance", "remark"}:
            return "value"
        return "unknown"

    def _compute_structure_confidence(self, canonical: CanonicalTable) -> None:
        score = 1.0
        diagnostics = canonical.diagnostics

        if diagnostics.header_row_count == 0:
            diagnostics.notes.append("header_not_detected")
            score -= 0.35
        if diagnostics.header_row_count > 3:
            diagnostics.notes.append("too_many_header_rows")
            score -= 0.1
        if not canonical.column_paths:
            diagnostics.notes.append("column_paths_missing")
            score -= 0.25

        known_roles = sum(1 for path in canonical.column_paths if path.role != "unknown")
        if canonical.column_paths and known_roles == 0:
            diagnostics.notes.append("column_roles_unknown")
            score -= 0.2

        body_len = len(canonical.body_rows)
        if body_len == 0:
            diagnostics.notes.append("body_rows_empty")
            score -= 0.2
        elif diagnostics.inferred_rowspans > body_len * 2:
            diagnostics.notes.append("too_many_fill_down")
            score -= 0.15

        if diagnostics.inferred_colspans > canonical.n_cols:
            diagnostics.notes.append("heavy_header_propagation")
            score -= 0.1

        diagnostics.structure_confidence = max(0.0, min(1.0, score))

    def _find_role_indexes(self, paths: list[ColumnPath], roles: set[str]) -> list[int]:
        return [idx for idx, path in enumerate(paths) if path.role in roles]

    def _find_first_role(self, paths: list[ColumnPath], roles: set[str], default: int = 0) -> int:
        for idx, path in enumerate(paths):
            if path.role in roles:
                return idx
        return default

    def _is_numeric_like(self, value: str) -> bool:
        return bool(
            re.fullmatch(
                r"[-+]?[\d.]+(?:%|ms|mV|V|A|Ω|KΩ|ppm|μs|us)?",
                value,
                re.IGNORECASE,
            )
        )

    def serialize_diagnostics(self, canonical: CanonicalTable) -> dict[str, object]:
        """Serialize diagnostics for logging/debugging."""
        payload = asdict(canonical.diagnostics)
        payload["column_paths"] = [path.key for path in canonical.column_paths]
        payload["roles"] = [path.role for path in canonical.column_paths]
        return payload
