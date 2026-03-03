"""
OCR Service for Report Self-Check.

Handles Chinese label recognition using PaddleOCR, with field extraction
for batch numbers, serial numbers, production dates, and expiration dates.
Handles photo/tag Caption parsing and main name extraction.
"""

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import fitz
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

# Field extraction regex patterns for Chinese labels
FIELD_PATTERNS = {
    # Model/Spec: 型号, 规格, 规格型号, Model, Spec
    "model_spec": [
        r"规格\s*型号\s*(?:[：:]\s*)?([^\n]+)",
        r"型号\s*规格\s*(?:[：:]\s*)?([^\n]+)",
        r"(?<!产品)型号\s*(?:[：:]\s*)?([^\n]+)",
        r"规格\s*(?:[：:]\s*)?([^\n]+)",
        r"Model\s*(?:[：:]\s*)?([^\n]+)",
        r"Spec\s*(?:[：:]\s*)?([^\n]+)",
    ],
    # Production Date: 生产日期, MFG, MFD, 生产日期, Manufacturing Date
    "production_date": [
        r"生产\s*日期\s*(?:[：:]\s*)?([^\n]+)",
        r"MFG\s*(?:[：:]\s*)?([^\n]+)",
        r"MFD\s*(?:[：:]\s*)?([^\n]+)",
        r"Manufacturing Date\s*(?:[：:]\s*)?([^\n]+)",
        r"制造\s*日期\s*(?:[：:]\s*)?([^\n]+)",
    ],
    # Batch/Lot Number: 批号, LOT, Lot Number, Batch Number
    "batch_number": [
        r"批号\s*(?:[：:]\s*)?([^\n]+)",
        r"LOT\s*(?:[：:]\s*)?([^\n]+)",
        r"Lot Number\s*(?:[：:]\s*)?([^\n]+)",
        r"Batch Number\s*(?:[：:]\s*)?([^\n]+)",
    ],
    # Serial Number: 序列号, SN, Serial Number
    "serial_number": [
        r"序列号\s*(?:[：:]\s*)?([^\n]+)",
        r"\bSN\b\s*(?:[：:]\s*)?([^\n]+)",
        r"Serial Number\s*(?:[：:]\s*)?([^\n]+)",
    ],
    # Registration Holder: 注册人, 注册人名称
    "registrant": [
        r"注册人\s*名称\s*[：:]\s*([^\n]+)",
        r"注册人\s*[：:]\s*([^\n]+)",
        r"[注註][^\n]{0,2}人\s*[：:]\s*([^\n]+)",
    ],
    # Registration Address: 注册人住所, 注册人地址
    "registrant_address": [
        r"注册人住所\s*(?:[：:]\s*)?([^\n]+)",
        r"注册人地址\s*(?:[：:]\s*)?([^\n]+)",
    ],
}


@dataclass
class CaptionInfo:
    """Information extracted from a photo/tag Caption.

    Attributes:
        raw_caption: Original caption text
        caption_number: Caption number if present
        is_chinese_label: Whether this is a Chinese label
        main_name: Extracted main name (with number/direction/category removed)
        position: Position information if available
    """

    raw_caption: str = ""
    caption_number: str = ""
    is_chinese_label: bool = False
    main_name: str = ""
    position: tuple[int, int, int, int] | None = None  # x0, y0, x1, y1

    def __str__(self) -> str:
        """String representation."""
        return f"{self.raw_caption} -> {self.main_name}"


@dataclass
class LabelOCRResult:
    """Result of OCR processing a label.

    Attributes:
        raw_text: Raw OCR text
        fields: Extracted field values
        confidence: OCR confidence score
        warnings: List of warning messages
        success: Whether OCR was successful
    """

    raw_text: str = ""
    fields: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    success: bool = False

    def get_field(self, field_name: str) -> str | None:
        """Get a field value."""
        return self.fields.get(field_name)

    def has_field(self, field_name: str) -> bool:
        """Check if field exists and has value."""
        value = self.fields.get(field_name)
        return bool(value and value.strip())


class OCRService:
    """OCR service for processing Chinese labels and extracting fields.

    Uses PaddleOCR for Chinese text recognition with specialized
    field extraction and main name parsing.
    """

    def __init__(
        self,
        use_angle_cls: bool = True,
        language: str = "ch",
    ):
        """Initialize OCR service.

        Args:
            use_angle_cls: Whether to use angle classifier
            language: OCR language ('ch' for Chinese)
        """
        self.use_angle_cls = use_angle_cls
        self.language = language
        self._ocr_engine: PaddleOCR | None = None
        self._rapid_ocr_engine: Any = None

    @property
    def ocr_engine(self) -> PaddleOCR:
        """Lazy initialization of PaddleOCR engine."""
        if self._ocr_engine is None:
            logger.info("Initializing PaddleOCR engine for OCR service...")
            self._ocr_engine = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.language,
            )
            logger.info("PaddleOCR OCR engine initialized")
        return self._ocr_engine

    def process_image(
        self,
        image_path: str | Path,
        extract_fields: bool = True,
    ) -> LabelOCRResult:
        """Process an image with OCR and extract fields.

        Args:
            image_path: Path to image file
            extract_fields: Whether to extract structured fields

        Returns:
            LabelOCRResult with extracted data
        """
        image_path = Path(image_path)
        result = LabelOCRResult()

        # Prefer PaddleOCR when runtime is available; otherwise fallback to RapidOCR.
        paddle_available = find_spec("paddle") is not None

        if paddle_available:
            result = self._process_image_with_paddle(image_path, extract_fields)
            # If Paddle returns no usable content, fallback to RapidOCR.
            if result.success and result.raw_text.strip():
                return result

        rapid_result = self._process_image_with_rapidocr(image_path, extract_fields)
        if rapid_result.success:
            return rapid_result
        if result.success:
            return result
        if result.warnings:
            rapid_result.warnings.extend(result.warnings)
        return rapid_result

    def _process_image_with_paddle(
        self,
        image_path: Path,
        extract_fields: bool,
    ) -> LabelOCRResult:
        """Process image with PaddleOCR backend."""
        result = LabelOCRResult()

        try:
            # Perform OCR
            ocr_result = self.ocr_engine.ocr(str(image_path), cls=True)

            if not ocr_result or not ocr_result[0]:
                result.warnings.append("OCR returned no results")
                return result

            # Extract text from OCR results
            text_parts = []
            total_confidence = 0.0

            for line_data in ocr_result[0]:
                if not line_data or len(line_data) < 2:
                    continue

                bbox_points = line_data[0]
                text_info = line_data[1]

                if not text_info:
                    continue

                text = text_info[0]
                confidence = text_info[1] if len(text_info) > 1 else 0.0

                if text:
                    text_parts.append(text)
                    total_confidence += confidence

            result.raw_text = "\n".join(text_parts)
            result.confidence = total_confidence / len(text_parts) if text_parts else 0.0
            result.success = len(text_parts) > 0

            # Extract structured fields if requested
            if extract_fields:
                result.fields = self._extract_fields(result.raw_text)

            logger.debug(
                f"OCR processed {image_path.name}: "
                f"{len(text_parts)} lines, confidence={result.confidence:.2f}"
            )

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            result.warnings.append(f"Processing error: {e}")

        return result

    def _process_image_with_rapidocr(
        self,
        image_path: Path,
        extract_fields: bool,
    ) -> LabelOCRResult:
        """Process image with RapidOCR fallback backend."""
        result = LabelOCRResult()

        try:
            if self._rapid_ocr_engine is None:
                from rapidocr_onnxruntime import RapidOCR
                self._rapid_ocr_engine = RapidOCR()

            ocr_result, _ = self._rapid_ocr_engine(str(image_path))
            if not ocr_result:
                result.warnings.append("RapidOCR returned no results")
                return result

            text_parts: list[str] = []
            total_confidence = 0.0
            valid_count = 0

            for line_data in ocr_result:
                if not line_data or len(line_data) < 3:
                    continue
                text = str(line_data[1] or "").strip()
                try:
                    confidence = float(line_data[2])
                except (TypeError, ValueError):
                    confidence = 0.0
                if text:
                    text_parts.append(text)
                    total_confidence += confidence
                    valid_count += 1

            if not text_parts:
                result.warnings.append("RapidOCR returned empty text lines")
                return result

            result.raw_text = "\n".join(text_parts)
            result.confidence = total_confidence / valid_count if valid_count else 0.0
            result.success = True

            if extract_fields:
                result.fields = self._extract_fields(result.raw_text)

            logger.debug(
                f"RapidOCR processed {image_path.name}: "
                f"{len(text_parts)} lines, confidence={result.confidence:.2f}"
            )
        except Exception as e:
            logger.error(f"RapidOCR processing error {image_path}: {e}")
            result.warnings.append(f"RapidOCR error: {e}")

        return result

    def _extract_fields(self, text: str) -> dict[str, str]:
        """Extract structured fields from OCR text.

        Args:
            text: OCR text to parse

        Returns:
            Dictionary of field names to values
        """
        fields: dict[str, str] = {}

        for field_name, patterns in FIELD_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value and self._is_valid_field_value(field_name, value):
                        fields[field_name] = value
                        break

        # Key-value can be split across two lines, e.g.:
        # "规格型号：" on one line and "RMD01" on next line.
        fields = self._fill_from_next_line_values(text, fields)

        # Multiline fallback for registrant address lines on label images.
        multiline_address = self._extract_multiline_value(
            text=text,
            label_patterns=[r"注册人住所", r"注册人地址"],
            stop_patterns=[
                r"注册人联系方式",
                r"受托生产企业名称",
                r"受托生产企业住所",
                r"受托生产企业生产地址",
                r"产品名称",
                r"型号规格",
                r"生产日期",
                r"失效日期",
                r"生产批号",
            ],
        )
        if multiline_address:
            fields["registrant_address"] = multiline_address

        # Fallback: infer production date from standalone 8-digit line.
        if not fields.get("production_date"):
            date_candidate = self._extract_standalone_date(text)
            if date_candidate:
                fields["production_date"] = date_candidate

        # Fallback: infer serial/batch from standalone alphanumeric token.
        if not fields.get("serial_number") and not fields.get("batch_number"):
            serial_candidate = self._extract_standalone_serial_or_batch(text)
            if serial_candidate:
                fields["serial_number"] = serial_candidate

        # Cleanup obvious OCR noise around field values.
        for key, value in list(fields.items()):
            cleaned = (value or "").strip()
            cleaned = re.sub(r"^[：:]+", "", cleaned).strip()
            fields[key] = cleaned

        return fields

    def _is_valid_field_value(self, field_name: str, value: str) -> bool:
        """Validate extracted value to avoid cross-field false captures."""
        cleaned = (value or "").strip()
        if not cleaned:
            return False

        if field_name == "registrant":
            # Reject values that are clearly address/contact field spillover.
            if re.search(r"(住所|住址|地址|联系方式)", cleaned):
                return False

        return True

    def _fill_from_next_line_values(
        self,
        text: str,
        fields: dict[str, str],
    ) -> dict[str, str]:
        """Fill fields when value appears on the next line after label."""
        lines = [line.strip() for line in (text or "").split("\n")]

        def _next_non_empty(start: int) -> str:
            for idx in range(start + 1, len(lines)):
                candidate = lines[idx].strip()
                if candidate:
                    return candidate
            return ""

        for idx, line in enumerate(lines):
            if not line:
                continue

            next_value = _next_non_empty(idx)
            if not next_value:
                continue

            if ("规格型号" in line or "型号规格" in line) and not fields.get("model_spec"):
                if re.fullmatch(r"[A-Za-z0-9.\-_/]+", next_value):
                    fields["model_spec"] = next_value

            if any(k in line.upper() for k in ["SN", "序列号", "批号"]) and not (
                fields.get("serial_number") or fields.get("batch_number")
            ):
                if re.fullmatch(r"[A-Za-z]{1,6}\d{6,}[A-Za-z0-9\-_/]*", next_value):
                    fields["serial_number"] = next_value

            if any(k in line for k in ["生产日期", "制造日期"]) and not fields.get("production_date"):
                if re.fullmatch(r"\d{8}", re.sub(r"\D", "", next_value)):
                    fields["production_date"] = re.sub(r"\D", "", next_value)

        return fields

    def _extract_standalone_date(self, text: str) -> str:
        """Extract standalone 8-digit date token from OCR text."""
        candidates = re.findall(r"(?<!\d)(20\d{6})(?!\d)", text or "")
        for token in candidates:
            try:
                from datetime import datetime
                datetime.strptime(token, "%Y%m%d")
                return token
            except ValueError:
                continue
        return ""

    def _extract_standalone_serial_or_batch(self, text: str) -> str:
        """Extract serial/batch-like token when label key is missing."""
        candidates = re.findall(r"\b[A-Z]{2,8}\d{6,}[A-Z0-9\-_/]*\b", text or "")
        if not candidates:
            return ""
        # Prefer longest candidate; usually serial/batch is the longest alnum code.
        return sorted(candidates, key=len, reverse=True)[0]

    def _extract_multiline_value(
        self,
        text: str,
        label_patterns: list[str],
        stop_patterns: list[str],
    ) -> str:
        """Extract multiline value that starts after a specific label."""
        lines = [line.strip() for line in (text or "").split("\n")]
        label_res = [re.compile(pat) for pat in label_patterns]
        stop_res = [re.compile(pat) for pat in stop_patterns]

        for idx, line in enumerate(lines):
            if not line:
                continue

            matched_label = None
            for label_re in label_res:
                if label_re.search(line):
                    matched_label = label_re
                    break
            if not matched_label:
                continue

            parts: list[str] = []
            same_line = re.split(r"[:：]", line, maxsplit=1)
            if len(same_line) == 2 and same_line[1].strip():
                parts.append(same_line[1].strip())

            for j in range(idx + 1, len(lines)):
                current = lines[j].strip()
                if not current:
                    continue
                if any(stop_re.search(current) for stop_re in stop_res):
                    break
                parts.append(current)

            if parts:
                return "".join(parts).strip()

        return ""

    def parse_caption(self, caption_text: str) -> CaptionInfo:
        """Parse a photo/tag Caption to extract main name.

        Args:
            caption_text: Caption text to parse

        Returns:
            CaptionInfo with extracted main name
        """
        info = CaptionInfo(raw_caption=caption_text)

        # Check if this is a Chinese label
        info.is_chinese_label = self._is_chinese_label(caption_text)

        # Extract caption number if present (e.g., "图1", "№2", "No.3", "Photo 2")
        caption_number_match = re.search(
            r"(?:图|№|No\.?|Photo|Fig|Fig\.)\s*(\d+)",
            caption_text,
            re.IGNORECASE,
        )
        if caption_number_match:
            info.caption_number = caption_number_match.group(1)

        # Extract and clean main name
        main_name = caption_text.strip()

        # Remove caption number prefix
        main_name = re.sub(
            r"^(?:图|№|No\.?|Photo|Plate|Fig|Fig\.)\s*\d+\s*[:：]?\s*",
            "",
            main_name,
            flags=re.IGNORECASE,
        )

        # Remove direction indicators (方位词)
        direction_indicators = [
            r"左侧显示", r"右侧显示", r"左图", r"右图",
            r"正面图", r"背面图", r"俯视图", r"仰视图",
            r"局部放大图", r"细节图", r"整体图",
        ]
        for pattern in direction_indicators:
            main_name = re.sub(pattern, "", main_name)

        # Remove category indicators (类别词)
        category_indicators = [
            r"中文标签[样张]?\s*[:：]?",
            r"标签[样张]?\s*[:：]?",
            r"铭牌\s*[:：]?",
            r"标牌\s*[:：]?",
            r"标签\s*[:：]?",
        ]
        for pattern in category_indicators:
            main_name = re.sub(pattern, "", main_name)

        # Remove common prefixes
        prefixes_to_remove = [
            r"^[第一二三四五六七八九十\d]+(?:[\.、:：]|张)\s*",
            r"^\d+[\.、]\s*",
        ]
        for pattern in prefixes_to_remove:
            main_name = re.sub(pattern, "", main_name)

        info.main_name = main_name.strip()

        return info

    def extract_caption_info(self, page_text: str) -> CaptionInfo | None:
        """Extract caption information from page text.

        Args:
            page_text: Raw page text

        Returns:
            CaptionInfo if a caption-like line is found, otherwise None
        """
        if not page_text:
            return None

        lines = [line.strip() for line in page_text.split("\n") if line.strip()]
        caption_line = ""

        # Prefer obvious caption prefixes first.
        prefix_candidates: list[str] = []
        for line in lines:
            if re.match(r"^(图|№|No\.?|Photo|Plate|Fig\.?)", line, re.IGNORECASE):
                prefix_candidates.append(line)

        if prefix_candidates:
            # If multiple captions exist on one page, prefer the one explicitly marked
            # as Chinese label (e.g., "№2 ... 中文标签").
            for candidate in prefix_candidates:
                if self._is_chinese_label(candidate):
                    caption_line = candidate
                    break
            if not caption_line:
                caption_line = prefix_candidates[0]

        # Fallback: any line containing label-related keywords.
        if not caption_line:
            for line in lines:
                if self._is_chinese_label(line):
                    caption_line = line
                    break

        if not caption_line:
            return None

        return self.parse_caption(caption_line)

    async def extract_label_from_page(
        self,
        page: Any,
        pdf_path: str | Path | None = None,
        enable_llm: bool = False,
    ) -> LabelOCRResult | None:
        """Extract label fields from a parsed PDF page.

        This method is designed for report-check pipeline usage where page-level
        text is already available from PDF parsing. OCR image-level extraction can
        be integrated later when page image crops are available.

        Args:
            page: Parsed PDF page object, expected to expose `raw_text`
            pdf_path: Optional source PDF path for image-level OCR extraction
            enable_llm: Reserved flag for future VLM enhancement

        Returns:
            LabelOCRResult parsed from page text
        """
        raw_text = getattr(page, "raw_text", "") or ""
        if not raw_text and getattr(page, "text_blocks", None):
            raw_text = "\n".join(
                str(getattr(block, "text", "")).strip()
                for block in page.text_blocks
                if getattr(block, "text", "")
            )

        text_result = LabelOCRResult(
            raw_text=raw_text,
            fields=self._extract_fields(raw_text),
            confidence=1.0 if raw_text else 0.0,
            success=bool(raw_text),
        )

        image_result: LabelOCRResult | None = None
        tmp_image_path: str | None = None
        page_number = int(getattr(page, "page_number", 0) or 0)

        if pdf_path and page_number > 0:
            try:
                with fitz.open(str(pdf_path)) as pdf_doc:
                    page_index = page_number - 1
                    if 0 <= page_index < pdf_doc.page_count:
                        fitz_page = pdf_doc[page_index]
                        pix = fitz_page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                            tmp_image_path = tmp.name
                        pix.save(tmp_image_path)
                        image_result = self.process_image(tmp_image_path, extract_fields=True)
            except Exception as e:
                logger.warning(
                    f"Image-level OCR failed for page {page_number}: {e}"
                )
            finally:
                if tmp_image_path and os.path.exists(tmp_image_path):
                    try:
                        os.unlink(tmp_image_path)
                    except OSError:
                        pass

        # Prefer image OCR fields when available; fallback to text extraction.
        result = text_result
        if image_result and image_result.success:
            merged_fields = dict(text_result.fields)
            merged_fields.update(image_result.fields)
            result = LabelOCRResult(
                raw_text=image_result.raw_text or text_result.raw_text,
                fields=merged_fields,
                confidence=image_result.confidence,
                warnings=[*text_result.warnings, *image_result.warnings],
                success=True,
            )

        if enable_llm:
            # Placeholder to preserve interface behavior until VLM page extraction
            # is introduced.
            result.warnings.append("LLM增强暂未用于页面级文本提取，当前使用规则提取")

        return result

    def _is_chinese_label(self, text: str) -> bool:
        """Check if text indicates a Chinese label.

        Args:
            text: Text to check

        Returns:
            True if this appears to be a Chinese label
        """
        # Check for Chinese label keywords
        label_keywords = [
            "中文标签",
            "标签样张",
            "标签",
            "中文标签样张",
            "铭牌",
        ]

        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in label_keywords)

    def extract_main_name_from_caption(
        self, caption_text: str
    ) -> str:
        """Convenience method to extract just the main name.

        Args:
            caption_text: Caption text to parse

        Returns:
            Extracted main name
        """
        info = self.parse_caption(caption_text)
        return info.main_name

    def process_label_image(
        self,
        image_path: str | Path,
    ) -> tuple[CaptionInfo, LabelOCRResult]:
        """Process a label image and extract both Caption info and fields.

        Args:
            image_path: Path to label image

        Returns:
            Tuple of (CaptionInfo, LabelOCRResult)
        """
        # First get OCR result
        ocr_result = self.process_image(image_path, extract_fields=True)

        # Then parse as caption
        caption_info = self.parse_caption(ocr_result.raw_text)

        return caption_info, ocr_result


# Convenience functions
def extract_label_fields(image_path: str | Path) -> dict[str, str]:
    """Convenience function to extract fields from a label image.

    Args:
        image_path: Path to label image

    Returns:
        Dictionary of extracted field values
    """
    service = OCRService()
    result = service.process_image(image_path, extract_fields=True)
    return result.fields


def parse_caption_main_name(caption_text: str) -> str:
    """Convenience function to extract main name from caption.

    Args:
        caption_text: Caption text to parse

    Returns:
        Extracted main name
    """
    service = OCRService()
    return service.extract_main_name_from_caption(caption_text)
