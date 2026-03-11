"""
Report Export Service for PDF generation.

Generates PDF reports for both PTR comparison and report self-check results.
"""

import io
import logging
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.services.presentation_status import get_clause_presentation_status

logger = logging.getLogger(__name__)

# Color scheme - Morandi colors (matching frontend)
COLOR_SUCCESS = colors.HexColor("#6b9e8a")
COLOR_DANGER = colors.HexColor("#c07878")
COLOR_WARN = colors.HexColor("#c4a76c")
COLOR_INFO = colors.HexColor("#7a8fb5")
COLOR_ACCENT = colors.HexColor("#8b7ec8")
COLOR_TEXT = colors.HexColor("#333333")
COLOR_TEXT_LIGHT = colors.HexColor("#666666")
COLOR_BORDER = colors.HexColor("#dddddd")


class ReportExportService:
    """Service for exporting comparison results to PDF."""

    def __init__(self):
        """Initialize the export service."""
        self._setup_fonts()
        self._setup_styles()

    def _setup_fonts(self) -> None:
        """Setup Chinese fonts for PDF generation."""
        try:
            # Try to register Chinese font (fallback to default if not available)
            pdfmetrics.registerFont(
                TTFont("SimHei", "/System/Library/Fonts/STHeiti Light.ttc", subfontIndex=0)
            )
            self.chinese_font = "SimHei"
        except Exception:
            logger.warning("Chinese font not available, using default")
            self.chinese_font = "Helvetica"

    def _setup_styles(self) -> None:
        """Setup paragraph styles for PDF."""
        self.styles = getSampleStyleSheet()

        # Title style
        self.styles.add(
            ParagraphStyle(
                name="ChineseTitle",
                fontName=self.chinese_font,
                fontSize=18,
                leading=24,
                alignment=1,  # Center
                spaceAfter=20,
            )
        )

        # Heading style
        self.styles.add(
            ParagraphStyle(
                name="ChineseHeading",
                fontName=self.chinese_font,
                fontSize=14,
                leading=18,
                spaceBefore=15,
                spaceAfter=10,
            )
        )

        # Normal text style
        self.styles.add(
            ParagraphStyle(
                name="ChineseNormal",
                fontName=self.chinese_font,
                fontSize=10,
                leading=14,
                spaceAfter=6,
            )
        )

        # Code/monospace style
        self.styles.add(
            ParagraphStyle(
                name="CodeStyle",
                fontName="Courier",
                fontSize=9,
                leading=12,
                backColor=colors.HexColor("#f5f5f5"),
                borderPadding=5,
            )
        )

    def export_ptr_comparison(
        self,
        result: dict[str, Any],
        title: str = "PTR 条款核对报告",
    ) -> bytes:
        """Export PTR comparison result to PDF.

        Args:
            result: PTR comparison result dictionary
            title: PDF title

        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        story = []

        # Title
        story.append(Paragraph(title, self.styles["ChineseTitle"]))
        story.append(
            Paragraph(
                f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                self.styles["ChineseNormal"],
            )
        )
        story.append(Spacer(1, 10 * mm))

        # Summary statistics
        story.append(Paragraph("核对总览", self.styles["ChineseHeading"]))

        summary = result.get("summary", {})
        statistics = result.get("statistics", {})
        ptr_statistics = {
            "total": summary.get("total_clauses", statistics.get("total", 0)),
            "consistent": summary.get("matches", statistics.get("consistent", 0)),
            "inconsistent": (
                summary.get("differs", 0) + summary.get("missing", 0)
                if summary else statistics.get("inconsistent", 0)
            ),
            "excluded": summary.get("excluded", 0),
            "consistency_rate": (
                summary.get("match_rate", 0) * 100 if summary else statistics.get("consistency_rate", 0)
            ),
            "special_status_counts": summary.get("special_status_counts", {}),
        }
        summary_data = [
            ["指标", "数值"],
            ["条款总数", str(ptr_statistics.get("total", 0))],
            ["一致数量", str(ptr_statistics.get("consistent", 0))],
            ["不一致数量", str(ptr_statistics.get("inconsistent", 0))],
            ["排除数量", str(ptr_statistics.get("excluded", 0))],
            ["一致率", f"{ptr_statistics.get('consistency_rate', 0):.1f}%"],
        ]

        summary_table = Table(summary_data, colWidths=[80 * mm, 50 * mm])
        summary_table.setStyle(
            TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), self.chinese_font),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWHEIGHT", (0, 0), (-1, -1), 8 * mm),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 10 * mm))

        # Clause details
        story.append(Paragraph("条款比对详情", self.styles["ChineseHeading"]))

        clauses = result.get("clauses", [])
        for clause in clauses:
            clause_data = self._format_clause_for_pdf(clause)
            story.append(clause_data)

        # Build PDF
        doc.build(story)

        buffer.seek(0)
        return buffer.getvalue()

    def export_report_check(
        self,
        result: dict[str, Any],
        title: str = "报告自身核对报告",
    ) -> bytes:
        """Export report self-check result to PDF.

        Args:
            result: Report check result dictionary
            title: PDF title

        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        story = []

        # Title
        story.append(Paragraph(title, self.styles["ChineseTitle"]))
        story.append(
            Paragraph(
                f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                self.styles["ChineseNormal"],
            )
        )
        story.append(Spacer(1, 10 * mm))

        # Summary statistics
        story.append(Paragraph("核对总览", self.styles["ChineseHeading"]))

        statistics = result.get("statistics", {})
        summary_data = [
            ["指标", "数值"],
            ["总项目数", str(statistics.get("total", 0))],
            ["通过数量", str(statistics.get("passed", 0))],
            ["失败数量", str(statistics.get("failed", 0))],
            ["警告数量", str(statistics.get("warnings", 0))],
        ]

        summary_table = Table(summary_data, colWidths=[80 * mm, 50 * mm])
        summary_table.setStyle(
            TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), self.chinese_font),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWHEIGHT", (0, 0), (-1, -1), 8 * mm),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 10 * mm))

        # Check details by category
        checks = result.get("checks", [])

        # C01-C03: Field checks
        field_checks = [c for c in checks if c.get("code", "").startswith("C0")]
        if field_checks:
            story.append(Paragraph("字段核对 (C01-C03)", self.styles["ChineseHeading"]))
            story.extend(self._format_checks_for_pdf(field_checks))

        # C04-C06: Sample description checks
        sample_checks = [c for c in checks if c.get("code", "").startswith("C0") and int(c.get("code", "C00")[1:]) >= 4]
        if sample_checks:
            story.append(Spacer(1, 5 * mm))
            story.append(Paragraph("样品描述核对 (C04-C06)", self.styles["ChineseHeading"]))
            story.extend(self._format_checks_for_pdf(sample_checks))

        # C07-C10: Inspection item checks
        inspection_checks = [c for c in checks if c.get("code", "").startswith("C0") and int(c.get("code", "C00")[1:]) >= 7]
        if inspection_checks:
            story.append(Spacer(1, 5 * mm))
            story.append(Paragraph("检验项目核对 (C07-C10)", self.styles["ChineseHeading"]))
            story.extend(self._format_checks_for_pdf(inspection_checks))

        # C11: Page number check
        page_checks = [c for c in checks if c.get("code") == "C11"]
        if page_checks:
            story.append(Spacer(1, 5 * mm))
            story.append(Paragraph("页码核对 (C11)", self.styles["ChineseHeading"]))
            story.extend(self._format_checks_for_pdf(page_checks))

        # Build PDF
        doc.build(story)

        buffer.seek(0)
        return buffer.getvalue()

    def _format_clause_for_pdf(self, clause: dict[str, Any]) -> Any:
        """Format a clause comparison for PDF display.

        Args:
            clause: Clause comparison data

        Returns:
            PDF table element
        """
        code = clause.get("code") or clause.get("ptr_number", "")
        title = clause.get("title") or clause.get("display_title") or clause.get("ptr_text", "")
        presentation = self._resolve_clause_presentation(clause)
        status_color = self._status_color(presentation["display_status_variant"])
        status_text = presentation["display_status_label"]
        explanation = clause.get("display_status_explanation") or presentation["display_status_explanation"] or ""

        # Create clause table
        clause_data = [
            [f"{code}: {title}", status_text, explanation],
        ]

        table = Table(clause_data, colWidths=[95 * mm, 28 * mm, 47 * mm])
        table.setStyle(
            TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), self.chinese_font),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (1, 0), (1, 0), status_color),
                ("TEXTCOLOR", (1, 0), (1, 0), colors.white),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("ALIGN", (2, 0), (2, 0), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWHEIGHT", (0, 0), (-1, -1), 8 * mm),
                ("LEFTPADDING", (0, 0), (0, 0), 5 * mm),
            ])
        )

        return table

    def _resolve_clause_presentation(self, clause: dict[str, Any]) -> dict[str, Any]:
        if clause.get("display_status"):
            return {
                "display_status": clause.get("display_status"),
                "display_status_label": clause.get("display_status_label", clause.get("display_status")),
                "display_status_variant": clause.get("display_status_variant", "info"),
                "display_status_explanation": clause.get("display_status_explanation", ""),
            }

        return get_clause_presentation_status(
            result="match" if clause.get("is_consistent") else ("differ" if clause.get("status") == "mismatched" else "excluded"),
            comparison_status=clause.get("status", ""),
            match_reason=clause.get("match_reason", ""),
        )

    def _status_color(self, variant: str) -> colors.Color:
        return {
            "success": COLOR_SUCCESS,
            "danger": COLOR_DANGER,
            "warn": COLOR_WARN,
            "info": COLOR_INFO,
            "accent": COLOR_ACCENT,
        }.get(variant, COLOR_INFO)

    def _format_checks_for_pdf(self, checks: list[dict[str, Any]]) -> list[Any]:
        """Format a list of checks for PDF display.

        Args:
            checks: List of check results

        Returns:
            List of PDF elements
        """
        elements = []

        for check in checks:
            code = check.get("code", "")
            name = check.get("name", "")
            status = check.get("status", "PASS")
            message = check.get("message", "")

            # Status color
            if status == "PASS":
                status_color = COLOR_SUCCESS
            elif status == "WARN":
                status_color = COLOR_WARN
            else:
                status_color = COLOR_DANGER

            # Create check row
            check_data = [
                [f"{code}: {name}", status, message[:50] + "..." if len(message) > 50 else message],
            ]

            table = Table(check_data, colWidths=[50 * mm, 20 * mm, 80 * mm])
            table.setStyle(
                TableStyle([
                    ("FONTNAME", (0, 0), (-1, -1), self.chinese_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (1, 0), (1, 0), status_color),
                    ("TEXTCOLOR", (1, 0), (1, 0), colors.white),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "CENTER"),
                    ("ALIGN", (2, 0), (2, 0), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWHEIGHT", (0, 0), (-1, -1), 7 * mm),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ])
            )

            elements.append(table)
            elements.append(Spacer(1, 2 * mm))

        return elements


# Convenience functions
def create_export_service() -> ReportExportService:
    """Create an export service instance.

    Returns:
        ReportExportService instance
    """
    return ReportExportService()


def export_ptr_to_pdf(result: dict[str, Any]) -> bytes:
    """Export PTR comparison result to PDF.

    Args:
        result: PTR comparison result

    Returns:
        PDF bytes
    """
    service = create_export_service()
    return service.export_ptr_comparison(result)


def export_report_check_to_pdf(result: dict[str, Any]) -> bytes:
    """Export report check result to PDF.

    Args:
        result: Report check result

    Returns:
        PDF bytes
    """
    service = create_export_service()
    return service.export_report_check(result)
