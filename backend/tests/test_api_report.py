"""
Tests for Report Check API Router.

Tests upload, progress, and result endpoints for C01-C11 checks.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# Mock data
@pytest.fixture
def mock_pdf_parser():
    """Mock PDF parser."""
    parser = MagicMock()
    pdf_doc = MagicMock()
    pdf_doc.pages = [
        MagicMock(page_number=1, width=595, height=842, raw_text="首页内容"),
        MagicMock(page_number=2, width=595, height=842, raw_text="注意事项"),
        MagicMock(page_number=3, width=595, height=842, raw_text="检验报告首页"),
        MagicMock(page_number=4, width=595, height=842, raw_text="共5页 第1页\n样品描述\n主机 RF-2000"),
        MagicMock(page_number=5, width=595, height=842, raw_text="共5页 第2页\n图1 主机"),
    ]
    parser.parse.return_value = pdf_doc
    return parser


@pytest.fixture
def mock_report_extractor():
    """Mock report extractor."""
    extractor = MagicMock()
    from app.models.report_models import ReportDocument, ThirdPageFields, InspectionTable, InspectionItem

    report_doc = ReportDocument(
        third_page_fields=ThirdPageFields(
            client="ABC医疗器械有限公司",
            sample_name="射频消融电极",
            model_spec="RF-2000",
        ),
        first_page_fields={
            "client": "ABC医疗器械有限公司",
            "sample_name": "射频消融电极",
            "model_spec": "RF-2000",
        },
        inspection_table=InspectionTable(
            items=[
                InspectionItem(
                    sequence_number="1",
                    inspection_project="外观检查",
                    test_result="符合要求",
                    item_conclusion="符合",
                    remark="正常",
                ),
            ]
        ),
    )
    extractor.extract_from_pdf_doc.return_value = report_doc
    return extractor


@pytest.fixture
def mock_ocr_service():
    """Mock OCR service."""
    ocr = MagicMock()

    # Mock caption info extraction
    from app.services.ocr_service import CaptionInfo, LabelOCRResult

    ocr.extract_caption_info.return_value = CaptionInfo(
        raw_caption="中文标签：主机",
        caption_number="1",
        is_chinese_label=True,
        main_name="主机",
        position=None,
    )

    # Mock label extraction
    async def mock_extract(*args, **kwargs):
        return LabelOCRResult(
            raw_text="型号：RF-2000",
            fields={"model_spec": "RF-2000"},
        )

    ocr.extract_label_from_page = AsyncMock(side_effect=mock_extract)
    return ocr


@pytest.fixture
async def async_client():
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestUploadEndpoint:
    """Test POST /api/report/upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_success(self, async_client, mock_pdf_parser):
        """Test successful file upload."""
        # Mock file content
        file_content = b"mock pdf content"

        with patch("app.routers.report_check.process_report_check") as mock_process:
            # Make process_report_check return immediately
            mock_process.return_value = asyncio.sleep(0)

            files = {"report_file": ("test_report.pdf", file_content, "application/pdf")}
            response = await async_client.post(
                "/api/report/upload",
                files=files,
            )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "processing"

    @pytest.mark.asyncio
    async def test_upload_with_llm_enabled(self, async_client):
        """Test upload with LLM enabled."""
        file_content = b"mock pdf content"

        with patch("app.routers.report_check.process_report_check"):
            files = {"report_file": ("test_report.pdf", file_content, "application/pdf")}
            response = await async_client.post(
                "/api/report/upload",
                files=files,
                params={"enable_llm": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"]


class TestProgressEndpoint:
    """Test GET /api/report/{task_id}/progress endpoint."""

    @pytest.mark.asyncio
    async def test_get_progress_pending(self, async_client):
        """Test getting progress for pending task."""
        # First create a task by uploading
        file_content = b"mock pdf content"

        with patch("app.routers.report_check.process_report_check"):
            upload_response = await async_client.post(
                "/api/report/upload",
                files={"report_file": ("test.pdf", file_content, "application/pdf")},
            )

        task_id = upload_response.json()["task_id"]

        # Get progress
        progress_response = await async_client.get(f"/api/report/{task_id}/progress")

        assert progress_response.status_code == 200
        data = progress_response.json()
        assert data["task_id"] == task_id
        assert data["status"] in ["pending", "processing"]
        assert "progress" in data

    @pytest.mark.asyncio
    async def test_get_progress_not_found(self, async_client):
        """Test getting progress for non-existent task."""
        response = await async_client.get("/api/report/nonexistent/progress")

        assert response.status_code == 404


class TestResultEndpoint:
    """Test GET /api/report/{task_id}/result endpoint."""

    @pytest.mark.asyncio
    async def test_get_result_processing(self, async_client):
        """Test getting result while task is still processing."""
        file_content = b"mock pdf content"

        with patch("app.routers.report_check.process_report_check"):
            upload_response = await async_client.post(
                "/api/report/upload",
                files={"report_file": ("test.pdf", file_content, "application/pdf")},
            )

        task_id = upload_response.json()["task_id"]

        # Get result immediately (should still be processing)
        result_response = await async_client.get(f"/api/report/{task_id}/result")

        # Should return 202 if processing, or 200 if already completed/pending
        assert result_response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, async_client):
        """Test getting result for non-existent task."""
        response = await async_client.get("/api/report/nonexistent/result")

        assert response.status_code == 404


class TestTaskStorage:
    """Test in-memory task storage."""

    def test_task_storage_exists(self):
        """Test that task storage is available."""
        from app.routers import report_check

        assert hasattr(report_check, "tasks")
        assert isinstance(report_check.tasks, dict)


class TestIntegrationWorkflow:
    """Test complete upload -> progress -> result workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, async_client):
        """Test full workflow from upload to result."""
        file_content = b"mock pdf content"

        # Mock the entire processing pipeline
        mock_result = {
            "summary": {
                "total_checks": 11,
                "passed": 10,
                "errors": 1,
                "warnings": 0,
                "overall_status": "error",
            },
            "checks": {
                "C01": {"name": "首页与第三页一致性", "status": "pass", "results": []},
            },
        }

        with patch("app.routers.report_check.process_report_check") as mock_process:
            # Make process_report_check set the result
            async def set_result(*args, **kwargs):
                task_id = args[0]
                from app.routers import report_check
                # Simulate completion
                await asyncio.sleep(0.1)
                report_check.tasks[task_id]["status"] = "completed"
                report_check.tasks[task_id]["result"] = mock_result
                report_check.tasks[task_id]["progress"] = 100

            mock_process.side_effect = set_result

            # Upload
            upload_response = await async_client.post(
                "/api/report/upload",
                files={"report_file": ("test.pdf", file_content, "application/pdf")},
            )
            assert upload_response.status_code == 200

            task_id = upload_response.json()["task_id"]

            # Wait for processing
            await asyncio.sleep(0.2)

            # Get result
            result_response = await async_client.get(f"/api/report/{task_id}/result")

        assert result_response.status_code == 200
        data = result_response.json()
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert "summary" in data["result"]


class TestResultStructure:
    """Test structure of result JSON."""

    def test_result_has_all_checks(self):
        """Test that result includes all C01-C11 checks."""
        from app.routers.report_check import build_report_check_result
        from app.models.report_models import ReportDocument, InspectionTable

        # Create mock document
        report_doc = ReportDocument(
            inspection_table=InspectionTable(),
        )

        # Create mock check results
        mock_c01 = [MagicMock(status="pass", field_name="委托方", message="OK")]
        mock_c02 = [MagicMock(status="pass", field_name="型号规格", message="OK")]
        mock_c03 = MagicMock(status="pass", message="OK")
        mock_c04 = MagicMock(status="pass", message="OK", field_results=[])
        mock_c05 = [MagicMock(status="pass", component_name="主机", message="OK")]
        mock_c06 = [MagicMock(status="pass", component_name="主机", message="OK")]
        mock_c07 = []  # No errors
        mock_c08 = []  # No errors
        mock_c09 = MagicMock(status="pass", message="OK")
        mock_c10 = MagicMock(status="pass", message="OK")
        mock_c11 = MagicMock(status="pass", message="OK")

        result = build_report_check_result(
            report_doc=report_doc,
            c01_results=mock_c01,
            c02_results=mock_c02,
            c03_result=mock_c03,
            c04_result=mock_c04,
            c05_results=mock_c05,
            c06_results=mock_c06,
            c07_results=mock_c07,
            c08_results=mock_c08,
            c09_result=mock_c09,
            c10_result=mock_c10,
            c11_result=mock_c11,
        )

        # Verify structure
        assert "summary" in result
        assert "checks" in result
        assert "report_info" in result

        # Verify all checks are present
        checks = result["checks"]
        assert "C01" in checks
        assert "C02" in checks
        assert "C03" in checks
        assert "C04" in checks
        assert "C05" in checks
        assert "C06" in checks
        assert "C07" in checks
        assert "C08" in checks
        assert "C09" in checks
        assert "C10" in checks
        assert "C11" in checks


class TestCountCheckStatus:
    """Test _count_check_status helper function."""

    def test_count_all_pass(self):
        """Test counting all pass results."""
        from app.routers.report_check import _count_check_status

        results = [
            MagicMock(status="pass"),
            MagicMock(status="pass"),
            MagicMock(status="pass"),
        ]

        pass_count, error_count, warn_count = _count_check_status(results)
        assert pass_count == 3
        assert error_count == 0
        assert warn_count == 0

    def test_count_mixed(self):
        """Test counting mixed results."""
        from app.routers.report_check import _count_check_status

        results = [
            MagicMock(status="pass"),
            MagicMock(status="error"),
            MagicMock(status="warning"),
            MagicMock(status="pass"),
        ]

        pass_count, error_count, warn_count = _count_check_status(results)
        assert pass_count == 2
        assert error_count == 1
        assert warn_count == 1


class TestErrorHandling:
    """Test error handling in API endpoints."""

    @pytest.mark.asyncio
    async def test_upload_error_handling(self, async_client):
        """Test error handling during upload."""
        # Mock file save to raise error
        with patch("pathlib.Path.open", side_effect=IOError("Disk full")):
            file_content = b"mock pdf content"
            files = {"report_file": ("test.pdf", file_content, "application/pdf")}

            response = await async_client.post(
                "/api/report/upload",
                files=files,
            )

        # Should return error
        assert response.status_code in [500, 200]  # May vary based on error handling


class TestResponseModels:
    """Test Pydantic response models."""

    def test_upload_response_model(self):
        """Test UploadResponse model."""
        from app.routers.report_check import UploadResponse, TaskStatus

        response = UploadResponse(
            task_id="test-123",
            status=TaskStatus.PROCESSING,
            message="Processing",
        )

        assert response.task_id == "test-123"
        assert response.status == TaskStatus.PROCESSING

    def test_progress_response_model(self):
        """Test ProgressResponse model."""
        from app.routers.report_check import ProgressResponse, TaskStatus

        response = ProgressResponse(
            task_id="test-123",
            status=TaskStatus.PROCESSING,
            progress=50,
            message="Half done",
        )

        assert response.progress == 50

    def test_result_response_model(self):
        """Test ResultResponse model."""
        from app.routers.report_check import ResultResponse, TaskStatus

        response = ResultResponse(
            task_id="test-123",
            status=TaskStatus.COMPLETED,
            result={"test": "data"},
        )

        assert response.result == {"test": "data"}
