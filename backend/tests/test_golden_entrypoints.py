"""Lightweight real-sample golden entrypoint checks for refactor phases."""

from pathlib import Path


def test_expected_case_inventory_when_materials_exist():
    repo_root = Path(__file__).resolve().parents[2]
    expected_root = repo_root / "素材" / "expected"
    if not expected_root.exists():
        return

    sample_dirs = [p for p in expected_root.iterdir() if p.is_dir()]
    assert sample_dirs, "素材/expected 目录存在时至少应包含一个样本子目录"

    has_ptr = any((d / "ptr_compare.expected.json").exists() for d in sample_dirs)
    has_report = any((d / "report_check.expected.json").exists() for d in sample_dirs)
    assert has_ptr or has_report
