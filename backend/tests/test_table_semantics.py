"""Canonical table semantics tests.

These tests ensure comparator and normalizer share a consistent role
inference vocabulary and synonyms.
"""

from app.services.table_comparator import TableComparator
from app.services.table_normalizer import TableNormalizer


def test_column_role_synonym_alignment_across_normalizer_and_comparator():
    """Normalize and comparator should infer identical roles for same labels."""
    normalizer = TableNormalizer()
    comparator = TableComparator()

    cases = [
        ["参数"],
        ["参数名称"],
        ["适用型号"],
        ["规格"],
        ["型号"],
        ["默认值"],
        ["设置值"],
        ["范围"],
        ["检验结果"],
    ]

    for labels in cases:
        assert normalizer.semantics.infer_column_role(labels) == comparator.semantics.infer_column_role(labels)


def test_unknown_role_is_counted_and_resettable():
    """Unknown labels should be counted and reset cleanly."""
    semantics = TableComparator().semantics
    semantics.reset()
    assert semantics.unknown_role_count == 0

    role = semantics.infer_column_role(["未知字段"])
    assert role == "unknown"
    assert semantics.unknown_role_count == 1

    semantics.reset()
    assert semantics.unknown_role_count == 0


def test_split_path_semantics_detects_dimension_and_leaf():
    """Path with dimension+leaf should split dimensions from value leaf."""
    semantics = TableNormalizer().semantics
    dims, leaf_label, leaf_role = semantics.split_path_semantics(["心房", "标准设置"])

    assert dims == ["心房"]
    assert leaf_label == "标准设置"
    assert leaf_role in {"default", "value", "tolerance", "remark"}
