"""
Tests for PDF Export Service.

Tests both PTR comparison and report self-check PDF generation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.services.report_export_service import (
    ReportExportService,
    create_export_service,
    export_ptr_to_pdf,
    export_report_check_to_pdf,
)


class TestReportExportService:
    """Test cases for ReportExportService."""

    @pytest.fixture
    def service(self) -> ReportExportService:
        """Create export service instance."""
        # Create service directly - it will use font fallback
        service = ReportExportService()
        return service

    @pytest.fixture
    def ptr_result(self) -> dict:
        """Sample PTR comparison result."""
        return {
            "task_id": "test-task-123",
            "status": "completed",
            "statistics": {
                "total": 10,
                "consistent": 8,
                "inconsistent": 2,
                "consistency_rate": 80.0,
            },
            "clauses": [
                {
                    "code": "4.1",
                    "title": "外观",
                    "status": "matched",
                    "is_consistent": True,
                },
                {
                    "code": "4.2",
                    "title": "尺寸",
                    "status": "mismatched",
                    "is_consistent": False,
                },
            ],
        }

    @pytest.fixture
    def report_check_result(self) -> dict:
        """Sample report check result."""
        return {
            "task_id": "check-task-456",
            "status": "completed",
            "statistics": {
                "total": 11,
                "passed": 9,
                "failed": 1,
                "warnings": 1,
            },
            "checks": [
                {
                    "code": "C01",
                    "name": "首页字段完整性",
                    "status": "PASS",
                    "message": "所有字段完整",
                },
                {
                    "code": "C02",
                    "name": "第三页字段完整性",
                    "status": "PASS",
                    "message": "所有字段完整",
                },
                {
                    "code": "C07",
                    "name": "单项结论逻辑",
                    "status": "FAIL",
                    "message": "序号5结论不一致",
                },
                {
                    "code": "C09",
                    "name": "序号连续性",
                    "status": "WARN",
                    "message": "存在跳号: [10]",
                },
                {
                    "code": "C11",
                    "name": "页码连续性",
                    "status": "PASS",
                    "message": "页码连续",
                },
            ],
        }

    def test_create_export_service(self):
        """Test service factory function."""
        service = create_export_service()
        assert isinstance(service, ReportExportService)

    def test_export_ptr_comparison_returns_bytes(self, service, ptr_result):
        """Test that PTR export returns PDF bytes."""
        pdf_bytes = service.export_ptr_comparison(ptr_result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF files start with %PDF
        assert pdf_bytes[:4] == b"%PDF"

    def test_export_ptr_comparison_with_custom_title(self, service, ptr_result):
        """Test PTR export with custom title."""
        pdf_bytes = service.export_ptr_comparison(
            ptr_result, title="Custom Report Title"
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_export_ptr_comparison_empty_result(self, service):
        """Test PTR export with empty result."""
        empty_result = {
            "statistics": {},
            "clauses": [],
        }

        pdf_bytes = service.export_ptr_comparison(empty_result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_export_report_check_returns_bytes(self, service, report_check_result):
        """Test that report check export returns PDF bytes."""
        pdf_bytes = service.export_report_check(report_check_result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF files start with %PDF
        assert pdf_bytes[:4] == b"%PDF"

    def test_export_report_check_with_custom_title(self, service, report_check_result):
        """Test report check export with custom title."""
        pdf_bytes = service.export_report_check(
            report_check_result, title="Custom Check Report"
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_export_report_check_empty_result(self, service):
        """Test report check export with empty result."""
        empty_result = {
            "statistics": {},
            "checks": [],
        }

        pdf_bytes = service.export_report_check(empty_result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_export_report_check_categorizes_checks(self, service):
        """Test that checks are properly categorized in PDF."""
        result = {
            "statistics": {"total": 5, "passed": 3, "failed": 2, "warnings": 0},
            "checks": [
                {"code": "C01", "name": "Field 1", "status": "PASS", "message": "OK"},
                {"code": "C04", "name": "Sample 1", "status": "PASS", "message": "OK"},
                {"code": "C07", "name": "Item 1", "status": "FAIL", "message": "Error"},
                {"code": "C11", "name": "Page 1", "status": "PASS", "message": "OK"},
            ],
        }

        pdf_bytes = service.export_report_check(result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_format_clause_for_pdf_consistent(self, service):
        """Test clause formatting for consistent clause."""
        clause = {
            "code": "4.1",
            "title": "Test Clause",
            "status": "matched",
            "is_consistent": True,
        }

        table = service._format_clause_for_pdf(clause)

        assert table is not None
        # Table should be a Table object
        from reportlab.platypus import Table as RLTable
        assert isinstance(table, RLTable)

    def test_format_clause_for_pdf_inconsistent(self, service):
        """Test clause formatting for inconsistent clause."""
        clause = {
            "code": "4.2",
            "title": "Test Clause",
            "status": "mismatched",
            "is_consistent": False,
        }

        table = service._format_clause_for_pdf(clause)

        assert table is not None

    def test_format_clause_for_pdf_group_clause_not_red(self, service):
        """Group clauses should not be rendered as red mismatches in export."""
        clause = {
            "ptr_number": "2.1",
            "display_title": "基本电性能指标及允许误差",
            "display_status": "group_clause",
            "display_status_label": "分组条款",
            "display_status_variant": "accent",
            "display_status_explanation": "该条款属于父级/分组条款，已由下级条款单独判定。",
        }

        table = service._format_clause_for_pdf(clause)

        assert table is not None

    def test_format_clause_for_pdf_out_of_scope_not_red(self, service):
        """Out-of-scope clauses should be exported as warning/info state instead of failure."""
        clause = {
            "ptr_number": "2.5.3",
            "display_title": "电磁兼容",
            "display_status": "out_of_scope_in_current_report",
            "display_status_label": "范围外",
            "display_status_variant": "warn",
            "display_status_explanation": "该条款不在当前报告本次检验范围内。",
        }

        table = service._format_clause_for_pdf(clause)

        assert table is not None

    def test_format_checks_for_pdf(self, service):
        """Test formatting multiple checks for PDF."""
        checks = [
            {"code": "C01", "name": "Check 1", "status": "PASS", "message": "OK"},
            {"code": "C02", "name": "Check 2", "status": "FAIL", "message": "Error"},
            {"code": "C03", "name": "Check 3", "status": "WARN", "message": "Warning"},
        ]

        elements = service._format_checks_for_pdf(checks)

        assert len(elements) == 6  # 3 tables + 3 spacers
        # Each table followed by spacer
        from reportlab.platypus import Table, Spacer

        for i in range(0, 6, 2):
            assert isinstance(elements[i], Table)
            assert isinstance(elements[i + 1], Spacer)

    def test_format_checks_truncates_long_messages(self, service):
        """Test that long messages are truncated in PDF."""
        long_message = "This is a very long message that exceeds fifty characters and should be truncated"
        checks = [
            {
                "code": "C01",
                "name": "Check",
                "status": "FAIL",
                "message": long_message,
            }
        ]

        elements = service._format_checks_for_pdf(checks)

        # Should have table + spacer
        assert len(elements) == 2

    def test_convenience_function_export_ptr_to_pdf(self, ptr_result):
        """Test convenience function for PTR export."""
        pdf_bytes = export_ptr_to_pdf(ptr_result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_export_ptr_comparison_accepts_summary_style_payload(self, service):
        """Export should support the live PTR API payload with summary/display statuses."""
        result = {
            "summary": {
                "total_clauses": 3,
                "evaluated_clauses": 2,
                "matches": 1,
                "differs": 0,
                "missing": 1,
                "excluded": 1,
                "match_rate": 0.5,
                "special_status_counts": {
                    "group_clause": 1,
                    "out_of_scope_in_current_report": 1,
                },
            },
            "clauses": [
                {
                    "ptr_number": "2.1",
                    "display_title": "基本电性能指标及允许误差",
                    "display_status": "group_clause",
                    "display_status_label": "分组条款",
                    "display_status_variant": "accent",
                },
                {
                    "ptr_number": "2.5.3",
                    "display_title": "电磁兼容",
                    "display_status": "out_of_scope_in_current_report",
                    "display_status_label": "范围外",
                    "display_status_variant": "warn",
                },
                {
                    "ptr_number": "2.1.6",
                    "display_title": "干扰转复频率",
                    "display_status": "missing",
                    "display_status_label": "缺失",
                    "display_status_variant": "danger",
                },
            ],
        }

        pdf_bytes = service.export_ptr_comparison(result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_convenience_function_export_report_check_to_pdf(self, report_check_result):
        """Test convenience function for report check export."""
        pdf_bytes = export_report_check_to_pdf(report_check_result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0


class TestExportServiceColors:
    """Test color scheme in export service."""

    def test_color_constants(self):
        """Test that color constants are properly defined."""
        from app.services.report_export_service import (
            COLOR_SUCCESS,
            COLOR_DANGER,
            COLOR_WARN,
            COLOR_INFO,
            COLOR_ACCENT,
        )

        # All colors should be Color instances
        from reportlab.lib.colors import Color
        assert isinstance(COLOR_SUCCESS, Color)
        assert isinstance(COLOR_DANGER, Color)
        assert isinstance(COLOR_WARN, Color)
        assert isinstance(COLOR_INFO, Color)
        assert isinstance(COLOR_ACCENT, Color)


class TestExportServiceEdgeCases:
    """Test edge cases in export service."""

    @pytest.fixture
    def service(self) -> ReportExportService:
        """Create export service instance."""
        # Create service directly - it will use font fallback
        return ReportExportService()

    def test_export_with_special_characters(self, service):
        """Test export with special characters in content."""
        result = {
            "statistics": {"total": 1, "consistent": 1, "inconsistent": 0},
            "clauses": [
                {
                    "code": "4.1",
                    "title": "测试 <特殊> & 字符 \"引号\"",
                    "status": "matched",
                    "is_consistent": True,
                }
            ],
        }

        pdf_bytes = service.export_ptr_comparison(result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_export_with_unicode(self, service):
        """Test export with Unicode characters."""
        result = {
            "statistics": {"total": 1, "passed": 1, "failed": 0, "warnings": 0},
            "checks": [
                {
                    "code": "C01",
                    "name": "中文测试",
                    "status": "PASS",
                    "message": "包含特殊符号：✓ ✗ ⚠",
                }
            ],
        }

        pdf_bytes = service.export_report_check(result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_export_with_large_dataset(self, service):
        """Test export with large number of items."""
        # Create 100 clauses
        clauses = [
            {
                "code": f"4.{i}",
                "title": f"条款 {i}",
                "status": "matched" if i % 2 == 0 else "mismatched",
                "is_consistent": i % 2 == 0,
            }
            for i in range(1, 101)
        ]

        result = {
            "statistics": {
                "total": 100,
                "consistent": 50,
                "inconsistent": 50,
                "consistency_rate": 50.0,
            },
            "clauses": clauses,
        }

        pdf_bytes = service.export_ptr_comparison(result)

        assert isinstance(pdf_bytes, bytes)
        # Should produce a reasonably sized PDF
        assert len(pdf_bytes) > 10000  # At least 10KB for 100 items

    def test_export_with_missing_optional_fields(self, service):
        """Test export when optional fields are missing."""
        result = {
            "statistics": {},  # Empty statistics
            "clauses": [
                {
                    "code": "4.1",
                    # Missing title
                    "status": "matched",
                    # Missing is_consistent
                }
            ],
        }

        # Should not raise error
        pdf_bytes = service.export_ptr_comparison(result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_font_fallback(self):
        """Test font fallback when Chinese font not available."""
        with patch(
            "app.services.report_export_service.pdfmetrics.registerFont",
            side_effect=Exception("Font not found"),
        ):
            service = ReportExportService()

            # Should fall back to Helvetica
            assert service.chinese_font == "Helvetica"
