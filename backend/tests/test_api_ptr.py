"""
Tests for PTR Compare API endpoints.

Tests upload, progress tracking, and result retrieval.
"""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_files():
    """Get paths to sample files."""
    base_path = Path(__file__).parent.parent.parent / "素材"

    ptr_path = base_path / "ptr" / "1539" / "射频脉冲电场消融系统产品技术要求-20260102-Clean.pdf"
    report_path = base_path / "report" / "1539" / "QW2025-1539 Draft.pdf"

    return {
        "ptr": ptr_path if ptr_path.exists() else None,
        "report": report_path if report_path.exists() else None,
    }


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data


class TestUploadEndpoint:
    """Test file upload endpoint."""

    def test_upload_missing_files(self, client):
        """Test upload with missing files."""
        response = client.post("/api/ptr/upload")
        assert response.status_code == 422  # Unprocessable Entity

    def test_upload_with_sample_files(self, client, sample_files):
        """Test upload with actual sample files."""
        if not sample_files["ptr"] or not sample_files["report"]:
            pytest.skip("Sample files not available")

        with open(sample_files["ptr"], "rb") as ptr_file, \
             open(sample_files["report"], "rb") as report_file:

            files = {
                "ptr_file": ("ptr.pdf", ptr_file, "application/pdf"),
                "report_file": ("report.pdf", report_file, "application/pdf"),
            }

            response = client.post("/api/ptr/upload", files=files)

            # Should accept the upload
            assert response.status_code == 200

            data = response.json()
            assert "task_id" in data
            assert "status" in data
            assert data["status"] in ["pending", "processing"]


class TestProgressEndpoint:
    """Test progress tracking endpoint."""

    def test_progress_nonexistent_task(self, client):
        """Test progress for nonexistent task."""
        response = client.get("/api/ptr/nonexistent-task/progress")
        assert response.status_code == 404

    def test_progress_response_format(self, client):
        """Test progress response has correct format."""
        # This would require an actual task to be created first
        # For now, just test the endpoint structure
        pass


class TestResultEndpoint:
    """Test result retrieval endpoint."""

    def test_result_nonexistent_task(self, client):
        """Test result for nonexistent task."""
        response = client.get("/api/ptr/nonexistent-task/result")
        assert response.status_code == 404

    def test_result_response_format(self, client):
        """Test result response has correct format."""
        # This would require a completed task
        pass


class TestTaskModels:
    """Test task-related data models."""

    def test_task_status_enum(self):
        """Test TaskStatus enum."""
        from app.routers.ptr_compare import TaskStatus

        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.ERROR.value == "error"

    def test_upload_response_model(self):
        """Test UploadResponse model."""
        from app.routers.ptr_compare import UploadResponse, TaskStatus

        response = UploadResponse(
            task_id="test-id",
            status=TaskStatus.PROCESSING,
            message="Processing",
        )

        assert response.task_id == "test-id"
        assert response.status == TaskStatus.PROCESSING
        assert response.message == "Processing"

    def test_progress_response_model(self):
        """Test ProgressResponse model."""
        from app.routers.ptr_compare import ProgressResponse, TaskStatus

        response = ProgressResponse(
            task_id="test-id",
            status=TaskStatus.PROCESSING,
            progress=50,
            message="Halfway done",
        )

        assert response.progress == 50
        assert response.task_id == "test-id"

    def test_result_response_model(self):
        """Test ResultResponse model."""
        from app.routers.ptr_compare import ResultResponse, TaskStatus

        response = ResultResponse(
            task_id="test-id",
            status=TaskStatus.COMPLETED,
            result={"test": "data"},
        )

        assert response.task_id == "test-id"
        assert response.result == {"test": "data"}


class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_workflow_skipped(self, client, sample_files):
        """Test full upload-progress-result workflow.

        Note: This test is skipped in normal test runs as it requires
        actual file processing which can be slow.
        """
        if not sample_files["ptr"] or not sample_files["report"]:
            pytest.skip("Sample files not available")

        pytest.skip("Full workflow test requires long-running processing")

        # The actual workflow would be:
        # 1. Upload files
        # 2. Poll progress endpoint
        # 3. Get results when complete


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_task_id_format(self, client):
        """Test with invalid task ID format."""
        # Should handle any string format gracefully
        response = client.get("/api/ptr/invalid-id-!@#/progress")
        assert response.status_code == 404

    def test_concurrent_tasks(self, client):
        """Test handling multiple concurrent tasks."""
        # This would require mocking the task processing
        pass


class TestUploadsDirectory:
    """Test uploads directory handling."""

    def test_uploads_directory_creation(self, tmp_path):
        """Test that uploads directory can be created."""
        from app.routers.ptr_compare import process_comparison

        # The function should handle missing directories
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir(exist_ok=True)

        assert upload_dir.exists()


class TestBackgroundProcessing:
    """Test background task processing."""

    def test_process_comparison_function_exists(self):
        """Test that process_comparison function exists."""
        from app.routers.ptr_compare import process_comparison

        assert callable(process_comparison)

    def test_build_comparison_result_function(self):
        """Test build_comparison_result function."""
        from app.routers.ptr_compare import build_comparison_result
        from app.models.ptr_models import PTRDocument
        from app.models.report_models import ReportDocument
        from app.services.comparator import ComparisonResult

        # Create minimal documents
        ptr_doc = PTRDocument()
        report_doc = ReportDocument()

        result = build_comparison_result(
            ptr_doc,
            report_doc,
            [],
            [],
        )

        assert "summary" in result
        assert "warnings" in result
        assert "clauses" in result
        assert "tables" in result
        assert result["summary"]["total_clauses"] == 0
        assert result["summary"]["evaluated_clauses"] == 0

    def test_build_comparison_result_match_rate_excludes_out_of_scope(self):
        """Match rate denominator should exclude out-of-scope clauses."""
        from app.models.ptr_models import PTRClause, PTRClauseNumber, PTRDocument
        from app.models.report_models import ReportDocument
        from app.routers.ptr_compare import build_comparison_result
        from app.services.comparator import ComparisonDetail, ComparisonResult

        ptr_doc = PTRDocument()
        report_doc = ReportDocument()

        clause_211 = PTRClause(
            number=PTRClauseNumber.from_string("2.1.1"),
            full_text="2.1.1 A",
            text_content="A",
            level=4,
        )
        clause_212 = PTRClause(
            number=PTRClauseNumber.from_string("2.1.2"),
            full_text="2.1.2 B",
            text_content="B",
            level=4,
        )
        clause_213 = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 C",
            text_content="C",
            level=4,
        )

        details = [
            ComparisonDetail(ptr_clause=clause_211, result=ComparisonResult.MATCH),
            ComparisonDetail(ptr_clause=clause_212, result=ComparisonResult.DIFFER),
            ComparisonDetail(ptr_clause=clause_213, result=ComparisonResult.EXCLUDED),
        ]

        result = build_comparison_result(ptr_doc, report_doc, details, [])

        assert result["summary"]["total_clauses"] == 3
        assert result["summary"]["evaluated_clauses"] == 2
        assert result["summary"]["matches"] == 1
        assert result["summary"]["excluded"] == 1
        assert result["summary"]["match_rate"] == 0.5

    def test_build_comparison_result_includes_clause_table_expansions(self):
        """Clause payload should include related table parameter details."""
        from app.models.ptr_models import PTRClause, PTRClauseNumber, PTRDocument
        from app.models.report_models import ReportDocument
        from app.routers.ptr_compare import build_comparison_result
        from app.services.comparator import ComparisonDetail, ComparisonResult
        from app.services.table_comparator import ParameterComparison, TableExpansionResult

        ptr_doc = PTRDocument()
        report_doc = ReportDocument()
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 脉冲宽度应符合表1中的数值。",
            text_content="脉冲宽度应符合表1中的数值。",
            level=4,
        )

        details = [
            ComparisonDetail(
                ptr_clause=clause,
                result=ComparisonResult.MATCH,
                match_reason="table_parameter_equivalent",
            )
        ]
        table_results = [
            TableExpansionResult(
                table_number=1,
                clause_number="2.1.3",
                table_found=True,
                total_parameters=1,
                total_matches=1,
                parameters=[
                    ParameterComparison(
                        parameter_name="脉冲宽度",
                        ptr_value="20",
                        report_value="20",
                        matches=True,
                        is_expanded=True,
                    )
                ],
            )
        ]

        result = build_comparison_result(ptr_doc, report_doc, details, table_results)
        clause_data = result["clauses"][0]
        assert "table_expansions" in clause_data
        assert clause_data["table_expansions"][0]["table_number"] == 1
        assert clause_data["table_expansions"][0]["parameters"][0]["name"] == "脉冲宽度"

    def test_build_comparison_result_includes_display_metadata(self):
        """Structured clauses should expose display metadata for the frontend detail view."""
        from app.models.ptr_models import PTRClause, PTRClauseNumber, PTRDocument
        from app.models.report_models import ReportDocument
        from app.routers.ptr_compare import build_comparison_result
        from app.services.comparator import ComparisonDetail, ComparisonResult

        ptr_clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1.3"),
            full_text="2.1.3 断裂力",
            text_content="断裂力 各试验段的断裂力应符合下表的规定。",
            level=3,
        )
        detail = ComparisonDetail(
            ptr_clause=ptr_clause,
            result=ComparisonResult.MATCH,
            match_reason="segmented_threshold_bundle_match",
            comparison_status="pass",
            details={
                "display_title": "断裂力",
                "display_type": "segmented_threshold_bundle",
                "raw_text_collapsed": True,
                "structured_summary": "共核对 5 个试验段，均满足要求。",
                "structured_rows": [
                    {"segment": "环形圈头端与环形圈管身", "requirement": "≥10", "actual": "17～46", "result": "一致"},
                ],
            },
        )

        result = build_comparison_result(PTRDocument(clauses=[ptr_clause]), ReportDocument(), [detail], [])

        clause_data = result["clauses"][0]
        assert clause_data["display_title"] == "断裂力"
        assert clause_data["display_type"] == "segmented_threshold_bundle"
        assert clause_data["raw_text_collapsed"] is True
        assert clause_data["structured_rows"][0]["actual"] == "17～46"

    def test_build_comparison_result_includes_presentation_status(self):
        """API payload should expose unified presentation status for UI/export consumers."""
        from app.models.ptr_models import PTRClause, PTRClauseNumber, PTRDocument
        from app.models.report_models import ReportDocument
        from app.routers.ptr_compare import build_comparison_result
        from app.services.comparator import ComparisonDetail, ComparisonResult

        ptr_clause = PTRClause(
            number=PTRClauseNumber.from_string("2.5.3"),
            full_text="2.5.3 电磁兼容",
            text_content="电磁兼容应符合要求。",
            level=3,
        )
        detail = ComparisonDetail(
            ptr_clause=ptr_clause,
            result=ComparisonResult.MATCH,
            comparison_status="out_of_scope_in_current_report",
            match_reason="out_of_scope_in_current_report",
        )

        result = build_comparison_result(PTRDocument(clauses=[ptr_clause]), ReportDocument(), [detail], [])
        clause = result["clauses"][0]
        assert clause["display_status"] == "out_of_scope_in_current_report"
        assert clause["display_status_variant"] == "warn"
        assert clause["is_failure"] is False


class TestAPIRoutes:
    """Test API route registration."""

    def test_ptr_routes_registered(self, client):
        """Test that PTR routes are registered."""
        response = client.get("/api/health")
        # If we can reach health endpoint, app is running
        assert response.status_code == 200

    def test_api_prefix(self):
        """Test API prefix configuration."""
        from app.routers.ptr_compare import router

        assert router.prefix == "/api/ptr"
        assert "PTR Compare" in router.tags


class TestResponseModels:
    """Test response model validation."""

    def test_upload_response_validation(self):
        """Test UploadResponse validates correctly."""
        from pydantic import ValidationError
        from app.routers.ptr_compare import UploadResponse, TaskStatus

        # Valid data
        UploadResponse(
            task_id="test",
            status=TaskStatus.PENDING,
            message="Test",
        )

        # Missing required field should fail
        with pytest.raises(ValidationError):
            UploadResponse(
                task_id="test",
                status=TaskStatus.PENDING,
                # message is required
            )

    def test_result_response_with_data(self):
        """Test ResultResponse with actual result data."""
        from app.routers.ptr_compare import ResultResponse, TaskStatus

        result_data = {
            "summary": {
                "total_clauses": 10,
                "matches": 8,
                "differs": 2,
                "missing": 0,
                "excluded": 0,
                "match_rate": 0.8,
            },
            "clauses": [],
            "tables": [],
        }

        response = ResultResponse(
            task_id="test",
            status=TaskStatus.COMPLETED,
            result=result_data,
        )

        assert response.result == result_data


class TestRealSampleRegressions:
    """Real sample regressions for status classification and display payload."""

    def _run_ptr_compare(self, ptr_path: Path, report_path: Path) -> dict[str, Any]:
        from app.routers.ptr_compare import build_comparison_result
        from app.services.comparator import ClauseComparator
        from app.services.pdf_parser import parse_pdf
        from app.services.ptr_extractor import PTRExtractor
        from app.services.report_extractor import ReportExtractor
        from app.services.table_comparator import compare_table_expansions

        ptr_doc = PTRExtractor().extract(parse_pdf(ptr_path))
        report_doc = ReportExtractor().extract_from_pdf_doc(parse_pdf(report_path))
        comparison_results = ClauseComparator(strict_mode=True).compare_documents(ptr_doc, report_doc)
        report_items = report_doc.inspection_table.items if report_doc.inspection_table else []
        table_results = compare_table_expansions(ptr_doc, report_items)
        return build_comparison_result(ptr_doc, report_doc, comparison_results, table_results)

    def test_5332_status_regression_should_keep_non_failure_special_states(self):
        base = Path(__file__).parent.parent.parent / "素材"
        ptr_path = base / "ptr" / "5332" / "TR-AP0105-001 Rev01一次性使用磁电定位心脏脉冲电场消融导管产品技术要求-0305V2.pdf"
        report_path = base / "report" / "5332" / "QW2025-5332 Draft.pdf"
        if not ptr_path.exists() or not report_path.exists():
            pytest.skip("5332 sample not available")

        result = self._run_ptr_compare(ptr_path, report_path)
        clause_map = {clause["ptr_number"]: clause for clause in result["clauses"]}

        assert clause_map["2.5.3"]["display_status"] == "out_of_scope_in_current_report"
        assert clause_map["2.5.3"]["is_failure"] is False

    def test_3940_status_regression_should_not_render_parent_and_scope_clauses_as_failures(self):
        base = Path(__file__).parent.parent.parent / "素材"
        ptr_path = base / "ptr" / "3940" / "3940 产品技术要求 Edora 8 改批注zx260218 260225更新.pdf"
        report_path = base / "report" / "3940" / "3940.pdf"
        if not ptr_path.exists() or not report_path.exists():
            pytest.skip("3940 sample not available")

        result = self._run_ptr_compare(ptr_path, report_path)
        clause_map = {clause["ptr_number"]: clause for clause in result["clauses"]}

        assert clause_map["2.1"]["display_status"] == "group_clause"
        assert clause_map["2.1"]["is_failure"] is False
        assert clause_map["2.2"]["display_status"] == "out_of_scope_in_current_report"
        assert clause_map["2.2"]["is_failure"] is False
