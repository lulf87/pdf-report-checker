"""
Page Number Checker for Report Self-Check (C11).

Handles page number continuity check starting from the third page.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.models.common_models import PDFDocument, PDFPage

logger = logging.getLogger(__name__)


class CheckStatus(str, Enum):
    """Status of a check result."""

    PASS = "pass"
    ERROR = "error"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a single check.

    Attributes:
        check_id: Check identifier (e.g., C11)
        status: Check status
        message: Human-readable result message
        details: Additional details about the check
        warnings: List of warning messages
    """

    check_id: str
    status: CheckStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        if self.status == CheckStatus.PASS:
            self.status = CheckStatus.WARNING


@dataclass
class PageNumberInfo:
    """Information extracted from a page number string.

    Attributes:
        raw_text: Original page number text
        total_pages: Total pages (XXX in "共XXX页")
        current_page: Current page number (Y in "第Y页")
        page_index: PDF page index (0-based)
    """

    raw_text: str = ""
    total_pages: int = 0
    current_page: int = 0
    page_index: int = 0

    def __post_init__(self) -> None:
        """Validate page numbers."""
        if self.total_pages < 0:
            object.__setattr__(self, 'total_pages', 0)
        if self.current_page < 0:
            object.__setattr__(self, 'current_page', 0)


@dataclass
class C11Result(CheckResult):
    """Result of C11: Page number continuity check.

    Attributes:
        page_infos: List of extracted page number information
        missing_pages: List of missing page numbers
        duplicate_pages: List of duplicate page numbers
        total_inconsistent: Whether total page counts are inconsistent
        final_page_mismatch: Whether final page Y doesn't equal total XXX
    """

    page_infos: list[PageNumberInfo] = field(default_factory=list)
    missing_pages: list[int] = field(default_factory=list)
    duplicate_pages: list[tuple[int, int]] = field(default_factory=list)  # (page_num, pdf_index)
    total_inconsistent: bool = False
    final_page_mismatch: bool = False

    def __post_init__(self) -> None:
        """Set check_id if not provided."""
        if not self.check_id:
            object.__setattr__(self, 'check_id', "C11")


class PageNumberChecker:
    """Checker for page number validation (C11).

    Verifies that page numbers starting from the third page are:
    - Continuous (Y from 1, no gaps or duplicates)
    - Consistent (all XXX values are the same)
    - Complete (final Y equals XXX)
    """

    # Pattern for page numbers: 共XXX页 第Y页
    PAGE_NUMBER_PATTERN = re.compile(
        r"共\s*(\d+)\s*页\s*第\s*(\d+)\s*页",
        re.IGNORECASE,
    )

    # Alternative patterns
    ALTERNATIVE_PATTERNS = [
        re.compile(r"第\s*(\d+)\s*页\s*/\s*共\s*(\d+)\s*页", re.IGNORECASE),
        re.compile(r"Page\s*(\d+)\s*of\s*(\d+)", re.IGNORECASE),
        re.compile(r"(\d+)\s*/\s*(\d+)", re.IGNORECASE),
    ]

    # Search position: top-right corner of page
    SEARCH_REGION = {
        "x_min": 0.5,  # Right half of page
        "y_min": 0,
        "y_max": 0.2,  # Top 20% of page
    }

    def __init__(self):
        """Initialize page number checker."""
        self.page_number_pattern = self.PAGE_NUMBER_PATTERN

    def _extract_page_number_from_text(
        self, text: str | None
    ) -> tuple[int, int] | None:
        """Extract page numbers from text.

        Args:
            text: Text to search for page numbers

        Returns:
            Tuple of (current_page, total_pages) or None
        """
        if not text:
            return None

        # Try main pattern first
        match = self.page_number_pattern.search(text)
        if match:
            try:
                total = int(match.group(1))
                current = int(match.group(2))
                return (current, total)
            except (ValueError, IndexError):
                pass

        # Try alternative patterns
        for pattern in self.ALTERNATIVE_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    g1, g2 = match.group(1), match.group(2)
                    # Determine order based on pattern
                    if "of" in pattern.pattern or "/" in pattern.pattern:
                        # Format: "current/total" or "Page X of Y"
                        current = int(g1)
                        total = int(g2)
                    else:
                        # Format: "第X页/共Y页"
                        current = int(g1)
                        total = int(g2)
                    return (current, total)
                except (ValueError, IndexError):
                    pass

        return None

    def extract_page_numbers(
        self, pdf_doc: PDFDocument, start_from_third: bool = True
    ) -> list[PageNumberInfo]:
        """Extract page numbers from PDF document.

        Args:
            pdf_doc: Parsed PDF document
            start_from_third: If True, start extraction from third page

        Returns:
            List of PageNumberInfo objects
        """
        page_infos: list[PageNumberInfo] = []

        start_index = 2 if start_from_third else 0  # Third page = index 2

        for i in range(start_index, len(pdf_doc.pages)):
            page = pdf_doc.pages[i]

            # Extract page number from text
            page_num = self._extract_page_number_from_text(page.raw_text)

            if page_num:
                current, total = page_num
                page_infos.append(
                    PageNumberInfo(
                        raw_text=page.raw_text[
                            max(0, page.raw_text.find("共")) : page.raw_text.find("页") + 1
                        ]
                        if "共" in page.raw_text
                        else "",
                        total_pages=total,
                        current_page=current,
                        page_index=i,
                    )
                )
            else:
                # Page number not found
                logger.warning(f"Page number not found on page {i + 1}")
                page_infos.append(
                    PageNumberInfo(
                        raw_text="",
                        total_pages=0,
                        current_page=0,
                        page_index=i,
                    )
                )

        return page_infos

    def check_c11_page_continuity(
        self,
        pdf_doc: PDFDocument | list[PageNumberInfo],
        start_from_third: bool = True,
    ) -> C11Result:
        """Check C11: Page number continuity and consistency.

        Args:
            pdf_doc: Parsed PDF document or list of PageNumberInfo
            start_from_third: If True, start checking from third page

        Returns:
            C11Result with continuity check details
        """
        result = C11Result(check_id="C11", status=CheckStatus.PASS)

        # Extract page numbers if PDF document is provided
        if isinstance(pdf_doc, PDFDocument):
            page_infos = self.extract_page_numbers(pdf_doc, start_from_third)
        else:
            page_infos = pdf_doc

        if not page_infos:
            result.status = CheckStatus.WARNING
            result.message = "未找到页码信息"
            return result

        result.page_infos = page_infos

        # Get valid page numbers
        valid_pages: list[PageNumberInfo] = [p for p in page_infos if p.current_page > 0]

        if not valid_pages:
            result.status = CheckStatus.ERROR
            result.message = "所有页码均无效"
            return result

        # Get all page numbers
        page_numbers = [p.current_page for p in valid_pages]
        total_values = [p.total_pages for p in valid_pages]

        # Check 1: Y starts from 1
        if page_numbers[0] != 1:
            result.status = CheckStatus.ERROR
            result.message = f"页码未从1开始，起始页码为{page_numbers[0]}"

        # Check 2: Y is continuous (no gaps)
        expected_pages = set(range(1, max(page_numbers) + 1))
        actual_pages = set(page_numbers)
        missing = sorted(expected_pages - actual_pages)
        result.missing_pages = missing

        if missing:
            result.status = CheckStatus.ERROR
            if result.message:
                result.message += f"；存在跳页: {missing}"
            else:
                result.message = f"存在跳页: {missing}"

        # Check 3: No duplicate Y values
        seen_pages: dict[int, list[int]] = {}
        for page_info in valid_pages:
            page_num = page_info.current_page
            if page_num not in seen_pages:
                seen_pages[page_num] = []
            seen_pages[page_num].append(page_info.page_index)

        duplicates = [
            (num, indices[0])
            for num, indices in seen_pages.items()
            if len(indices) > 1
        ]
        result.duplicate_pages = duplicates

        if duplicates:
            result.status = CheckStatus.ERROR
            if result.message:
                result.message += f"；存在重复页码: {[d[0] for d in duplicates]}"
            else:
                result.message = f"存在重复页码: {[d[0] for d in duplicates]}"

        # Check 4: All XXX values are the same
        unique_totals = set(total_values)
        if len(unique_totals) > 1:
            result.total_inconsistent = True
            result.status = CheckStatus.ERROR
            if result.message:
                result.message += f"；总页数不一致: {unique_totals}"
            else:
                result.message = f"总页数不一致: {unique_totals}"
        else:
            result.total_inconsistent = False

        # Check 5: Final page Y equals XXX
        if valid_pages:
            last_page = valid_pages[-1]
            total_pages = last_page.total_pages

            if last_page.current_page != total_pages:
                result.final_page_mismatch = True
                result.status = CheckStatus.ERROR
                if result.message:
                    result.message += (
                        f"；末页页码({last_page.current_page})与总页数({total_pages})不一致"
                    )
                else:
                    result.message = (
                        f"末页页码({last_page.current_page})与总页数({total_pages})不一致"
                    )

        # Set success message if no errors
        if result.status == CheckStatus.PASS:
            total = unique_totals.pop() if unique_totals else 0
            result.message = (
                f"页码连续完整: 第1页 ~ 第{page_numbers[-1]}页，共{total}页"
            )

        return result

    def check_c11_from_pdf_document(
        self, pdf_doc: PDFDocument
    ) -> C11Result:
        """Convenience method to check page numbers from PDF document.

        Args:
            pdf_doc: Parsed PDF document

        Returns:
            C11Result with continuity check details
        """
        return self.check_c11_page_continuity(pdf_doc, start_from_third=True)

    def get_summary(self, result: C11Result) -> dict[str, Any]:
        """Get summary of page number check result.

        Args:
            result: C11Result from check

        Returns:
            Summary dictionary
        """
        return {
            "status": result.status,
            "total_pages_checked": len(result.page_infos),
            "valid_pages": len([p for p in result.page_infos if p.current_page > 0]),
            "missing_pages": result.missing_pages,
            "duplicate_pages": result.duplicate_pages,
            "total_inconsistent": result.total_inconsistent,
            "final_page_mismatch": result.final_page_mismatch,
        }


def create_page_number_checker() -> PageNumberChecker:
    """Create page number checker instance.

    Returns:
        PageNumberChecker instance
    """
    return PageNumberChecker()
