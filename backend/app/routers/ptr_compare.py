"""
PTR Compare API Router.

Provides endpoints for uploading PTR and report PDFs,
tracking comparison progress, and retrieving results.
"""

import asyncio
import logging
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

import fitz
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.models.ptr_models import PTRDocument
from app.models.report_models import ReportDocument
from app.services.comparator import (
    ClauseComparator,
    ComparisonDetail,
    ComparisonResult,
)
from app.services.pdf_parser import PDFParser
from app.services.ptr_extractor import PTRExtractor
from app.services.report_extractor import ReportExtractor
from app.services.table_comparator import (
    TableComparator,
    TableExpansionResult,
    compare_table_expansions,
)
from app.services.report_export_service import export_ptr_to_pdf

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/ptr", tags=["PTR Compare"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_PDF_PAGES = 200

# In-memory task storage (in production, use Redis or database)
tasks: dict[str, dict[str, Any]] = {}


class TaskStatus(str, Enum):
    """Status of a comparison task."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class ComparisonTask(BaseModel):
    """Model for comparison task."""

    task_id: str
    status: TaskStatus
    progress: int = 0
    message: str = ""
    error: str | None = None
    result: dict[str, Any] | None = None


class UploadResponse(BaseModel):
    """Response model for file upload."""

    task_id: str
    status: TaskStatus
    message: str


class ProgressResponse(BaseModel):
    """Response model for progress check."""

    task_id: str
    status: TaskStatus
    progress: int
    message: str
    error: str | None = None


class ResultResponse(BaseModel):
    """Response model for comparison result."""

    task_id: str
    status: TaskStatus
    result: dict[str, Any] | None = None
    error: str | None = None


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    ptr_file: UploadFile = File(..., description="PTR PDF file"),
    report_file: UploadFile = File(..., description="Report PDF file"),
) -> UploadResponse:
    """Upload PTR and report PDF files for comparison.

    Args:
        ptr_file: PTR (Product Technical Requirements) PDF file
        report_file: Inspection Report PDF file

    Returns:
        UploadResponse with task ID
    """
    # Generate task ID
    task_id = str(uuid.uuid4())

    # Initialize task
    tasks[task_id] = {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "progress": 0,
        "message": "Files uploaded, starting processing",
        "error": None,
        "result": None,
        "ptr_file": ptr_file.filename,
        "report_file": report_file.filename,
    }

    # Save uploaded files
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    ptr_path = upload_dir / f"{task_id}_ptr.pdf"
    report_path = upload_dir / f"{task_id}_report.pdf"

    try:
        # Save files
        with ptr_path.open("wb") as f:
            content = await ptr_file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="PTR文件大小超过50MB限制")
            try:
                with fitz.open(stream=content, filetype="pdf") as pdf:
                    if pdf.page_count > MAX_PDF_PAGES:
                        raise HTTPException(
                            status_code=400,
                            detail=f"PTR PDF页数超过限制（最多{MAX_PDF_PAGES}页）",
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Skip PTR PDF page-count validation: {e}")
            f.write(content)

        with report_path.open("wb") as f:
            content = await report_file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="报告文件大小超过50MB限制")
            try:
                with fitz.open(stream=content, filetype="pdf") as pdf:
                    if pdf.page_count > MAX_PDF_PAGES:
                        raise HTTPException(
                            status_code=400,
                            detail=f"报告PDF页数超过限制（最多{MAX_PDF_PAGES}页）",
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Skip report PDF page-count validation: {e}")
            f.write(content)

        # Start processing in background
        asyncio.create_task(
            process_comparison(task_id, str(ptr_path), str(report_path))
        )

        logger.info(f"Created comparison task {task_id}")

        return UploadResponse(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            message="Files uploaded successfully, processing started",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        tasks[task_id]["status"] = TaskStatus.ERROR
        tasks[task_id]["error"] = str(e)

        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.get("/{task_id}/progress", response_model=ProgressResponse)
async def get_progress(task_id: str) -> ProgressResponse:
    """Get the progress of a comparison task.

    Args:
        task_id: Task ID from upload response

    Returns:
        ProgressResponse with current status
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    return ProgressResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        error=task.get("error"),
    )


@router.get("/{task_id}/result", response_model=ResultResponse)
async def get_result(task_id: str) -> ResultResponse:
    """Get the result of a comparison task.

    Args:
        task_id: Task ID from upload response

    Returns:
        ResultResponse with comparison results
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    if task["status"] == TaskStatus.PROCESSING:
        raise HTTPException(
            status_code=202,
            detail="Task still processing",
        )

    if task["status"] == TaskStatus.ERROR:
        return ResultResponse(
            task_id=task_id,
            status=TaskStatus.ERROR,
            result=None,
            error=task.get("error", "Unknown error"),
        )

    return ResultResponse(
        task_id=task_id,
        status=task["status"],
        result=task["result"],
    )


@router.get("/{task_id}/export")
async def export_result(task_id: str) -> Response:
    """Export comparison result as PDF.

    Args:
        task_id: Task ID from upload response

    Returns:
        PDF file download
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    if task["status"] != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Task not completed yet",
        )

    result = task.get("result")
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No result available",
        )

    try:
        # Transform result to match expected format
        export_result = {
            "statistics": {
                "total": result.get("summary", {}).get("total_clauses", 0),
                "consistent": result.get("summary", {}).get("matches", 0),
                "inconsistent": result.get("summary", {}).get("differs", 0)
                + result.get("summary", {}).get("missing", 0),
                "consistency_rate": result.get("summary", {}).get("match_rate", 0) * 100,
            },
            "clauses": [
                {
                    "code": clause.get("ptr_number", ""),
                    "title": clause.get("ptr_text", "")[:50] + "..."
                    if len(clause.get("ptr_text", "")) > 50
                    else clause.get("ptr_text", ""),
                    "status": clause.get("result", "unknown"),
                    "is_consistent": clause.get("result") == "match",
                }
                for clause in result.get("clauses", [])
            ],
        }

        # Generate PDF
        pdf_bytes = export_ptr_to_pdf(export_result)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ptr_comparison_{task_id}.pdf"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting PDF for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


async def process_comparison(
    task_id: str,
    ptr_path: str,
    report_path: str,
) -> None:
    """Process PTR and report comparison in background.

    Args:
        task_id: Task ID
        ptr_path: Path to PTR PDF file
        report_path: Path to report PDF file
    """
    try:
        task = tasks[task_id]
        task["status"] = TaskStatus.PROCESSING
        task["progress"] = 10
        task["message"] = "Parsing PDF files"

        # Parse PTR PDF
        logger.info(f"Task {task_id}: Parsing PTR PDF")
        pdf_parser = PDFParser()
        ptr_pdf_doc = pdf_parser.parse(ptr_path)

        task["progress"] = 30
        task["message"] = "Extracting PTR clauses"

        # Extract PTR structure
        ptr_extractor = PTRExtractor()
        ptr_doc = ptr_extractor.extract(ptr_pdf_doc)

        task["progress"] = 50
        task["message"] = "Parsing report PDF"

        # Parse Report PDF
        logger.info(f"Task {task_id}: Parsing report PDF")
        report_pdf_doc = pdf_parser.parse(report_path)

        task["progress"] = 60
        task["message"] = "Extracting report data"

        # Extract report structure
        report_extractor = ReportExtractor()
        report_doc = report_extractor.extract_from_pdf_doc(report_pdf_doc)

        task["progress"] = 70
        task["message"] = "Comparing clauses"

        # Compare clauses
        logger.info(f"Task {task_id}: Comparing clauses")
        clause_comparator = ClauseComparator()
        comparison_results = clause_comparator.compare_documents(
            ptr_doc, report_doc
        )

        task["progress"] = 85
        task["message"] = "Comparing table expansions"

        # Compare table expansions
        logger.info(f"Task {task_id}: Comparing table expansions")
        table_comparator = TableComparator()
        report_items = (
            report_doc.inspection_table.items
            if report_doc.inspection_table
            else []
        )
        table_results = table_comparator.compare_table_references(
            ptr_doc, report_items
        )

        task["progress"] = 95
        task["message"] = "Finalizing results"

        # Build result
        result = build_comparison_result(
            ptr_doc,
            report_doc,
            comparison_results,
            table_results,
        )

        task["progress"] = 100
        task["status"] = TaskStatus.COMPLETED
        task["message"] = "Comparison completed successfully"
        task["result"] = result

        logger.info(f"Task {task_id}: Comparison completed")

    except Exception as e:
        logger.error(f"Task {task_id}: Error during processing: {e}")
        task["status"] = TaskStatus.ERROR
        task["error"] = str(e)
        task["message"] = f"Processing failed: {e}"


def build_comparison_result(
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
    comparison_results: list[ComparisonDetail],
    table_results: list[TableExpansionResult],
) -> dict[str, Any]:
    """Build comparison result dictionary.

    Args:
        ptr_doc: PTR document
        report_doc: Report document
        comparison_results: Clause comparison results
        table_results: Table expansion results

    Returns:
        Result dictionary
    """
    # Count results by type
    total_clauses = len(comparison_results)
    matches = sum(1 for r in comparison_results if r.is_match)
    differs = sum(1 for r in comparison_results if r.result == ComparisonResult.DIFFER)
    missing = sum(1 for r in comparison_results if r.result == ComparisonResult.MISSING)
    excluded = sum(1 for r in comparison_results if r.result == ComparisonResult.EXCLUDED)
    special_status_counts: dict[str, int] = {}
    for detail in comparison_results:
        status = str(getattr(detail, "comparison_status", "") or "")
        if status and status != "pass":
            special_status_counts[status] = special_status_counts.get(status, 0) + 1
    evaluated_clauses = max(total_clauses - excluded, 0)
    out_of_scope_clauses = [
        str(r.ptr_clause.number)
        for r in comparison_results
        if r.result == ComparisonResult.EXCLUDED and r.ptr_clause is not None
    ]
    missing_in_scope = [
        str(r.ptr_clause.number)
        for r in comparison_results
        if r.result == ComparisonResult.MISSING and r.ptr_clause is not None
    ]

    # Build table details and clause->table mapping
    tables = []
    table_by_clause: dict[str, list[dict[str, Any]]] = {}
    for table_result in table_results:
        table_data = {
            "table_number": table_result.table_number,
            "clause_number": table_result.clause_number,
            "found": table_result.table_found,
            "total_parameters": table_result.total_parameters,
            "matches": table_result.total_matches,
            "match_rate": table_result.match_rate,
        }

        table_parameters = []
        if table_result.parameters:
            table_parameters = [
                {
                    "name": p.parameter_name,
                    "ptr_value": p.ptr_value,
                    "report_value": p.report_value,
                    "matches": p.matches,
                    "status": p.comparison_status,
                    "details": p.details,
                }
                for p in table_result.parameters
            ]
            table_data["parameters"] = table_parameters

        tables.append(table_data)

        if table_result.clause_number:
            table_by_clause.setdefault(table_result.clause_number, []).append(
                {
                    "table_number": table_result.table_number,
                    "found": table_result.table_found,
                    "total_parameters": table_result.total_parameters,
                    "matches": table_result.total_matches,
                    "match_rate": table_result.match_rate,
                    "parameters": table_parameters,
                }
            )

    # Build clause details
    clauses = []
    for detail in comparison_results:
        clause_number = str(detail.ptr_clause.number) if detail.ptr_clause else ""
        clause_data = {
            "ptr_number": clause_number,
            "ptr_text": detail.ptr_clause.text_content if detail.ptr_clause else "",
            "report_text": (
                detail.report_text_for_display
                if detail.report_text_for_display
                else (detail.report_item.standard_requirement if detail.report_item else "")
            ),
            "result": detail.result.value,
            "status": getattr(detail, "comparison_status", "pass"),
            "similarity": detail.similarity,
            "match_reason": detail.match_reason,
        }
        if getattr(detail, "details", None):
            clause_data["details"] = detail.details

        if detail.has_differences:
            clause_data["differences"] = [
                {
                    "text": d.text,
                    "type": d.type,
                }
                for d in detail.differences
            ]

        related_tables = table_by_clause.get(clause_number, [])
        if related_tables:
            clause_data["table_expansions"] = related_tables

        clauses.append(clause_data)

    return {
        "summary": {
            "total_clauses": total_clauses,
            "evaluated_clauses": evaluated_clauses,
            "matches": matches,
            "differs": differs,
            "missing": missing,
            "excluded": excluded,
            "special_status_counts": special_status_counts,
            "match_rate": matches / evaluated_clauses if evaluated_clauses > 0 else 0.0,
        },
        "warnings": {
            "out_of_scope": {
                "count": len(out_of_scope_clauses),
                "clauses": out_of_scope_clauses,
                "message": "以下条款不在第三页检验项目范围内，已从正文一致性判定中排除。",
            },
            "missing_in_scope": {
                "count": len(missing_in_scope),
                "clauses": missing_in_scope,
                "message": "以下条款在第三页检验项目范围内，但未在报告正文检验表中提取到对应条款。",
            },
        },
        "clauses": clauses,
        "tables": tables,
        "ptr_info": {
            "total_clauses": len(ptr_doc.clauses),
            "total_tables": len(ptr_doc.tables),
        },
        "report_info": {
            "total_inspection_items": report_doc.total_inspection_items,
        },
    }
