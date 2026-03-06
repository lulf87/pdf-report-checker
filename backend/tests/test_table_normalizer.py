"""Tests for canonical multidimensional table normalization.

Phase-0 intention: lock problem archetypes before migration.
"""

from __future__ import annotations

import pytest

from tests.table_fixture_builder import build_table

# NOTE: This module is introduced in Phase 1.
from app.services.table_normalizer import TableNormalizer  # type: ignore


@pytest.fixture
def normalizer() -> TableNormalizer:
    return TableNormalizer()


def test_double_header_should_generate_column_paths(normalizer: TableNormalizer):
    table = build_table(
        rows=[
            ["参数", "心房", "", "心室", ""],
            ["", "常规数值", "标准设置", "常规数值", "标准设置"],
            ["脉冲宽度(ms)", "0.1...(0.1)...1.5", "0.4", "0.1...(0.1)...1.5", "0.4"],
        ],
        headers=["参数", "心房", "", "心室", ""],
        table_number=1,
    )

    canonical = normalizer.normalize(table)

    assert canonical.diagnostics.header_row_count == 2
    assert [path.labels for path in canonical.column_paths] == [
        ["参数"],
        ["心房", "常规数值"],
        ["心房", "标准设置"],
        ["心室", "常规数值"],
        ["心室", "标准设置"],
    ]
    assert normalizer.to_legacy_headers(canonical) == [
        "参数",
        "心房 / 常规数值",
        "心房 / 标准设置",
        "心室 / 常规数值",
        "心室 / 标准设置",
    ]


def test_triple_header_should_preserve_hierarchy(normalizer: TableNormalizer):
    table = build_table(
        rows=[
            ["参数", "心房", "", "", "心室", "", ""],
            ["", "双极", "", "单极", "双极", "", "单极"],
            ["", "常规数值", "标准设置", "常规数值", "常规数值", "标准设置", "常规数值"],
            ["脉冲幅度(V)", "0.2...7.5", "3.0", "0.1...5.0", "0.2...7.5", "3.0", "0.1...5.0"],
        ],
        table_number=1,
    )

    canonical = normalizer.normalize(table)

    assert canonical.diagnostics.header_row_count == 3
    assert canonical.column_paths[1].labels == ["心房", "双极", "常规数值"]
    assert canonical.column_paths[2].labels == ["心房", "双极", "标准设置"]
    assert canonical.column_paths[6].labels == ["心室", "单极", "常规数值"]


def test_fill_down_should_only_apply_to_dimension_columns(normalizer: TableNormalizer):
    table = build_table(
        rows=[
            ["参数", "型号", "常规数值", "标准设置", "允许误差"],
            ["脉冲宽度(ms)", "Edora 8 DR", "20...(5)...350", "180-170-160", "±20"],
            ["", "Edora 8 DR", "CLS模式下:20...(5)...350", "150-140-130", ""],
        ],
        table_number=1,
    )

    canonical = normalizer.normalize(table)
    legacy_rows = normalizer.to_legacy_rows(canonical)

    # 参数列允许继承
    assert legacy_rows[1][0] == "脉冲宽度(ms)"
    # 值列禁止无边界继承
    assert legacy_rows[1][4] == ""

    param_cell = next(c for c in canonical.cells if c.row == 2 and c.col == 0)
    assert param_cell.source == "inferred"
    assert param_cell.propagated_from == (1, 0)


def test_parameter_records_should_include_dimensions_and_values(normalizer: TableNormalizer):
    table = build_table(
        rows=[
            ["参数", "型号", "常规数值", "标准设置", "允许误差"],
            ["脉冲宽度(ms)", "全部型号", "0.1...(0.1)...1.5", "0.4", "±20μs"],
        ],
        table_number=1,
    )

    canonical = normalizer.normalize(table)
    records = normalizer.to_parameter_records(canonical)

    assert len(records) == 1
    assert records[0].parameter_name == "脉冲宽度(ms)"
    assert records[0].dimensions["型号"] == "全部型号"
    assert records[0].values["标准设置"] == "0.4"
    assert records[0].values["允许误差"] == "±20μs"


def test_structure_confidence_should_drop_for_ambiguous_header(normalizer: TableNormalizer):
    table = build_table(
        rows=[
            ["", "", "", ""],
            ["", "", "", ""],
            ["随机文本A", "随机文本B", "123", "456"],
        ],
    )

    canonical = normalizer.normalize(table)
    assert canonical.diagnostics.structure_confidence < 0.7
    assert canonical.metadata.get("needs_manual_review") is True
