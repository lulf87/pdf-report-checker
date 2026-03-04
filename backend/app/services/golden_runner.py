"""
Golden runner utilities.

Run the same backend pipelines used by API routes and return normalized
JSON payloads for golden-file baselines.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from app.routers import ptr_compare, report_check


def normalize_result(value: Any) -> Any:
    """Normalize nested values for deterministic golden JSON output."""
    if isinstance(value, dict):
        return {k: normalize_result(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_result(v) for v in value]
    if isinstance(value, float):
        return round(value, 6)
    return value


async def run_report_check_async(
    report_pdf_path: str | Path,
    *,
    enable_llm: bool = False,
) -> dict[str, Any]:
    """Run report self-check pipeline and return normalized payload."""
    report_path = str(Path(report_pdf_path).resolve())
    task_id = f"golden-report-{uuid.uuid4()}"
    report_check.tasks[task_id] = {
        "task_id": task_id,
        "status": report_check.TaskStatus.PENDING,
        "progress": 0,
        "message": "Golden baseline run",
        "error": None,
        "result": None,
        "report_file": Path(report_path).name,
        "enable_llm": enable_llm,
    }

    await report_check.process_report_check(task_id, report_path, enable_llm)
    task = report_check.tasks[task_id]
    if task["status"] != report_check.TaskStatus.COMPLETED:
        raise RuntimeError(
            f"Report check failed for '{report_path}': "
            f"{task.get('error') or task.get('message')}"
        )
    return normalize_result(task.get("result") or {})


async def run_ptr_compare_async(
    ptr_pdf_path: str | Path,
    report_pdf_path: str | Path,
) -> dict[str, Any]:
    """Run PTR-vs-report pipeline and return normalized payload."""
    ptr_path = str(Path(ptr_pdf_path).resolve())
    report_path = str(Path(report_pdf_path).resolve())
    task_id = f"golden-ptr-{uuid.uuid4()}"
    ptr_compare.tasks[task_id] = {
        "task_id": task_id,
        "status": ptr_compare.TaskStatus.PENDING,
        "progress": 0,
        "message": "Golden baseline run",
        "error": None,
        "result": None,
        "ptr_file": Path(ptr_path).name,
        "report_file": Path(report_path).name,
    }

    await ptr_compare.process_comparison(task_id, ptr_path, report_path)
    task = ptr_compare.tasks[task_id]
    if task["status"] != ptr_compare.TaskStatus.COMPLETED:
        raise RuntimeError(
            f"PTR compare failed for '{ptr_path}' vs '{report_path}': "
            f"{task.get('error') or task.get('message')}"
        )
    return normalize_result(task.get("result") or {})


def run_report_check(
    report_pdf_path: str | Path,
    *,
    enable_llm: bool = False,
) -> dict[str, Any]:
    """Sync wrapper for report self-check."""
    return asyncio.run(run_report_check_async(report_pdf_path, enable_llm=enable_llm))


def run_ptr_compare(
    ptr_pdf_path: str | Path,
    report_pdf_path: str | Path,
) -> dict[str, Any]:
    """Sync wrapper for PTR-vs-report comparison."""
    return asyncio.run(run_ptr_compare_async(ptr_pdf_path, report_pdf_path))

