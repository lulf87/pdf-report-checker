"""
Golden expected JSON regression tests.

Run with:
  RUN_GOLDEN=1 pytest tests/test_golden_expected.py -q
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.services.golden_runner import normalize_result, run_ptr_compare, run_report_check


RUN_GOLDEN = os.getenv("RUN_GOLDEN") == "1"


def _pick_first_pdf(folder: Path) -> Path | None:
    if not folder.exists() or not folder.is_dir():
        return None
    pdfs = sorted(p for p in folder.glob("*.pdf") if p.is_file())
    return pdfs[0] if pdfs else None


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLES_ROOT = REPO_ROOT / "素材"
EXPECTED_ROOT = SAMPLES_ROOT / "expected"
REPORT_ROOT = SAMPLES_ROOT / "report"
PTR_ROOT = SAMPLES_ROOT / "ptr"


def _collect_report_cases() -> list[tuple[str, Path, Path]]:
    cases: list[tuple[str, Path, Path]] = []
    if not EXPECTED_ROOT.exists():
        return cases

    for sample_dir in sorted(p for p in EXPECTED_ROOT.iterdir() if p.is_dir()):
        expected = sample_dir / "report_check.expected.json"
        report_pdf = _pick_first_pdf(REPORT_ROOT / sample_dir.name)
        if expected.exists() and report_pdf is not None:
            cases.append((sample_dir.name, report_pdf, expected))
    return cases


def _collect_ptr_cases() -> list[tuple[str, Path, Path, Path]]:
    cases: list[tuple[str, Path, Path, Path]] = []
    if not EXPECTED_ROOT.exists():
        return cases

    for sample_dir in sorted(p for p in EXPECTED_ROOT.iterdir() if p.is_dir()):
        expected = sample_dir / "ptr_compare.expected.json"
        report_pdf = _pick_first_pdf(REPORT_ROOT / sample_dir.name)
        ptr_pdf = _pick_first_pdf(PTR_ROOT / sample_dir.name)
        if expected.exists() and report_pdf is not None and ptr_pdf is not None:
            cases.append((sample_dir.name, ptr_pdf, report_pdf, expected))
    return cases


@pytest.mark.golden
@pytest.mark.skipif(not RUN_GOLDEN, reason="Set RUN_GOLDEN=1 to run golden regression tests.")
@pytest.mark.parametrize(
    ("sample_id", "report_pdf", "expected_json"),
    _collect_report_cases(),
    ids=lambda v: str(v),
)
def test_report_check_matches_golden(
    sample_id: str,
    report_pdf: Path,
    expected_json: Path,
):
    expected = _load_json(expected_json)
    actual = normalize_result(run_report_check(report_pdf, enable_llm=False))
    assert actual == expected, f"report_check golden mismatch for sample {sample_id}"


@pytest.mark.golden
@pytest.mark.skipif(not RUN_GOLDEN, reason="Set RUN_GOLDEN=1 to run golden regression tests.")
@pytest.mark.parametrize(
    ("sample_id", "ptr_pdf", "report_pdf", "expected_json"),
    _collect_ptr_cases(),
    ids=lambda v: str(v),
)
def test_ptr_compare_matches_golden(
    sample_id: str,
    ptr_pdf: Path,
    report_pdf: Path,
    expected_json: Path,
):
    expected = _load_json(expected_json)
    actual = normalize_result(run_ptr_compare(ptr_pdf, report_pdf))
    assert actual == expected, f"ptr_compare golden mismatch for sample {sample_id}"

