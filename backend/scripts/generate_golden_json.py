#!/usr/bin/env python3
"""
Generate golden expected JSON files from local sample PDFs.

Outputs:
- 素材/expected/<sample_id>/report_check.expected.json
- 素材/expected/<sample_id>/ptr_compare.expected.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

# Ensure backend root is on sys.path when executing as script.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.golden_runner import run_ptr_compare, run_report_check


def _pick_first_pdf(folder: Path) -> Path | None:
    if not folder.exists() or not folder.is_dir():
        return None
    pdfs = sorted(p for p in folder.glob("*.pdf") if p.is_file())
    return pdfs[0] if pdfs else None


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)


def _iter_sample_ids(report_root: Path, ptr_root: Path) -> list[str]:
    report_ids = {p.name for p in report_root.iterdir() if p.is_dir()} if report_root.exists() else set()
    ptr_ids = {p.name for p in ptr_root.iterdir() if p.is_dir()} if ptr_root.exists() else set()
    return sorted(report_ids | ptr_ids)


def _parse_ids(raw: str | None, all_ids: Iterable[str]) -> list[str]:
    if not raw:
        return sorted(all_ids)
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    return sorted(tokens)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate golden expected JSON files.")
    parser.add_argument(
        "--samples",
        help="Comma-separated sample IDs. Default: all discovered IDs.",
    )
    parser.add_argument(
        "--only",
        choices=["all", "report", "ptr"],
        default="all",
        help="Generate only report self-check, only ptr compare, or both.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing expected files.",
    )
    parser.add_argument(
        "--enable-llm",
        action="store_true",
        help="Enable LLM-enhanced OCR for report self-check generation.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    samples_root = repo_root / "素材"
    report_root = samples_root / "report"
    ptr_root = samples_root / "ptr"
    expected_root = samples_root / "expected"

    sample_ids = _parse_ids(args.samples, _iter_sample_ids(report_root, ptr_root))
    if not sample_ids:
        print("No samples found.")
        return 0

    print(f"Generating golden JSON for samples: {', '.join(sample_ids)}")
    generated = 0
    skipped = 0
    failed = 0

    for sample_id in sample_ids:
        report_pdf = _pick_first_pdf(report_root / sample_id)
        ptr_pdf = _pick_first_pdf(ptr_root / sample_id)
        out_dir = expected_root / sample_id

        if args.only in {"all", "report"}:
            if report_pdf is None:
                print(f"[{sample_id}] report_check: skip (report PDF not found)")
                skipped += 1
            else:
                out_path = out_dir / "report_check.expected.json"
                if out_path.exists() and not args.force:
                    print(f"[{sample_id}] report_check: skip (exists)")
                    skipped += 1
                else:
                    try:
                        result = run_report_check(report_pdf, enable_llm=args.enable_llm)
                        _write_json(out_path, result)
                        print(f"[{sample_id}] report_check: OK -> {out_path}")
                        generated += 1
                    except Exception as exc:
                        print(f"[{sample_id}] report_check: FAIL -> {exc}")
                        failed += 1

        if args.only in {"all", "ptr"}:
            if report_pdf is None or ptr_pdf is None:
                print(f"[{sample_id}] ptr_compare: skip (ptr/report PDF missing)")
                skipped += 1
            else:
                out_path = out_dir / "ptr_compare.expected.json"
                if out_path.exists() and not args.force:
                    print(f"[{sample_id}] ptr_compare: skip (exists)")
                    skipped += 1
                else:
                    try:
                        result = run_ptr_compare(ptr_pdf, report_pdf)
                        _write_json(out_path, result)
                        print(f"[{sample_id}] ptr_compare: OK -> {out_path}")
                        generated += 1
                    except Exception as exc:
                        print(f"[{sample_id}] ptr_compare: FAIL -> {exc}")
                        failed += 1

    print(
        f"Done. generated={generated}, skipped={skipped}, failed={failed}, output_root={expected_root}"
    )
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
