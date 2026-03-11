"""
OCR Parser for scanned PDF processing using PaddleOCR.

Handles Chinese text recognition with special symbol processing.
Special symbols are corrected after OCR with WARNING output for manual verification.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

from app.models.common_models import (
    BoundingBox,
    PDFDocument,
    PDFPage,
    TextBlock,
)

logger = logging.getLogger(__name__)

# Special symbols that need post-processing correction
# Format: (incorrect_pattern, correct_char, description)
SPECIAL_SYMBOL_CORRECTIONS = [
    # Oh/zero confusion
    (r"(\d)O(\d)", r"\1〇\2", "O between numbers as zero"),
    (r"(\W)O(\d)", r"\1〇\2", "O before digit as zero"),

    # Plus/minus symbol
    (r"[\+-]|\+/-", "±", "plus-minus variations"),

    # Degree symbol (common OCR errors)
    (r"o\s*C|O\s*C|0\s*C", "℃", "degree celsius"),
    (r"\^0|²|​2", "²", "superscript 2"),
    (r"\^3|​3", "³", "superscript 3"),

    # Greek letters
    (r"Q|Ω", "Ω", "omega symbol"),
    (r"u|μ", "μ", "mu symbol"),
    (r"<=", "≤", "less than or equal"),
    (r">=", "≥", "greater than or equal"),
]

# Symbols that should trigger WARNING when corrected
WARNING_SYMBOLS = ["Ω", "±", "℃", "²", "³", "μ", "≤", "≥"]


@dataclass
class OCRWarning:
    """Warning for special symbol corrections.

    Attributes:
        position: Location in text (char index)
        original: Original OCR text
        corrected: Corrected text
        symbol: The special symbol involved
        context: Surrounding text for context
    """

    position: int
    original: str
    corrected: str
    symbol: str
    context: str = ""

    def __str__(self) -> str:
        return (
            f"[WARNING] Position {self.position}: "
            f"'{self.original}' → '{self.corrected}' "
            f"(symbol: {self.symbol}) | Context: '{self.context}'"
        )


@dataclass
class OCRResult:
    """Result of OCR processing.

    Attributes:
        text: Full text content
        text_blocks: Individual text blocks with positions
        warnings: List of special symbol correction warnings
        confidence: Average confidence score
        raw_ocr_data: Raw OCR output for debugging
    """

    text: str = ""
    text_blocks: list[TextBlock] = field(default_factory=list)
    warnings: list[OCRWarning] = field(default_factory=list)
    confidence: float = 0.0
    raw_ocr_data: list[dict] = field(default_factory=list)

    def has_warnings(self) -> bool:
        """Check if any symbol correction warnings were generated."""
        return len(self.warnings) > 0


class OCRParser:
    """OCR parser using PaddleOCR for Chinese text recognition.

    Handles special symbol recognition with post-processing correction.
    """

    def __init__(
        self,
        language: str = "ch",
        use_angle_cls: bool = True,
    ):
        """Initialize OCR parser.

        Args:
            language: OCR language ('ch' for Chinese, 'en' for English)
            use_angle_cls: Whether to use angle classifier for rotated text
        """
        if not PADDLEOCR_AVAILABLE:
            raise ImportError(
                "PaddleOCR is not installed. "
                "Install with: pip install paddleocr"
            )

        self.language = language
        self.use_angle_cls = use_angle_cls
        self._ocr_engine: PaddleOCR | None = None

    @property
    def ocr_engine(self) -> PaddleOCR:
        """Lazy initialization of PaddleOCR engine."""
        if self._ocr_engine is None:
            logger.info("Initializing PaddleOCR engine...")
            self._ocr_engine = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.language,
            )
            logger.info("PaddleOCR engine initialized")
        return self._ocr_engine

    def parse_image(
        self,
        image_path: str | Path | np.ndarray,
        page_number: int = 1,
    ) -> OCRResult:
        """Perform OCR on an image file or numpy array.

        Args:
            image_path: Path to image file or numpy array
            page_number: Page number for bounding boxes

        Returns:
            OCRResult with text, blocks, and warnings
        """
        if isinstance(image_path, (str, Path)):
            image = np.array(Image.open(image_path))
        else:
            image = image_path

        # Perform OCR
        raw_result = self.ocr_engine.ocr(image, cls=True)

        # Process results
        result = OCRResult()
        result.raw_ocr_data = raw_result or []

        if not raw_result or not raw_result[0]:
            logger.warning(f"OCR returned no results for page {page_number}")
            return result

        total_confidence = 0.0
        text_parts = []

        # Process each detected text line
        for line_data in raw_result[0]:
            if not line_data or len(line_data) < 2:
                continue

            bbox_points = line_data[0]
            text_info = line_data[1]

            if not text_info:
                continue

            text = text_info[0]
            confidence = text_info[1] if len(text_info) > 1 else 0.0

            if not text:
                continue

            # Calculate bounding box from points
            x_coords = [p[0] for p in bbox_points]
            y_coords = [p[1] for p in bbox_points]

            bbox = BoundingBox(
                x0=min(x_coords),
                y0=min(y_coords),  # OCR coords: 0 at top
                x1=max(x_coords),
                y1=max(y_coords),
                page=page_number,
            )

            # Create text block
            text_block = TextBlock(
                text=text,
                bbox=bbox,
                font_size=12.0,  # OCR doesn't provide font size
            )
            result.text_blocks.append(text_block)

            text_parts.append(text)
            total_confidence += confidence

        # Combine all text
        combined_text = "\n".join(text_parts)

        # Apply special symbol corrections
        corrected_text, warnings = self._apply_symbol_corrections(combined_text)
        result.text = corrected_text
        result.warnings = warnings

        # Calculate average confidence
        if result.text_blocks:
            result.confidence = total_confidence / len(result.text_blocks)

        # Log warnings
        for warning in warnings:
            logger.warning(str(warning))

        return result

    def parse_pdf_document(
        self,
        pdf_path: str | Path,
        page_range: list[int] | None = None,
    ) -> PDFDocument:
        """Parse a PDF document using OCR for all pages.

        Note: This requires converting PDF pages to images first.
        For better performance, use PDFParser with OCR fallback.

        Args:
            pdf_path: Path to PDF file
            page_range: List of page numbers to process (1-indexed). None for all.

        Returns:
            PDFDocument with OCR-extracted content
        """
        import fitz  # PyMuPDF

        pdf_path = Path(pdf_path)
        doc = fitz.open(str(pdf_path))

        pdf_doc = PDFDocument(
            file_path=str(pdf_path),
            total_pages=doc.page_count,
            is_scanned=True,  # OCR implies scanned content
        )

        pages_to_process = page_range or list(range(1, doc.page_count + 1))

        for page_num in pages_to_process:
            if page_num < 1 or page_num > doc.page_count:
                continue

            page = doc[page_num - 1]

            # Render page to image
            mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            image = np.array(Image.open(img_data))

            # Perform OCR
            ocr_result = self.parse_image(image, page_num)

            # Create PDFPage
            pdf_page = PDFPage(
                page_number=page_num,
                width=page.rect.width,
                height=page.rect.height,
                text_blocks=ocr_result.text_blocks,
                raw_text=ocr_result.text,
                is_scanned=True,
            )

            pdf_doc.pages.append(pdf_page)

        doc.close()
        return pdf_doc

    def _apply_symbol_corrections(
        self,
        text: str,
    ) -> tuple[str, list[OCRWarning]]:
        """Apply post-processing corrections for special symbols.

        Args:
            text: Raw OCR text

        Returns:
            Tuple of (corrected_text, warnings)
        """
        warnings: list[OCRWarning] = []
        corrected_text = text

        # Apply each correction pattern
        for pattern, replacement, description in SPECIAL_SYMBOL_CORRECTIONS:
            # Find all matches
            for match in re.finditer(pattern, corrected_text):
                original = match.group(0)
                position = match.start()

                # Check if this involves a warning symbol
                has_warning_symbol = any(
                    symbol in replacement for symbol in WARNING_SYMBOLS
                )

                # Extract context (20 chars before and after)
                start = max(0, position - 20)
                end = min(len(corrected_text), position + len(original) + 20)
                context = corrected_text[start:end]

                if has_warning_symbol:
                    # Determine which symbol triggered the warning
                    for symbol in WARNING_SYMBOLS:
                        if symbol in replacement:
                            warnings.append(
                                OCRWarning(
                                    position=position,
                                    original=original,
                                    corrected=match.expand(replacement),
                                    symbol=symbol,
                                    context=context.strip(),
                                )
                            )
                            break

            # Apply replacement
            corrected_text = re.sub(pattern, replacement, corrected_text)

        return corrected_text, warnings

    def correct_special_symbols(
        self,
        text: str,
        output_warnings: bool = True,
    ) -> tuple[str, list[OCRWarning]]:
        """Convenience method to correct special symbols in text.

        Args:
            text: Input text
            output_warnings: Whether to generate warnings

        Returns:
            Tuple of (corrected_text, warnings)
        """
        corrected, warnings = self._apply_symbol_corrections(text)

        if not output_warnings:
            warnings = []

        return corrected, warnings

    def get_warnings_summary(self, result: OCRResult) -> str:
        """Get a formatted summary of OCR warnings.

        Args:
            result: OCRResult to summarize

        Returns:
            Formatted warning summary string
        """
        if not result.has_warnings():
            return "No special symbol corrections needed."

        lines = [
            f"OCR Symbol Corrections: {len(result.warnings)} warning(s)",
            "-" * 60,
        ]

        # Group by symbol
        by_symbol: dict[str, list[OCRWarning]] = {}
        for warning in result.warnings:
            if warning.symbol not in by_symbol:
                by_symbol[warning.symbol] = []
            by_symbol[warning.symbol].append(warning)

        for symbol, symbol_warnings in sorted(by_symbol.items()):
            lines.append(f"\nSymbol '{symbol}': {len(symbol_warnings)} occurrence(s)")
            for i, warning in enumerate(symbol_warnings[:5], 1):  # Show max 5 per symbol
                lines.append(f"  {i}. {warning.context[:50]}...")
            if len(symbol_warnings) > 5:
                lines.append(f"  ... and {len(symbol_warnings) - 5} more")

        lines.append("\n" + "=" * 60)
        lines.append("WARNING: Special symbols were auto-corrected.")
        lines.append("Please verify these corrections manually.")

        return "\n".join(lines)


def parse_with_ocr(
    image_path: str | Path | np.ndarray,
    language: str = "ch",
) -> OCRResult:
    """Convenience function to perform OCR on an image.

    Args:
        image_path: Path to image file or numpy array
        language: OCR language ('ch' for Chinese, 'en' for English)

    Returns:
        OCRResult with extracted text and warnings
    """
    parser = OCRParser(language=language)
    return parser.parse_image(image_path)


def correct_text_symbols(
    text: str,
    output_warnings: bool = True,
) -> tuple[str, list[OCRWarning]]:
    """Convenience function to correct special symbols in text.

    Args:
        text: Input text to correct
        output_warnings: Whether to output warnings

    Returns:
        Tuple of (corrected_text, warnings)
    """
    parser = OCRParser()
    return parser.correct_special_symbols(text, output_warnings)
