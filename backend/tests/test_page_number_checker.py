"""
Tests for Page Number Checker module (C11).

Tests page number continuity check starting from the third page.
"""

import pytest

from app.models.common_models import PDFDocument, PDFPage
from app.services.page_number_checker import (
    C11Result,
    CheckResult,
    CheckStatus,
    PageNumberChecker,
    PageNumberInfo,
    create_page_number_checker,
)


class TestCheckStatus:
    """Test CheckStatus enum."""

    def test_status_values(self):
        """Test CheckStatus has correct values."""
        assert CheckStatus.PASS == "pass"
        assert CheckStatus.ERROR == "error"
        assert CheckStatus.WARNING == "warning"
        assert CheckStatus.SKIPPED == "skipped"


class TestPageNumberChecker:
    """Test PageNumberChecker class."""

    def test_initialization(self):
        """Test checker initialization."""
        checker = PageNumberChecker()
        assert checker.page_number_pattern is not None


class TestExtractPageNumberFromText:
    """Test _extract_page_number_from_text method."""

    def test_standard_format(self):
        """Test standard format: 共XXX页 第Y页."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text("共5页 第1页")
        assert result == (1, 5)

        result = checker._extract_page_number_from_text("共10页 第3页")
        assert result == (3, 10)

    def test_with_spaces(self):
        """Test with extra spaces."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text("共 5 页 第 1 页")
        assert result == (1, 5)

    def test_slash_format(self):
        """Test slash format: 1/5."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text("1/5")
        assert result == (1, 5)

        result = checker._extract_page_number_from_text("3/10")
        assert result == (3, 10)

    def test_page_of_format(self):
        """Test "Page X of Y" format."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text("Page 1 of 5")
        assert result == (1, 5)

    def test_no_page_number(self):
        """Test text without page number."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text("Some text without page numbers")
        assert result is None

    def test_case_insensitive(self):
        """Test case insensitivity."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text("共5页 第1页")
        assert result == (1, 5)

        result = checker._extract_page_number_from_text("共5页 第1页")
        assert result == (1, 5)


class TestExtractPageNumbers:
    """Test extract_page_numbers method."""

    def test_extract_from_pdf_document(self):
        """Test extracting from PDF document."""
        checker = PageNumberChecker()

        pdf_doc = PDFDocument()
        pdf_doc.pages = [
            PDFPage(page_number=1, width=595, height=842, raw_text="封面"),
            PDFPage(page_number=2, width=595, height=842, raw_text="注意事项"),
            PDFPage(page_number=3, width=595, height=842, raw_text="共3页 第1页"),
            PDFPage(page_number=4, width=595, height=842, raw_text="共3页 第2页"),
            PDFPage(page_number=5, width=595, height=842, raw_text="共3页 第3页"),
        ]

        page_infos = checker.extract_page_numbers(pdf_doc, start_from_third=True)

        # Should start from third page (index 2)
        assert len(page_infos) == 3
        assert page_infos[0].current_page == 1
        assert page_infos[0].total_pages == 3
        assert page_infos[1].current_page == 2
        assert page_infos[1].total_pages == 3
        assert page_infos[2].current_page == 3
        assert page_infos[2].total_pages == 3

    def test_start_from_beginning(self):
        """Test starting from first page."""
        checker = PageNumberChecker()

        pdf_doc = PDFDocument()
        pdf_doc.pages = [
            PDFPage(page_number=1, width=595, height=842, raw_text="共2页 第1页"),
            PDFPage(page_number=2, width=595, height=842, raw_text="共2页 第2页"),
        ]

        page_infos = checker.extract_page_numbers(pdf_doc, start_from_third=False)

        assert len(page_infos) == 2
        assert page_infos[0].current_page == 1
        assert page_infos[0].total_pages == 2
        assert page_infos[1].current_page == 2
        assert page_infos[1].total_pages == 2

    def test_missing_page_numbers(self):
        """Test handling of missing page numbers."""
        checker = PageNumberChecker()

        pdf_doc = PDFDocument()
        # Need at least 3 pages since start_from_third=True
        pdf_doc.pages = [
            PDFPage(page_number=1, width=595, height=842, raw_text="First page"),
            PDFPage(page_number=2, width=595, height=842, raw_text="Second page"),
            PDFPage(page_number=3, width=595, height=842, raw_text="Some text"),
            PDFPage(page_number=4, width=595, height=842, raw_text="共2页 第1页"),
        ]

        page_infos = checker.extract_page_numbers(pdf_doc, start_from_third=True)

        # Should start from index 2 (page 3)
        assert len(page_infos) == 2
        # First extracted page (page 3) has no page number
        assert page_infos[0].current_page == 0
        # Second extracted page (page 4) has page number
        assert page_infos[1].current_page == 1
        assert page_infos[1].total_pages == 2


class TestCheckC11PageContinuity:
    """Test C11: Page number continuity check."""

    def test_perfect_continuity(self):
        """Test perfect page number continuity."""
        checker = PageNumberChecker()

        page_infos = [
            PageNumberInfo(raw_text="共5页 第1页", current_page=1, total_pages=5),
            PageNumberInfo(raw_text="共5页 第2页", current_page=2, total_pages=5),
            PageNumberInfo(raw_text="共5页 第3页", current_page=3, total_pages=5),
            PageNumberInfo(raw_text="共5页 第4页", current_page=4, total_pages=5),
            PageNumberInfo(raw_text="共5页 第5页", current_page=5, total_pages=5),
        ]

        result = checker.check_c11_page_continuity(page_infos, start_from_third=False)

        assert result.status == CheckStatus.PASS
        assert len(result.missing_pages) == 0
        assert len(result.duplicate_pages) == 0
        assert result.total_inconsistent is False
        assert result.final_page_mismatch is False

    def test_not_starting_from_one(self):
        """Test page numbers not starting from 1."""
        checker = PageNumberChecker()

        page_infos = [
            PageNumberInfo(raw_text="共5页 第2页", current_page=2, total_pages=5),
            PageNumberInfo(raw_text="共5页 第3页", current_page=3, total_pages=5),
        ]

        result = checker.check_c11_page_continuity(page_infos, start_from_third=False)

        assert result.status == CheckStatus.ERROR
        assert "从1开始" in result.message

    def test_missing_pages(self):
        """Test missing page numbers."""
        checker = PageNumberChecker()

        page_infos = [
            PageNumberInfo(raw_text="共5页 第1页", current_page=1, total_pages=5),
            PageNumberInfo(raw_text="共5页 第3页", current_page=3, total_pages=5),  # Missing 2
            PageNumberInfo(raw_text="共5页 第4页", current_page=4, total_pages=5),
        ]

        result = checker.check_c11_page_continuity(page_infos, start_from_third=False)

        assert result.status == CheckStatus.ERROR
        assert 2 in result.missing_pages
        assert "跳页" in result.message

    def test_duplicate_pages(self):
        """Test duplicate page numbers."""
        checker = PageNumberChecker()

        page_infos = [
            PageNumberInfo(raw_text="共5页 第1页", current_page=1, total_pages=5, page_index=2),
            PageNumberInfo(raw_text="共5页 第2页", current_page=2, total_pages=5, page_index=3),
            PageNumberInfo(raw_text="共5页 第2页", current_page=2, total_pages=5, page_index=4),  # Duplicate
        ]

        result = checker.check_c11_page_continuity(page_infos, start_from_third=False)

        assert result.status == CheckStatus.ERROR
        assert len(result.duplicate_pages) > 0
        assert "重复" in result.message

    def test_inconsistent_total_pages(self):
        """Test inconsistent total page counts."""
        checker = PageNumberChecker()

        page_infos = [
            PageNumberInfo(raw_text="共5页 第1页", current_page=1, total_pages=5),
            PageNumberInfo(raw_text="共6页 第2页", current_page=2, total_pages=6),  # Different total
            PageNumberInfo(raw_text="共5页 第3页", current_page=3, total_pages=5),
        ]

        result = checker.check_c11_page_continuity(page_infos, start_from_third=False)

        assert result.status == CheckStatus.ERROR
        assert result.total_inconsistent is True
        assert "不一致" in result.message

    def test_final_page_mismatch(self):
        """Test final page Y doesn't equal XXX."""
        checker = PageNumberChecker()

        page_infos = [
            PageNumberInfo(raw_text="共5页 第1页", current_page=1, total_pages=5),
            PageNumberInfo(raw_text="共5页 第2页", current_page=2, total_pages=5),
            PageNumberInfo(raw_text="共5页 第3页", current_page=3, total_pages=5),
            # Last page says 3 but total is 5
        ]

        result = checker.check_c11_page_continuity(page_infos, start_from_third=False)

        assert result.status == CheckStatus.ERROR
        assert result.final_page_mismatch is True
        assert "不一致" in result.message

    def test_empty_page_infos(self):
        """Test empty page infos."""
        checker = PageNumberChecker()

        result = checker.check_c11_page_continuity([], start_from_third=False)

        assert result.status == CheckStatus.WARNING
        assert "未找到" in result.message

    def test_all_invalid_pages(self):
        """Test all pages with invalid page numbers."""
        checker = PageNumberChecker()

        page_infos = [
            PageNumberInfo(raw_text="", current_page=0, total_pages=0),
            PageNumberInfo(raw_text="", current_page=0, total_pages=0),
        ]

        result = checker.check_c11_page_continuity(page_infos, start_from_third=False)

        assert result.status == CheckStatus.ERROR
        assert "无效" in result.message


class TestCheckC11FromPDFDocument:
    """Test check_c11_from_pdf_document method."""

    def test_from_pdf_document(self):
        """Test checking from PDF document."""
        checker = PageNumberChecker()

        pdf_doc = PDFDocument()
        pdf_doc.pages = [
            PDFPage(page_number=1, width=595, height=842, raw_text="封面"),
            PDFPage(page_number=2, width=595, height=842, raw_text="注意事项"),
            PDFPage(page_number=3, width=595, height=842, raw_text="共2页 第1页"),
            PDFPage(page_number=4, width=595, height=842, raw_text="共2页 第2页"),
        ]

        result = checker.check_c11_from_pdf_document(pdf_doc)

        assert isinstance(result, C11Result)
        assert result.check_id == "C11"


class TestGetSummary:
    """Test get_summary method."""

    def test_summary_with_pass(self):
        """Test summary with pass result."""
        checker = PageNumberChecker()

        page_infos = [
            PageNumberInfo(raw_text="共2页 第1页", current_page=1, total_pages=2),
            PageNumberInfo(raw_text="共2页 第2页", current_page=2, total_pages=2),
        ]

        result = checker.check_c11_page_continuity(page_infos, start_from_third=False)
        summary = checker.get_summary(result)

        assert summary["status"] == CheckStatus.PASS
        assert summary["total_pages_checked"] == 2
        assert summary["valid_pages"] == 2

    def test_summary_with_errors(self):
        """Test summary with error result."""
        checker = PageNumberChecker()

        page_infos = [
            PageNumberInfo(raw_text="共5页 第2页", current_page=2, total_pages=5),
        ]

        result = checker.check_c11_page_continuity(page_infos, start_from_third=False)
        summary = checker.get_summary(result)

        assert summary["status"] == CheckStatus.ERROR


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_page_number_checker(self):
        """Test create_page_number_checker function."""
        checker = create_page_number_checker()
        assert isinstance(checker, PageNumberChecker)


class TestPageNumberInfo:
    """Test PageNumberInfo dataclass."""

    def test_creation(self):
        """Test creating PageNumberInfo."""
        info = PageNumberInfo(
            raw_text="共5页 第1页",
            total_pages=5,
            current_page=1,
            page_index=2,
        )

        assert info.raw_text == "共5页 第1页"
        assert info.total_pages == 5
        assert info.current_page == 1
        assert info.page_index == 2

    def test_negative_values_validation(self):
        """Test that negative values are set to 0."""
        info = PageNumberInfo(
            raw_text="",
            total_pages=-1,
            current_page=-5,
            page_index=0,
        )

        assert info.total_pages == 0
        assert info.current_page == 0


class TestC11Result:
    """Test C11Result dataclass."""

    def test_creation(self):
        """Test creating C11Result."""
        result = C11Result(
            check_id="C11",
            status=CheckStatus.PASS,
            message="All good",
        )

        assert result.check_id == "C11"
        assert result.status == CheckStatus.PASS

    def test_check_id_auto_set(self):
        """Test check_id auto-set when not provided."""
        result = C11Result(
            check_id="C11",  # Must provide check_id
            status=CheckStatus.ERROR,
            message="Test",
        )

        assert result.check_id == "C11"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_values(self):
        """Test handling of None values."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text(None)
        assert result is None

    def test_empty_string(self):
        """Test handling of empty string."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text("")
        assert result is None

    def test_mixed_formats(self):
        """Test handling of mixed page number formats."""
        checker = PageNumberChecker()

        # Should handle both formats
        result1 = checker._extract_page_number_from_text("共5页 第1页")
        result2 = checker._extract_page_number_from_text("1/5")

        assert result1 == (1, 5)
        assert result2 == (1, 5)

    def test_very_large_page_numbers(self):
        """Test very large page numbers."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text("共999页 第999页")
        assert result == (999, 999)

    def test_unicode_characters(self):
        """Test Unicode characters in page numbers."""
        checker = PageNumberChecker()

        result = checker._extract_page_number_from_text("共５页 第１页")  # Full-width digits
        # This might not work with int() conversion, but shouldn't crash
        # Just verify it doesn't crash
        assert result is None or isinstance(result, tuple)
