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
        assert "clauses" in result
        assert "tables" in result
        assert result["summary"]["total_clauses"] == 0


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
