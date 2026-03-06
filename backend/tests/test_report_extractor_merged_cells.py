"""Merged-cell focused tests for report extractor (C08 archetypes)."""

from app.services.report_extractor import ReportExtractor
from tests.table_fixture_builder import build_cell, build_table


def _build_inspection_table_with_merge_in_result_columns():
    return build_table(
        rows=[
            ["序号", "检验项目", "标准条款", "标准要求", "检验结果", "单项结论", "备注"],
            ["1", "应用条件", "4.1", "应满足要求", "符合要求", "符合", "/"],
            ["", "", "", "", "", "", ""],
        ],
        headers=["序号", "检验项目", "标准条款", "标准要求", "检验结果", "单项结论", "备注"],
        spans={
            # row-1 values merged downward to row-2
            (1, 0): (2, 1),
            (1, 1): (2, 1),
            (1, 2): (2, 1),
            (1, 3): (2, 1),
            (1, 4): (2, 1),
            (1, 5): (2, 1),
            (1, 6): (2, 1),
        },
    )


def _build_inspection_table_with_empty_merged_header_value():
    return build_table(
        rows=[
            ["序号", "检验项目", "标准条款", "标准要求", "检验结果", "单项结论", "备注"],
            ["125", "控制装置", "201.7.4.2", "增补：...", "", "/", "/"],
            ["", "", "", "", "", "", ""],
        ],
        headers=["序号", "检验项目", "标准条款", "标准要求", "检验结果", "单项结论", "备注"],
        spans={
            (1, 0): (2, 1),
            (1, 1): (2, 1),
            (1, 2): (2, 1),
            (1, 3): (2, 1),
            (1, 4): (2, 1),
            (1, 5): (2, 1),
            (1, 6): (2, 1),
        },
    )


def test_extract_items_should_fill_from_merged_cells_for_c08_non_empty_fields():
    extractor = ReportExtractor(use_ocr=False)
    table = _build_inspection_table_with_merge_in_result_columns()

    items = extractor._extract_items_from_table(page_num=3, table=table)

    assert len(items) == 2
    # continuation row should inherit merged values; today this often gets lost.
    assert items[1].test_result == "符合要求"
    assert items[1].item_conclusion == "符合"
    assert items[1].remark == "/"
    assert items[1].field_provenance.get("test_result") == "merge_inferred"
    assert items[1].field_provenance.get("item_conclusion") == "merge_inferred"
    assert items[1].field_provenance.get("remark") == "merge_inferred"

def test_extract_items_should_keep_empty_when_merged_anchor_is_empty():
    extractor = ReportExtractor(use_ocr=False)
    table = _build_inspection_table_with_empty_merged_header_value()

    items = extractor._extract_items_from_table(page_num=4, table=table)

    assert len(items) == 2
    # merged anchor itself is empty, inherited value must stay empty.
    assert items[1].test_result == ""
    assert items[1].field_provenance.get("test_result") == "native"

def test_has_merged_cells_should_detect_native_or_inferred_merge():
    extractor = ReportExtractor(use_ocr=False)
    row = [
        build_cell("125", 0, 0, row_span=2),
        build_cell("控制装置", 0, 1, row_span=2),
        build_cell("", 0, 2),
    ]

    assert extractor._has_merged_cells(row) is True

    # Future-proof assertion: inferred merge flag should also be accepted in phase-3.
    inferred_row = [
        build_cell("", 1, 0),
        build_cell("", 1, 1),
    ]
    setattr(inferred_row[0], "source", "inferred")
    assert extractor._has_merged_cells(inferred_row) is True



def test_report_extractor_real_sample_entrypoint_when_available():
    """Golden entry: when sample exists, extractor should produce inspection table object."""
    from pathlib import Path

    base = Path(__file__).resolve().parents[2] / "素材" / "report" / "3940"
    pdfs = sorted(p for p in base.glob("*.pdf") if p.is_file())
    if not pdfs:
        return

    extractor = ReportExtractor()
    report_doc = extractor.extract_from_file(pdfs[0])
    assert report_doc is not None
