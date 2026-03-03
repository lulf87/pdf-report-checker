"""
Report Check API Router.

Provides endpoints for uploading report PDFs,
tracking check progress, and retrieving results for C01-C11 checks.
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

from app.models.common_models import PDFDocument
from app.models.report_models import InspectionTable, ReportDocument, ThirdPageFields
from app.services.inspection_item_checker import InspectionItemChecker
from app.services.ocr_service import CaptionInfo, LabelOCRResult, OCRService
from app.services.page_number_checker import PageNumberChecker
from app.services.pdf_parser import PDFParser
from app.services.report_checker import ComponentRow, ReportChecker
from app.services.report_extractor import ReportExtractor
from app.services.text_normalizer import TextNormalizer
from app.services.third_page_checker import ThirdPageChecker
from app.services.report_export_service import export_report_check_to_pdf

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/report", tags=["Report Check"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_PDF_PAGES = 200

# In-memory task storage (in production, use Redis or database)
tasks: dict[str, dict[str, Any]] = {}


class TaskStatus(str, Enum):
    """Status of a check task."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class CheckStatus(str, Enum):
    """Status of individual check result."""

    PASS = "pass"
    ERROR = "error"
    WARNING = "warning"
    SKIPPED = "skipped"


class ReportCheckTask(BaseModel):
    """Model for report check task."""

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
    """Response model for check result."""

    task_id: str
    status: TaskStatus
    result: dict[str, Any] | None = None
    error: str | None = None


@router.post("/upload", response_model=UploadResponse)
async def upload_report(
    report_file: UploadFile = File(..., description="Report PDF file"),
    enable_llm: bool = False,
) -> UploadResponse:
    """Upload report PDF file for self-check.

    Args:
        report_file: Inspection Report PDF file
        enable_llm: Whether to enable LLM enhancement for OCR

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
        "message": "Report uploaded, starting processing",
        "error": None,
        "result": None,
        "report_file": report_file.filename,
        "enable_llm": enable_llm,
    }

    # Save uploaded file
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    report_path = upload_dir / f"{task_id}_report.pdf"

    try:
        # Save file
        with report_path.open("wb") as f:
            content = await report_file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="文件大小超过50MB限制")
            try:
                with fitz.open(stream=content, filetype="pdf") as pdf:
                    if pdf.page_count > MAX_PDF_PAGES:
                        raise HTTPException(
                            status_code=400,
                            detail=f"PDF页数超过限制（最多{MAX_PDF_PAGES}页）",
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Skip PDF page-count validation: {e}")
            f.write(content)

        # Start processing in background
        asyncio.create_task(
            process_report_check(task_id, str(report_path), enable_llm)
        )

        logger.info(f"Created report check task {task_id}")

        return UploadResponse(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            message="Report uploaded successfully, processing started",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading report: {e}")
        tasks[task_id]["status"] = TaskStatus.ERROR
        tasks[task_id]["error"] = str(e)

        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.get("/{task_id}/progress", response_model=ProgressResponse)
async def get_progress(task_id: str) -> ProgressResponse:
    """Get the progress of a report check task.

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
    """Get the result of a report check task.

    Args:
        task_id: Task ID from upload response

    Returns:
        ResultResponse with check results (C01-C11)
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
    """Export report check result as PDF.

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
        summary = result.get("summary", {})
        checks_data = result.get("checks", {})

        # Build checks list in expected format
        checks = []
        for code, check_info in checks_data.items():
            status = check_info.get("status", "pass").upper()
            if status == "PASS":
                status = "PASS"
            elif status == "WARNING":
                status = "WARN"
            else:
                status = "FAIL"

            checks.append({
                "code": code,
                "name": check_info.get("name", code),
                "status": status,
                "message": check_info.get("message", ""),
            })

        export_result = {
            "statistics": {
                "total": summary.get("total_checks", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("errors", 0),
                "warnings": summary.get("warnings", 0),
            },
            "checks": checks,
        }

        # Generate PDF
        pdf_bytes = export_report_check_to_pdf(export_result)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_check_{task_id}.pdf"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting PDF for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


async def process_report_check(
    task_id: str,
    report_path: str,
    enable_llm: bool,
) -> None:
    """Process report self-check in background.

    Orchestrates all checkers (C01-C11) and builds comprehensive result.

    Args:
        task_id: Task ID
        report_path: Path to report PDF file
        enable_llm: Whether to enable LLM enhancement
    """
    try:
        task = tasks[task_id]
        task["status"] = TaskStatus.PROCESSING
        task["progress"] = 5
        task["message"] = "Parsing PDF file"

        # Initialize services
        pdf_parser = PDFParser()
        report_extractor = ReportExtractor()
        ocr_service = OCRService()
        third_page_checker = ThirdPageChecker(ocr_service=ocr_service)
        report_checker = ReportChecker(ocr_service=ocr_service)
        inspection_item_checker = InspectionItemChecker()
        page_number_checker = PageNumberChecker()
        text_normalizer = TextNormalizer()

        # Step 1: Parse PDF
        logger.info(f"Task {task_id}: Parsing report PDF")
        pdf_doc = pdf_parser.parse(report_path)

        task["progress"] = 15
        task["message"] = "Extracting report structure"

        # Step 2: Extract report structure
        logger.info(f"Task {task_id}: Extracting report data")
        report_doc = report_extractor.extract_from_pdf_doc(pdf_doc)

        task["progress"] = 25
        task["message"] = "Running C01-C03 checks"

        # Step 3: C01-C03 Third page checks
        logger.info(f"Task {task_id}: Running C01-C03 checks")
        third_page_fields = report_doc.third_page_fields or ThirdPageFields()
        first_page_fields = report_doc.first_page_fields

        # Need OCR results for photo pages
        # Extract photo page data and OCR labels
        photo_pages = _extract_photo_pages(pdf_doc)
        label_ocr_results = await _extract_labels_from_photos(
            photo_pages,
            ocr_service,
            enable_llm,
            report_path,
        )
        photo_captions = _extract_photo_captions(photo_pages)

        # Run C01-C03 checks
        c01_results = third_page_checker.check_c01_field_consistency(
            first_page_fields, third_page_fields
        )
        c02_results = third_page_checker.check_c02_extended_fields(
            third_page_fields,
            label_ocr_results,
            third_page_fields.sample_name if third_page_fields else "",
        )
        c03_result = third_page_checker.check_c03_production_date_format(
            third_page_fields,
            label_ocr_results,
            third_page_fields.sample_name if third_page_fields else "",
        )

        task["progress"] = 45
        task["message"] = "Running C04-C06 checks"

        # Step 4: C04-C06 Report checks
        logger.info(f"Task {task_id}: Running C04-C06 checks")

        # Extract sample description table
        sample_description_table = _extract_sample_description_table(pdf_doc)

        c04_result = report_checker.check_c04_sample_description(
            sample_description_table,
            label_ocr_results,
        )
        c05_results = report_checker.check_c05_photo_coverage(
            sample_description_table,
            photo_captions,
        )
        c06_results = report_checker.check_c06_chinese_label_coverage(
            sample_description_table,
            label_ocr_results,
        )

        task["progress"] = 65
        task["message"] = "Running C07-C10 checks"

        # Step 5: C07-C10 Inspection item checks
        logger.info(f"Task {task_id}: Running C07-C10 checks")

        inspection_table = report_doc.inspection_table
        if not inspection_table:
            inspection_table = InspectionTable()

        c07_results = inspection_item_checker.check_c07_conclusion_logic(inspection_table)
        c08_results = inspection_item_checker.check_c08_non_empty_fields(inspection_table)
        c09_result = inspection_item_checker.check_c09_sequence_continuity(inspection_table)
        c10_result = inspection_item_checker.check_c10_continuation_markers(inspection_table)

        task["progress"] = 85
        task["message"] = "Running C11 check"

        # Step 6: C11 Page number check
        logger.info(f"Task {task_id}: Running C11 check")
        c11_result = page_number_checker.check_c11_from_pdf_document(pdf_doc)

        task["progress"] = 95
        task["message"] = "Building result"

        # Step 7: Build comprehensive result
        result = build_report_check_result(
            report_doc=report_doc,
            c01_results=c01_results,
            c02_results=c02_results,
            c03_result=c03_result,
            c04_result=c04_result,
            c05_results=c05_results,
            c06_results=c06_results,
            c07_results=c07_results,
            c08_results=c08_results,
            c09_result=c09_result,
            c10_result=c10_result,
            c11_result=c11_result,
        )

        task["progress"] = 100
        task["status"] = TaskStatus.COMPLETED
        task["message"] = "Report check completed successfully"
        task["result"] = result

        logger.info(f"Task {task_id}: Report check completed")

    except Exception as e:
        logger.error(f"Task {task_id}: Error during processing: {e}")
        task["status"] = TaskStatus.ERROR
        task["error"] = str(e)
        task["message"] = f"Processing failed: {e}"


def _extract_photo_pages(pdf_doc: PDFDocument) -> list:
    """Extract photo pages from PDF document.

    Args:
        pdf_doc: Parsed PDF document

    Returns:
        List of photo page objects
    """
    photo_pages = []

    for page in pdf_doc.pages:
        # Check if page contains photo indicators
        # (e.g., "图", "照片", "标签", "Plate", "Photo", etc.)
        text = page.raw_text.lower()
        if any(keyword in text for keyword in ["图", "照片", "标签", "plate", "photo"]):
            photo_pages.append(page)

    return photo_pages


def _count_check_status(results: list) -> tuple[int, int, int]:
    """Count pass, error, warning in results.

    Args:
        results: List of check results

    Returns:
        Tuple of (pass_count, error_count, warning_count)
    """
    pass_count = sum(1 for r in results if getattr(r, "status", None) in ("pass", CheckStatus.PASS))
    error_count = sum(1 for r in results if getattr(r, "status", None) in ("error", CheckStatus.ERROR))
    warning_count = sum(1 for r in results if getattr(r, "status", None) in ("warning", CheckStatus.WARNING))
    return pass_count, error_count, warning_count


async def _extract_labels_from_photos(
    photo_pages: list,
    ocr_service: OCRService,
    enable_llm: bool,
    report_path: str | None = None,
) -> list[tuple[CaptionInfo, LabelOCRResult]]:
    """Extract Chinese labels from photo pages using OCR.

    Args:
        photo_pages: List of photo pages
        ocr_service: OCR service
        enable_llm: Whether to enable LLM enhancement

    Returns:
        List of (caption info, OCR result) tuples
    """
    results = []

    for page in photo_pages:
        # Extract caption info
        caption_info = ocr_service.extract_caption_info(page.raw_text)

        if caption_info and caption_info.is_chinese_label:
            # Perform OCR on the page
            ocr_result = await ocr_service.extract_label_from_page(
                page,
                pdf_path=report_path,
                enable_llm=enable_llm,
            )
            if ocr_result:
                results.append((caption_info, ocr_result))

    return results


def _extract_photo_captions(photo_pages: list) -> list[str]:
    """Extract photo captions from photo pages.

    Args:
        photo_pages: List of photo pages

    Returns:
        List of caption texts
    """
    captions = []

    for page in photo_pages:
        # Extract caption-like text
        lines = page.raw_text.split("\n")
        for line in lines:
            line = line.strip()
            # Look for lines that look like captions
            # (e.g., start with "图", "№", number, etc.)
            if line and any(line.startswith(prefix) for prefix in ["图", "№", "Plate", "Photo"]):
                captions.append(line)

    return captions


def _extract_sample_description_table(pdf_doc: PDFDocument) -> list[ComponentRow]:
    """Extract sample description table from parsed PDF.

    Args:
        pdf_doc: Parsed PDF document

    Returns:
        List of component rows
    """
    components: list[ComponentRow] = []

    header_aliases = {
        "sequence": {"序号"},
        "name": {"部件名称", "产品名称", "名称"},
        "model": {"规格型号", "型号规格", "型号", "规格"},
        "serial": {"序列号批号", "序列号/批号", "批号", "序列号", "SN", "LOT"},
        "production": {"生产日期", "MFG", "MFD"},
        "expiration": {"失效日期", "有效期至", "EXP"},
        "remark": {"备注"},
    }

    for page in pdf_doc.pages:
        if "样品描述" not in (page.raw_text or ""):
            continue
        for table in page.tables:
            if not table.headers:
                continue

            index_map: dict[str, int] = {}
            for idx, header in enumerate(table.headers):
                normalized = header.strip()
                for key, aliases in header_aliases.items():
                    if normalized in aliases:
                        index_map[key] = idx

            if "name" not in index_map:
                continue

            for row_idx, row in enumerate(table.rows):
                if row_idx == 0:
                    continue
                texts = [cell.text.strip() if cell and cell.text else "" for cell in row]
                name = texts[index_map["name"]] if index_map["name"] < len(texts) else ""
                if not name:
                    continue

                components.append(
                    ComponentRow(
                        sequence_number=texts[index_map["sequence"]] if "sequence" in index_map and index_map["sequence"] < len(texts) else "",
                        component_name=name,
                        model_spec=texts[index_map["model"]] if "model" in index_map and index_map["model"] < len(texts) else "",
                        serial_lot=texts[index_map["serial"]] if "serial" in index_map and index_map["serial"] < len(texts) else "",
                        production_date=texts[index_map["production"]] if "production" in index_map and index_map["production"] < len(texts) else "",
                        expiration_date=texts[index_map["expiration"]] if "expiration" in index_map and index_map["expiration"] < len(texts) else "",
                        remark=texts[index_map["remark"]] if "remark" in index_map and index_map["remark"] < len(texts) else "",
                    )
                )

    return components


def build_report_check_result(
    report_doc: ReportDocument,
    c01_results: list,
    c02_results: list,
    c03_result,
    c04_result,
    c05_results: list,
    c06_results: list,
    c07_results: list,
    c08_results: list,
    c09_result,
    c10_result,
    c11_result,
) -> dict[str, Any]:
    """Build comprehensive report check result.

    Args:
        report_doc: Parsed report document
        c01_results: C01 check results
        c02_results: C02 check results
        c03_result: C03 check result
        c04_result: C04 check result
        c05_results: C05 check results
        c06_results: C06 check results
        c07_results: C07 check results
        c08_results: C08 check results
        c09_result: C09 check result
        c10_result: C10 check result
        c11_result: C11 check result

    Returns:
        Comprehensive result dictionary
    """
    # Count statistics
    total_checks = 11  # C01-C11
    passed_checks = 0
    error_checks = 0
    warning_checks = 0

    # Count individual check results
    # C01
    c01_pass, c01_error, c01_warn = _count_check_status(c01_results)
    if c01_error > 0:
        error_checks += 1
    elif c01_warn > 0:
        warning_checks += 1
    else:
        passed_checks += 1

    # C02
    c02_pass, c02_error, c02_warn = _count_check_status(c02_results)
    if c02_error > 0:
        error_checks += 1
    elif c02_warn > 0:
        warning_checks += 1
    else:
        passed_checks += 1

    # C03
    if c03_result.status == "error":
        error_checks += 1
    elif c03_result.status == "warning":
        warning_checks += 1
    else:
        passed_checks += 1

    # C04
    if c04_result.status == "error":
        error_checks += 1
    elif c04_result.status == "warning":
        warning_checks += 1
    else:
        passed_checks += 1

    # C05
    c05_pass, c05_error, c05_warn = _count_check_status(c05_results)
    if c05_error > 0:
        error_checks += 1
    elif c05_warn > 0:
        warning_checks += 1
    else:
        passed_checks += 1

    # C06
    c06_pass, c06_error, c06_warn = _count_check_status(c06_results)
    if c06_error > 0:
        error_checks += 1
    elif c06_warn > 0:
        warning_checks += 1
    else:
        passed_checks += 1

    # C07
    if c07_results:
        error_checks += 1

    # C08
    if c08_results:
        error_checks += 1

    # C09
    if c09_result.status == "error":
        error_checks += 1
    elif c09_result.status == "warning":
        warning_checks += 1
    else:
        passed_checks += 1

    # C10
    if c10_result.status == "error":
        error_checks += 1
    elif c10_result.status == "warning":
        warning_checks += 1
    else:
        passed_checks += 1

    # C11
    if c11_result.status == "error":
        error_checks += 1
    elif c11_result.status == "warning":
        warning_checks += 1
    else:
        passed_checks += 1

    # Build result structure
    return {
        "summary": {
            "total_checks": total_checks,
            "passed": passed_checks,
            "errors": error_checks,
            "warnings": warning_checks,
            "overall_status": "pass" if error_checks == 0 else "error",
        },
        "checks": {
            "C01": {
                "name": "首页与第三页一致性",
                "status": "pass" if c01_error == 0 else "error",
                "results": [
                    {
                        "field_name": r.field_name,
                        "status": r.status,
                        "message": r.message,
                        "source_a": r.source_a,
                        "source_b": r.source_b,
                    }
                    for r in c01_results
                ],
            },
            "C02": {
                "name": "第三页扩展字段",
                "status": "pass" if c02_error == 0 else "error",
                "results": [
                    {
                        "field_name": r.field_name,
                        "status": r.status,
                        "message": r.message,
                        "source_a": r.source_a,
                        "source_b": r.source_b,
                    }
                    for r in c02_results
                ],
            },
            "C03": {
                "name": "生产日期格式与值",
                "status": c03_result.status,
                "message": c03_result.message,
            },
            "C04": {
                "name": "样品描述表格核对",
                "status": c04_result.status,
                "message": c04_result.message,
                "field_results": [
                    {
                        "component_name": r.component_name,
                        "field_name": r.field_name,
                        "status": r.status,
                        "message": r.message,
                        "source_a": r.source_a,
                        "source_b": r.source_b,
                    }
                    for r in c04_result.field_results
                ],
            },
            "C05": {
                "name": "照片覆盖性核对",
                "status": "pass" if c05_error == 0 else "error",
                "results": [
                    {
                        "component_name": r.component_name,
                        "status": r.status,
                        "message": r.message,
                        "matched_captions": r.matched_captions,
                    }
                    for r in c05_results
                ],
            },
            "C06": {
                "name": "中文标签覆盖核对",
                "status": "pass" if c06_error == 0 else "error",
                "results": [
                    {
                        "component_name": r.component_name,
                        "status": r.status,
                        "message": r.message,
                        "matched_captions": r.matched_captions,
                    }
                    for r in c06_results
                ],
            },
            "C07": {
                "name": "单项结论核对",
                "status": "pass" if len(c07_results) == 0 else "error",
                "error_count": len(c07_results),
                "results": [
                    {
                        "sequence_number": r.sequence_number,
                        "inspection_project": r.inspection_project,
                        "status": r.status,
                        "message": r.message,
                        "expected_conclusion": r.expected_conclusion,
                        "actual_conclusion": r.actual_conclusion,
                    }
                    for r in c07_results
                ],
            },
            "C08": {
                "name": "非空字段核对",
                "status": "pass" if len(c08_results) == 0 else "error",
                "error_count": len(c08_results),
                "results": [
                    {
                        "sequence_number": r.sequence_number,
                        "inspection_project": r.inspection_project,
                        "status": r.status,
                        "message": r.message,
                        "empty_fields": r.empty_fields,
                    }
                    for r in c08_results
                ],
            },
            "C09": {
                "name": "序号连续性核对",
                "status": c09_result.status,
                "message": c09_result.message,
                "details": {
                    "first_number": c09_result.first_number,
                    "last_number": c09_result.last_number,
                    "missing_numbers": c09_result.missing_numbers,
                    "duplicate_numbers": c09_result.duplicate_numbers,
                },
            },
            "C10": {
                "name": "续表标记核对",
                "status": c10_result.status,
                "message": c10_result.message,
                "details": {
                    "missing_markers": c10_result.missing_markers,
                    "extra_markers": c10_result.extra_markers,
                },
            },
            "C11": {
                "name": "页码连续性核对",
                "status": c11_result.status,
                "message": c11_result.message,
                "details": {
                    "total_pages_checked": len(c11_result.page_infos),
                    "missing_pages": c11_result.missing_pages,
                    "duplicate_pages": c11_result.duplicate_pages,
                    "total_inconsistent": c11_result.total_inconsistent,
                    "final_page_mismatch": c11_result.final_page_mismatch,
                },
            },
        },
        "report_info": {
            "total_inspection_items": report_doc.total_inspection_items,
            "has_third_page": report_doc.third_page_fields is not None,
        },
    }


import re
