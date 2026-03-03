"""
Third Page Checker for Report Self-Check (C01-C03).

Handles consistency checks between first page, third page, and Chinese labels
for client, sample name, model/spec, production date, and other fields.
"""

import logging
import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.models.report_models import ThirdPageFields
from app.services.ocr_service import CaptionInfo, LabelOCRResult, OCRService
from app.services.text_normalizer import TextNormalizer

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
        check_id: Check identifier (e.g., C01, C02)
        status: Check status
        message: Human-readable result message
        details: Additional details about the check
        source_a: Source A value
        source_b: Source B value
        warnings: List of warning messages
    """

    check_id: str
    status: CheckStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    source_a: str = ""
    source_b: str = ""
    warnings: list[str] = field(default_factory=list)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        if self.status == CheckStatus.PASS:
            self.status = CheckStatus.WARNING


@dataclass
class C01Result(CheckResult):
    """Result of C01: First page vs third page field consistency."""

    field_name: str = ""  # 委托方, 样品名称, 型号规格

    def __post_init__(self) -> None:
        """Set check_id."""
        if not self.check_id:
            self.check_id = "C01"


@dataclass
class C02Result(CheckResult):
    """Result of C02: Third page extended field checks."""

    field_name: str = ""  # 型号规格, 生产日期, 产品编号/批号, 委托方, 委托方地址

    def __post_init__(self) -> None:
        """Set check_id."""
        if not self.check_id:
            self.check_id = "C02"


@dataclass
class C03Result(CheckResult):
    """Result of C03: Production date format consistency."""

    page_format: str = ""
    label_format: str = ""
    page_value: str = ""
    label_value: str = ""

    def __post_init__(self) -> None:
        """Set check_id."""
        if not self.check_id:
            self.check_id = "C03"


class ThirdPageChecker:
    """Checker for third page field consistency (C01-C03).

    Performs checks for:
    - C01: First page vs third page field consistency
    - C02: Third page extended field checks with "见样品描述栏" logic
    - C03: Production date format consistency
    """

    # Reference text for "见样品描述栏"
    SEE_SAMPLE_DESC_PATTERNS = [
        r"见['\"'〞]?样品描述['\"'〞]?栏",
        r"见['\"'〞]?样品描述['\"'〞]?栏中",
        r"见样品描述栏",
        r"见'样品描述'栏",
    ]

    # Field mappings for C02: third page -> OCR label fields
    FIELD_MAPPINGS = {
        "型号规格": ["model_spec"],
        "生产日期": ["production_date"],
        "产品编号/批号": ["batch_number", "serial_number"],
        "委托方": ["registrant"],
        "委托方地址": ["registrant_address"],
    }

    def __init__(
        self,
        ocr_service: OCRService | None = None,
        normalizer: TextNormalizer | None = None,
    ):
        """Initialize third page checker.

        Args:
            ocr_service: OCR service for label extraction
            normalizer: Text normalizer for text comparison
        """
        self.ocr_service = ocr_service or OCRService()
        self.normalizer = normalizer or TextNormalizer()

    def _normalize_for_comparison(self, text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        return self.normalizer.normalize(text).strip()

    def _strict_equals(self, text1: str, text2: str) -> bool:
        """Strict equality for module-2 field checks."""
        return (text1 or "").strip() == (text2 or "").strip()

    def _address_equals(self, text1: str, text2: str) -> bool:
        """Address equality with whitespace-insensitive normalization."""
        norm1 = re.sub(r"\s+", "", self._normalize_for_comparison(text1))
        norm2 = re.sub(r"\s+", "", self._normalize_for_comparison(text2))
        if norm1 == norm2:
            return True
        if not norm1 or not norm2:
            return False
        # OCR often confuses a few address characters; allow high-similarity match.
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= 0.95

    def _client_equals(self, text1: str, text2: str) -> bool:
        """Client-name equality with OCR-noise tolerance."""
        norm1 = re.sub(r"\s+", "", self._normalize_for_comparison(text1))
        norm2 = re.sub(r"\s+", "", self._normalize_for_comparison(text2))
        if norm1 == norm2:
            return True
        if not norm1 or not norm2:
            return False

        # OCR may miss one character in company names (e.g., "器械" vs "器城").
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= 0.9

    def _model_spec_equals(self, text1: str, text2: str) -> bool:
        """Model/spec equality with limited OCR confusion tolerance."""
        norm1 = (text1 or "").strip()
        norm2 = (text2 or "").strip()
        if norm1 == norm2:
            return True
        if not norm1 or not norm2:
            return False

        # Accept common OCR substitutions in alphanumeric model codes.
        trans = str.maketrans({
            "O": "0",
            "o": "0",
            "I": "1",
            "l": "1",
            "|": "1",
            "S": "5",
        })
        canon1 = norm1.translate(trans)
        canon2 = norm2.translate(trans)
        return canon1 == canon2

    def _is_see_sample_desc(self, value: str) -> bool:
        """Check if value is "见样品描述栏" pattern.

        Args:
            value: Value to check

        Returns:
            True if matches pattern
        """
        normalized = self._normalize_for_comparison(value)
        for pattern in self.SEE_SAMPLE_DESC_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True
        return False

    def check_c01_field_consistency(
        self,
        first_page_fields: dict[str, str],
        third_page_fields: ThirdPageFields,
    ) -> list[C01Result]:
        """Check C01: First page vs third page field consistency.

        Args:
            first_page_fields: Fields extracted from first page
            third_page_fields: Fields extracted from third page

        Returns:
            List of C01 results for each field
        """
        results: list[C01Result] = []

        # Fields to check: 委托方, 样品名称, 型号规格
        fields_to_check = {
            "委托方": ("client", "client"),
            "样品名称": ("sample_name", "sample_name"),
            "型号规格": ("model_spec", "model_spec"),
        }

        for display_name, (first_key, third_key) in fields_to_check.items():
            # Get values
            first_value = (
                first_page_fields.get(first_key, "")
                or first_page_fields.get(display_name, "")
            )
            third_value = getattr(third_page_fields, third_key, "")

            # Strict comparison per PRD: character-level equality.
            if self._strict_equals(first_value, third_value):
                status = CheckStatus.PASS
                message = f"{display_name}一致: {first_value}"
            else:
                status = CheckStatus.ERROR
                message = f"{display_name}不一致: 首页='{first_value}' vs 第三页='{third_value}'"

            results.append(
                C01Result(
                    check_id="C01",
                    status=status,
                    message=message,
                    field_name=display_name,
                    source_a=first_value,
                    source_b=third_value,
                )
            )

        return results

    def check_c02_extended_fields(
        self,
        third_page_fields: ThirdPageFields,
        label_ocr_results: list[tuple[CaptionInfo, LabelOCRResult]],
        sample_name: str,
    ) -> list[C02Result]:
        """Check C02: Third page extended field checks.

        Implements the "见样品描述栏" logic:
        1. Check if all three fields (型号规格, 生产日期, 产品编号/批号) are "见样品描述栏"
        2. If yes, skip those three fields; continue with 委托方 and 委托方地址
        3. If partial or no "见样品描述栏", compare all five fields with label OCR

        Args:
            third_page_fields: Fields from third page
            label_ocr_results: List of (caption info, OCR result) from photo pages
            sample_name: Sample name to match labels

        Returns:
            List of C02 results
        """
        results: list[C02Result] = []

        # Find matching label (caption main name matches sample name)
        matching_label = self._find_matching_label(
            label_ocr_results,
            sample_name,
        )

        if not matching_label:
            # No matching label found - this is a warning for all fields
            for field_name in ["型号规格", "生产日期", "产品编号/批号", "委托方", "委托方地址"]:
                results.append(
                    C02Result(
                        check_id="C02",
                        status=CheckStatus.WARNING,
                        message=f"未找到与样品名称'{sample_name}'匹配的中文标签",
                        field_name=field_name,
                        warnings=["无匹配标签，跳过比对"],
                    )
                )
            return results

        caption_info, ocr_result = matching_label

        # Rule 1: Check "见样品描述栏" for first three fields
        see_sample_desc_fields = [
            "型号规格",
            "生产日期",
            "产品编号/批号",
        ]

        field_values = {
            "型号规格": third_page_fields.model_spec,
            "生产日期": third_page_fields.production_date,
            "产品编号/批号": third_page_fields.product_id_batch,
            "委托方": third_page_fields.client,
            "委托方地址": third_page_fields.client_address,
        }

        # Check if all three fields are "见样品描述栏"
        all_see_sample_desc = all(
            self._is_see_sample_desc(field_values.get(field, ""))
            for field in see_sample_desc_fields
        )

        none_see_sample_desc = all(
            not self._is_see_sample_desc(field_values.get(field, ""))
            for field in see_sample_desc_fields
        )

        # Partial "见样品描述栏" - this is an error
        if not all_see_sample_desc and not none_see_sample_desc:
            for field_name in see_sample_desc_fields:
                results.append(
                    C02Result(
                        check_id="C02",
                        status=CheckStatus.ERROR,
                        message=f"{field_name}字段必须统一：全部为'见样品描述栏'或全部不是",
                        field_name=field_name,
                        source_a=field_values.get(field_name, ""),
                        source_b="",
                    )
                )
            return results

        # If all three are "见样品描述栏", skip them with PASS
        if all_see_sample_desc:
            for field_name in see_sample_desc_fields:
                results.append(
                    C02Result(
                        check_id="C02",
                        status=CheckStatus.PASS,
                        message=f"{field_name}为'见样品描述栏'，跳过比对",
                        field_name=field_name,
                        source_a=field_values.get(field_name, ""),
                        source_b="N/A",
                    )
                )

        # Rule 2: Compare fields with label OCR
        fields_to_compare = []

        if all_see_sample_desc:
            # Only compare 委托方 and 委托方地址
            fields_to_compare = ["委托方", "委托方地址"]
        else:
            # Compare all five fields
            fields_to_compare = [
                "型号规格",
                "生产日期",
                "产品编号/批号",
                "委托方",
                "委托方地址",
            ]

        for field_name in fields_to_compare:
            page_value = field_values.get(field_name, "")

            # Get corresponding OCR value
            ocr_value = self._get_ocr_field_value(
                field_name,
                ocr_result,
            )

            # Compare
            values_match = (
                self._address_equals(page_value, ocr_value)
                if field_name == "委托方地址"
                else (
                    self._client_equals(page_value, ocr_value)
                    if field_name == "委托方"
                    else (
                        self._model_spec_equals(page_value, ocr_value)
                        if field_name == "型号规格"
                        else self._strict_equals(page_value, ocr_value)
                    )
                )
            )
            if values_match:
                status = CheckStatus.PASS
                message = f"{field_name}一致: {page_value}"
            else:
                status = CheckStatus.ERROR
                message = f"{field_name}不一致: 页面='{page_value}' vs 标签='{ocr_value}'"

            results.append(
                C02Result(
                    check_id="C02",
                    status=status,
                    message=message,
                    field_name=field_name,
                    source_a=page_value,
                    source_b=ocr_value,
                    details={
                        "label_caption": caption_info.raw_caption,
                    },
                )
            )

        return results

    def check_c03_production_date_format(
        self,
        third_page_fields: ThirdPageFields,
        label_ocr_results: list[tuple[CaptionInfo, LabelOCRResult]],
        sample_name: str,
    ) -> C03Result:
        """Check C03: Production date format and value consistency.

        Only triggered when third page production date is NOT "见样品描述栏".

        Args:
            third_page_fields: Fields from third page
            label_ocr_results: List of (caption info, OCR result) from photo pages
            sample_name: Sample name to match labels

        Returns:
            C03 result
        """
        # Get production date from third page
        page_date = third_page_fields.production_date or third_page_fields.model_spec
        if not page_date:
            return C03Result(
                check_id="C03",
                status=CheckStatus.WARNING,
                message="第三页未提取到生产日期，无法执行格式与值核对",
                page_value="",
                label_value="N/A",
                warnings=["第三页生产日期缺失"],
            )

        # Check if this is "见样品描述栏"
        if self._is_see_sample_desc(page_date):
            return C03Result(
                check_id="C03",
                status=CheckStatus.SKIPPED,
                message="生产日期为'见样品描述栏'，跳过格式核对",
                page_value=page_date,
                label_value="N/A",
            )

        # Find matching label
        matching_label = self._find_matching_label(
            label_ocr_results,
            sample_name,
        )

        if not matching_label:
            return C03Result(
                check_id="C03",
                status=CheckStatus.WARNING,
                message=f"未找到与样品名称'{sample_name}'匹配的中文标签，无法核对格式",
                page_value=page_date,
                label_value="N/A",
                warnings=["无匹配标签"],
            )

        _, ocr_result = matching_label
        label_date = ocr_result.fields.get("production_date", "")

        if not label_date:
            return C03Result(
                check_id="C03",
                status=CheckStatus.WARNING,
                message="标签未提取到生产日期，无法核对格式",
                page_value=page_date,
                label_value="N/A",
                warnings=["标签无生产日期字段"],
            )

        # Parse formats
        page_format = self._extract_date_format(page_date)
        label_format = self._extract_date_format(label_date)

        # Parse values
        page_date_obj = self._parse_date(page_date)
        label_date_obj = self._parse_date(label_date)

        # Compare format and value
        if page_format != label_format:
            return C03Result(
                check_id="C03",
                status=CheckStatus.ERROR,
                message=f"生产日期格式不一致: 页面='{page_date}' (格式:{page_format}) vs 标签='{label_date}' (格式:{label_format})",
                page_format=page_format,
                label_format=label_format,
                page_value=page_date,
                label_value=label_date,
                details={
                    "format_match": False,
                    "value_match": False,
                },
            )

        if page_date_obj != label_date_obj:
            return C03Result(
                check_id="C03",
                status=CheckStatus.ERROR,
                message=f"生产日期值不一致: 页面='{page_date}' vs 标签='{label_date}'",
                page_format=page_format,
                label_format=label_format,
                page_value=page_date,
                label_value=label_date,
                details={
                    "format_match": True,
                    "value_match": False,
                },
            )

        return C03Result(
            check_id="C03",
            status=CheckStatus.PASS,
            message=f"生产日期一致: {page_date}",
            page_format=page_format,
            label_format=label_format,
            page_value=page_date,
            label_value=label_date,
            details={
                "format_match": True,
                "value_match": True,
            },
        )

    def _find_matching_label(
        self,
        label_ocr_results: list[tuple[CaptionInfo, LabelOCRResult]],
        sample_name: str,
    ) -> tuple[CaptionInfo, LabelOCRResult] | None:
        """Find label whose caption main name matches sample name.

        Args:
            label_ocr_results: List of (caption info, OCR result)
            sample_name: Sample name to match

        Returns:
            Matching (caption info, OCR result) or None
        """
        normalized_sample = self._normalize_label_name(sample_name)
        if not normalized_sample:
            return None

        for caption_info, ocr_result in label_ocr_results:
            if caption_info.is_chinese_label:
                caption_main = self._normalize_label_name(caption_info.main_name)
                caption_raw = self._normalize_label_name(caption_info.raw_caption)

                # Support exact match and partial match
                if (
                    (caption_main and (
                        caption_main == normalized_sample
                        or normalized_sample in caption_main
                        or caption_main in normalized_sample
                    ))
                    or (caption_raw and (
                        caption_raw == normalized_sample
                        or normalized_sample in caption_raw
                        or caption_raw in normalized_sample
                    ))
                ):
                    return caption_info, ocr_result

        return None

    def _normalize_label_name(self, text: str) -> str:
        """Normalize label/sample names for robust matching.

        Removes caption indices and category suffixes to align names like:
        "№2 一次性使用... 中文标签" <-> "一次性使用..."
        """
        normalized = self._normalize_for_comparison(text)
        normalized = re.sub(r"^(?:№|no\.?|图|photo|plate|fig\.?)\s*\d+\s*", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(中文标签样张|中文标签|标签样张|标签)$", "", normalized)
        normalized = re.sub(r"\s+", "", normalized)
        return normalized.strip()

    def _get_ocr_field_value(
        self,
        field_name: str,
        ocr_result: LabelOCRResult,
    ) -> str:
        """Get OCR value for a third page field.

        Maps third page field names to OCR label field names.

        Args:
            field_name: Third page field name
            ocr_result: OCR result from label

        Returns:
            OCR field value
        """
        if field_name not in self.FIELD_MAPPINGS:
            return ""

        # Try each OCR field name
        for ocr_field in self.FIELD_MAPPINGS[field_name]:
            value = ocr_result.fields.get(ocr_field)
            if value:
                return value

        # Backward-compatible fallback for alias-based keys.
        legacy_aliases = {
            "型号规格": ["型号", "规格", "规格型号", "Model", "Spec"],
            "生产日期": ["生产日期", "MFG", "MFD", "Manufacturing Date"],
            "产品编号/批号": ["批号", "LOT", "Lot Number", "序列号", "SN", "Serial Number"],
            "委托方": ["注册人", "注册人名称"],
            "委托方地址": ["注册人住所", "注册人地址"],
        }
        for alias in legacy_aliases.get(field_name, []):
            value = ocr_result.fields.get(alias)
            if value:
                return value

        return ""

    def _extract_date_format(self, date_str: str) -> str:
        """Extract date format pattern from date string.

        Args:
            date_str: Date string

        Returns:
            Format pattern (e.g., "YYYY.MM.DD", "YYYY/MM/DD", "YYYY-MM-DD")
        """
        compact = (date_str or "").strip()
        if re.fullmatch(r"\d{8}", compact):
            return "YYYYMMDD"

        # Common date separators
        if "." in date_str:
            return "YYYY.MM.DD"
        elif "/" in date_str:
            return "YYYY/MM/DD"
        elif "-" in date_str:
            return "YYYY-MM-DD"
        else:
            return "UNKNOWN"

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date string to datetime object.

        Args:
            date_str: Date string

        Returns:
            Datetime object or None if parsing fails
        """
        # Common date formats
        formats = [
            "%Y%m%d",
            "%Y.%m.%d",
            "%Y/%m/%d",
            "%Y-%m-%d",
            "%Y.%m.%d",
            "%Y/%m/%d",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def run_all_checks(
        self,
        first_page_fields: dict[str, str],
        third_page_fields: ThirdPageFields,
        label_ocr_results: list[tuple[CaptionInfo, LabelOCRResult]],
    ) -> dict[str, list[CheckResult]]:
        """Run all C01-C03 checks.

        Args:
            first_page_fields: Fields from first page
            third_page_fields: Fields from third page
            label_ocr_results: List of (caption info, OCR result) from photo pages

        Returns:
            Dictionary with check_id as key and list of results as value
        """
        results: dict[str, list[CheckResult]] = {
            "C01": [],
            "C02": [],
            "C03": [],
        }

        # C01: First page vs third page field consistency
        c01_results = self.check_c01_field_consistency(
            first_page_fields,
            third_page_fields,
        )
        results["C01"].extend(c01_results)

        # C02: Third page extended field checks
        c02_results = self.check_c02_extended_fields(
            third_page_fields,
            label_ocr_results,
            third_page_fields.sample_name,
        )
        results["C02"].extend(c02_results)

        # C03: Production date format consistency
        c03_result = self.check_c03_production_date_format(
            third_page_fields,
            label_ocr_results,
            third_page_fields.sample_name,
        )
        results["C03"].append(c03_result)

        return results


def create_third_page_checker(
    ocr_service: OCRService | None = None,
) -> ThirdPageChecker:
    """Create third page checker instance.

    Args:
        ocr_service: Optional OCR service

    Returns:
        ThirdPageChecker instance
    """
    return ThirdPageChecker(ocr_service=ocr_service)


async def check_third_page_fields(
    first_page_fields: dict[str, str],
    third_page_fields: ThirdPageFields,
    label_ocr_results: list[tuple[CaptionInfo, LabelOCRResult]],
) -> dict[str, list[CheckResult]]:
    """Convenience function to run all third page checks.

    Args:
        first_page_fields: Fields from first page
        third_page_fields: Fields from third page
        label_ocr_results: List of (caption info, OCR result) from photo pages

    Returns:
        Dictionary with check results
    """
    checker = create_third_page_checker()
    return checker.run_all_checks(
        first_page_fields,
        third_page_fields,
        label_ocr_results,
    )
