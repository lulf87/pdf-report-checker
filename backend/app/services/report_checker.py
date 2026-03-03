"""
Report Checker for Report Self-Check (C04-C06).

Handles sample description table OCR comparison, photo coverage checks,
and Chinese label coverage checks.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.models.report_models import InspectionItem, InspectionTable
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
        check_id: Check identifier (e.g., C04, C05, C06)
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
class C04FieldCheckResult(CheckResult):
    """Result of a single field check in C04.

    Attributes:
        component_name: Name of the component
        field_name: Name of the field being checked
    """

    component_name: str = ""
    field_name: str = ""


@dataclass
class C04Result(CheckResult):
    """Result of C04: Sample description table check."""

    field_results: list[C04FieldCheckResult] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any field check has errors."""
        return any(r.status == CheckStatus.ERROR for r in self.field_results)


@dataclass
class C05Result(CheckResult):
    """Result of C05: Photo coverage check.

    Attributes:
        component_name: Name of the component
        matched_captions: List of matched photo captions
    """

    component_name: str = ""
    matched_captions: list[str] = field(default_factory=list)


@dataclass
class C06Result(CheckResult):
    """Result of C06: Chinese label coverage check.

    Attributes:
        component_name: Name of the component
        matched_captions: List of matched Chinese label captions
    """

    component_name: str = ""
    matched_captions: list[str] = field(default_factory=list)


@dataclass
class ComponentRow:
    """A row from the sample description table.

    Attributes:
        sequence_number: Sequence number (序号)
        component_name: Component name (部件名称)
        model_spec: Model/specification (规格型号)
        serial_lot: Serial/lot number (序列号批号)
        production_date: Production date (生产日期)
        expiration_date: Expiration date (失效日期)
        remark: Remarks (备注)
    """

    sequence_number: str = ""
    component_name: str = ""
    model_spec: str = ""
    serial_lot: str = ""
    production_date: str = ""
    expiration_date: str = ""
    remark: str = ""

    @property
    def is_not_used_in_test(self) -> bool:
        """Check if this component is marked as not used in testing."""
        return "本次检测未使用" in self.remark

    def get_non_empty_fields_key(self) -> str:
        """Get a key based on non-empty fields for matching.

        Returns:
            A string key combining all non-empty field values
        """
        fields = [
            self.component_name,
            self.model_spec,
            self.serial_lot,
            self.production_date,
            self.expiration_date,
        ]
        non_empty = [f for f in fields if f and f.strip() and f not in ("/", "——")]
        return "|".join(non_empty) if non_empty else self.component_name


class ReportChecker:
    """Checker for report self-check C04-C06.

    Performs checks for:
    - C04: Sample description table vs label OCR comparison
    - C05: Photo coverage check
    - C06: Chinese label coverage check
    """

    # Column name synonyms for C04
    COLUMN_SYNONYMS: dict[str, list[str]] = {
        "部件名称": ["部件名称", "产品名称", "名称", "Component", "Product"],
        "规格型号": ["规格型号", "型号规格", "型号", "规格", "Model", "Spec"],
        "序列号批号": [
            "序列号批号",
            "序列号/批号",
            "批号",
            "序列号",
            "SN",
            "LOT",
            "Lot",
            "Serial",
        ],
        "生产日期": ["生产日期", "MFG", "MFD", "Manufacturing Date"],
        "失效日期": ["失效日期", "有效期至", "EXP", "Expiration"],
    }

    # Fields to exclude from comparison
    IGNORED_COLUMNS = {"序号", "备注"}

    # Keywords indicating Chinese labels for C06
    CHINESE_LABEL_KEYWORDS = [
        "中文标签",
        "标签样张",
        "中文标签样张",
        "铭牌",
        "标牌",
    ]

    def __init__(
        self,
        ocr_service: OCRService | None = None,
        normalizer: TextNormalizer | None = None,
    ):
        """Initialize report checker.

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
        if not text:
            return ""
        return self.normalizer.normalize(text).strip()

    def _normalize_name_for_match(self, text: str) -> str:
        """Normalize component/caption name for robust matching."""
        normalized = self._normalize_for_comparison(text)
        normalized = re.sub(r"\s+", "", normalized)

        # Remove common caption suffixes/orientations, but preserve core names
        # (e.g. "主机" should not be stripped to empty).
        suffixes = [
            "中文标签样张",
            "中文标签",
            "标签样张",
            "标签",
            "主机背面",
            "主机正面",
            "主机侧面",
            "背面",
            "正面",
            "侧面",
            "照片",
        ]
        for suffix in suffixes:
            if normalized.endswith(suffix) and len(normalized) > len(suffix):
                normalized = normalized[: -len(suffix)]

        # Only trim trailing "主机" when there is descriptive prefix.
        if normalized.endswith("主机") and len(normalized) > 2:
            normalized = normalized[:-2]

        return normalized.strip()

    def _is_empty_value(self, value: str) -> bool:
        """Check if value is considered empty.

        Args:
            value: Value to check

        Returns:
            True if value is empty or equivalent to empty
        """
        if not value:
            return True
        normalized = value.strip()
        return normalized in ("", "/", "——", "-")

    def _values_match(self, table_value: str, label_value: str) -> bool:
        """Compare table value with label value.

        Args:
            table_value: Value from sample description table
            label_value: Value from OCR label

        Returns:
            True if values match (with normalization)
        """
        # Handle empty values - both empty means match
        table_empty = self._is_empty_value(table_value)
        label_empty = self._is_empty_value(label_value)

        if table_empty and label_empty:
            return True

        if table_empty != label_empty:
            return False

        # Both non-empty, compare strictly (character-level).
        return table_value.strip() == label_value.strip()

    def _find_standard_column_name(
        self, header: str, available_headers: list[str]
    ) -> str | None:
        """Find the standard column name from a header.

        Args:
            header: Header text to match
            available_headers: List of available headers

        Returns:
            Standard column name or None
        """
        normalized_header = self._normalize_for_comparison(header)

        for standard_name, synonyms in self.COLUMN_SYNONYMS.items():
            if standard_name in available_headers:
                # Direct match with standard name
                if self._normalize_for_comparison(standard_name) == normalized_header:
                    return standard_name
            # Check synonyms
            for synonym in synonyms:
                if self._normalize_for_comparison(synonym) == normalized_header:
                    return standard_name

        return None

    def _parse_sample_description_table(
        self, table: InspectionTable
    ) -> list[ComponentRow]:
        """Parse sample description table from inspection table.

        Args:
            table: Inspection table to parse

        Returns:
            List of ComponentRow objects
        """
        components: list[ComponentRow] = []

        # Map table headers to standard column names
        header_mapping: dict[str, str] = {}
        if table.headers:
            for i, header in enumerate(table.headers):
                standard_name = self._find_standard_column_name(header, table.headers)
                if standard_name:
                    header_mapping[standard_name] = i

        # If no headers found, use default positions
        if not header_mapping:
            # Default column order: 序号, 部件名称, 规格型号, 序列号批号, 生产日期, 失效日期, 备注
            default_headers = ["序号", "部件名称", "规格型号", "序列号批号", "生产日期", "失效日期", "备注"]
            for i, h in enumerate(default_headers):
                header_mapping[h] = i

        # Parse each item as a component row
        for item in table.items:
            # Get component name from inspection_project or a dedicated column
            component_name = item.inspection_project

            # Try to extract from standard_requirement if inspection_project is empty
            if not component_name:
                # Parse from inspection table text
                component_name = item.standard_requirement.split("\n")[0] if item.standard_requirement else ""

            row = ComponentRow(
                sequence_number=item.sequence_number,
                component_name=component_name,
                remark=item.remark,
            )

            # Extract other fields from standard_requirement if available
            if item.standard_requirement:
                lines = item.standard_requirement.split("\n")
                for line in lines:
                    line = line.strip()
                    if ":" in line or "：" in line:
                        parts = re.split(r"[:：]", line, maxsplit=1)
                        if len(parts) == 2:
                            field_name = parts[0].strip()
                            field_value = parts[1].strip()

                            # Map to standard fields
                            for standard_name, synonyms in self.COLUMN_SYNONYMS.items():
                                if field_name in synonyms or field_name == standard_name:
                                    if standard_name == "规格型号":
                                        row.model_spec = field_value
                                    elif standard_name == "序列号批号":
                                        row.serial_lot = field_value
                                    elif standard_name == "生产日期":
                                        row.production_date = field_value
                                    elif standard_name == "失效日期":
                                        row.expiration_date = field_value

            components.append(row)

        return components

    def check_c04_sample_description(
        self,
        sample_description_table: list[ComponentRow] | InspectionTable,
        label_ocr_results: list[tuple[CaptionInfo, LabelOCRResult]],
    ) -> C04Result:
        """Check C04: Sample description table vs label OCR.

        Args:
            sample_description_table: Component rows or inspection table
            label_ocr_results: List of (caption info, OCR result) from photo pages

        Returns:
            C04Result with all field check results
        """
        result = C04Result(check_id="C04", status=CheckStatus.PASS)

        # Parse components if inspection table is provided
        if isinstance(sample_description_table, InspectionTable):
            components = self._parse_sample_description_table(sample_description_table)
        else:
            components = sample_description_table

        if not components:
            result.add_warning("样品描述表格为空")
            return result

        # Create a map of component names to their OCR results
        label_map: dict[str, list[tuple[CaptionInfo, LabelOCRResult]]] = {}
        for caption_info, ocr_result in label_ocr_results:
            if caption_info.is_chinese_label:
                main_name = caption_info.main_name
                if main_name not in label_map:
                    label_map[main_name] = []
                label_map[main_name].append((caption_info, ocr_result))

        # Check each component
        for component in components:
            if not component.component_name:
                continue

            # Find matching labels for this component
            matching_labels = self._find_matching_labels_for_component(
                component, label_map
            )

            if not matching_labels:
                # No matching label - add warning for each field
                for field_name in ["规格型号", "序列号批号", "生产日期", "失效日期"]:
                    field_result = C04FieldCheckResult(
                        check_id="C04",
                        component_name=component.component_name,
                        field_name=field_name,
                        status=CheckStatus.WARNING,
                        message=f"未找到部件'{component.component_name}'的中文标签",
                        source_a=self._get_component_field_value(component, field_name),
                        source_b="N/A",
                    )
                    result.field_results.append(field_result)
                result.add_warning(f"部件'{component.component_name}'无匹配标签")
                continue

            # Check each field against all matching labels
            for field_name in ["规格型号", "序列号批号", "生产日期", "失效日期"]:
                table_value = self._get_component_field_value(component, field_name)

                # Try to find a label that matches
                match_found = False
                for caption_info, ocr_result in matching_labels:
                    label_value = self._get_ocr_field_value(field_name, ocr_result)

                    if self._values_match(table_value, label_value):
                        match_found = True
                        # Field matches
                        field_result = C04FieldCheckResult(
                            check_id="C04",
                            component_name=component.component_name,
                            field_name=field_name,
                            status=CheckStatus.PASS,
                            message=f"{component.component_name} - {field_name}: 一致",
                            source_a=table_value,
                            source_b=label_value,
                        )
                        result.field_results.append(field_result)
                        break
                    elif table_value or label_value:
                        # Values don't match but at least one is non-empty
                        pass

                if not match_found:
                    # Check if both are empty (pass) or not (error)
                    best_label_value = ""
                    if matching_labels:
                        # Use the first matching label's value
                        best_label_value = self._get_ocr_field_value(
                            field_name, matching_labels[0][1]
                        )

                    if self._is_empty_value(table_value) and self._is_empty_value(
                        best_label_value
                    ):
                        status = CheckStatus.PASS
                        message = f"{component.component_name} - {field_name}: 均为空"
                    else:
                        status = CheckStatus.ERROR
                        message = (
                            f"{component.component_name} - {field_name}: 不一致 - "
                            f"表格='{table_value}' vs 标签='{best_label_value}'"
                        )
                        result.status = CheckStatus.ERROR

                    field_result = C04FieldCheckResult(
                        check_id="C04",
                        component_name=component.component_name,
                        field_name=field_name,
                        status=status,
                        message=message,
                        source_a=table_value,
                        source_b=best_label_value,
                    )
                    result.field_results.append(field_result)

        # Update overall message
        error_count = sum(1 for r in result.field_results if r.status == CheckStatus.ERROR)
        warning_count = sum(1 for r in result.field_results if r.status == CheckStatus.WARNING)

        if error_count > 0:
            result.message = f"C04 核对完成：{error_count} 个错误，{warning_count} 个警告"
        elif warning_count > 0:
            result.message = f"C04 核对完成：{warning_count} 个警告"
        else:
            result.message = "C04 核对完成：全部一致"

        return result

    def check_c05_photo_coverage(
        self,
        sample_description_table: list[ComponentRow] | InspectionTable,
        photo_captions: list[str],
    ) -> list[C05Result]:
        """Check C05: Photo coverage for each component.

        Args:
            sample_description_table: Component rows or inspection table
            photo_captions: List of photo caption texts

        Returns:
            List of C05Result for each component
        """
        results: list[C05Result] = []

        # Parse components if inspection table is provided
        if isinstance(sample_description_table, InspectionTable):
            components = self._parse_sample_description_table(sample_description_table)
        else:
            components = sample_description_table

        # Parse photo captions to extract main names
        photo_main_names: list[str] = []
        for caption in photo_captions:
            main_name = self.ocr_service.extract_main_name_from_caption(caption)
            if main_name:
                photo_main_names.append(main_name)

        # Check each component
        for component in components:
            if not component.component_name:
                continue

            # Skip if marked as not used
            if component.is_not_used_in_test:
                results.append(
                    C05Result(
                        check_id="C05",
                        component_name=component.component_name,
                        status=CheckStatus.SKIPPED,
                        message=f"{component.component_name}: 标记为'本次检测未使用'，跳过照片检查",
                        matched_captions=[],
                    )
                )
                continue

            # Find matching photos
            matched = self._find_matching_captions(
                component.component_name, photo_main_names
            )

            if matched:
                results.append(
                    C05Result(
                        check_id="C05",
                        component_name=component.component_name,
                        status=CheckStatus.PASS,
                        message=f"{component.component_name}: 有 {len(matched)} 张照片覆盖",
                        matched_captions=matched,
                    )
                )
            else:
                results.append(
                    C05Result(
                        check_id="C05",
                        component_name=component.component_name,
                        status=CheckStatus.ERROR,
                        message=f"{component.component_name}: 无照片覆盖",
                        matched_captions=[],
                    )
                )

        return results

    def check_c06_chinese_label_coverage(
        self,
        sample_description_table: list[ComponentRow] | InspectionTable,
        label_ocr_results: list[tuple[CaptionInfo, LabelOCRResult]],
    ) -> list[C06Result]:
        """Check C06: Chinese label coverage for each component.

        Args:
            sample_description_table: Component rows or inspection table
            label_ocr_results: List of (caption info, OCR result) from photo pages

        Returns:
            List of C06Result for each component
        """
        results: list[C06Result] = []

        # Parse components if inspection table is provided
        if isinstance(sample_description_table, InspectionTable):
            components = self._parse_sample_description_table(sample_description_table)
        else:
            components = sample_description_table

        # Create a map of component names to their Chinese labels
        label_map: dict[str, list[tuple[CaptionInfo, LabelOCRResult]]] = {}
        for caption_info, ocr_result in label_ocr_results:
            if caption_info.is_chinese_label:
                main_name = caption_info.main_name
                if main_name not in label_map:
                    label_map[main_name] = []
                label_map[main_name].append((caption_info, ocr_result))

        # Group same-name components to support non-empty-field composite-key matching.
        grouped_components: dict[str, list[ComponentRow]] = {}
        for component in components:
            if not component.component_name:
                continue
            grouped_components.setdefault(component.component_name, []).append(component)

        for component_name, same_name_components in grouped_components.items():
            caption_name_matches = self._find_matching_captions(component_name, list(label_map.keys()))
            candidates: list[tuple[CaptionInfo, LabelOCRResult]] = []
            for match_name in caption_name_matches:
                candidates.extend(label_map.get(match_name, []))

            used_candidate_indexes: set[int] = set()

            for component in same_name_components:
                if component.is_not_used_in_test:
                    results.append(
                        C06Result(
                            check_id="C06",
                            component_name=component.component_name,
                            status=CheckStatus.SKIPPED,
                            message=f"{component.component_name}: 标记为'本次检测未使用'，跳过标签检查",
                            matched_captions=[],
                        )
                    )
                    continue

                matched_indexes: list[int] = []
                for idx, (_, ocr_result) in enumerate(candidates):
                    if idx in used_candidate_indexes:
                        continue
                    if self._component_matches_label(component, ocr_result):
                        matched_indexes.append(idx)

                if matched_indexes:
                    selected_idx = matched_indexes[0]
                    used_candidate_indexes.add(selected_idx)
                    caption = candidates[selected_idx][0].raw_caption
                    results.append(
                        C06Result(
                            check_id="C06",
                            component_name=component.component_name,
                            status=CheckStatus.PASS,
                            message=f"{component.component_name}: 有中文标签覆盖",
                            matched_captions=[caption],
                        )
                    )
                else:
                    results.append(
                        C06Result(
                            check_id="C06",
                            component_name=component.component_name,
                            status=CheckStatus.ERROR,
                            message=f"{component.component_name}: 无中文标签",
                            matched_captions=[],
                        )
                    )

        return results

    def _component_matches_label(
        self,
        component: ComponentRow,
        ocr_result: LabelOCRResult,
    ) -> bool:
        """Match by non-empty component fields (composite key)."""
        field_pairs = [
            ("规格型号", component.model_spec),
            ("序列号批号", component.serial_lot),
            ("生产日期", component.production_date),
            ("失效日期", component.expiration_date),
        ]

        has_non_empty = False
        comparable_count = 0
        for field_name, component_value in field_pairs:
            if self._is_empty_value(component_value):
                continue
            has_non_empty = True
            label_value = self._get_ocr_field_value(field_name, ocr_result)
            if self._is_empty_value(label_value):
                # OCR may miss one field; defer to other non-empty fields.
                continue
            comparable_count += 1
            if not self._values_match(component_value, label_value):
                return False

        # If all comparable non-empty fields match, or there are no non-empty
        # fields (fallback to name-based candidate matching), treat as matched.
        if not has_non_empty:
            return True
        return comparable_count > 0

    def _find_matching_labels_for_component(
        self,
        component: ComponentRow,
        label_map: dict[str, list[tuple[CaptionInfo, LabelOCRResult]]],
    ) -> list[tuple[CaptionInfo, LabelOCRResult]]:
        """Find matching labels for a component.

        Args:
            component: Component row to find labels for
            label_map: Map of main names to label results

        Returns:
            List of matching (caption info, OCR result)
        """
        if not component.component_name:
            return []

        normalized_component = self._normalize_name_for_match(component.component_name)
        if not normalized_component:
            return []
        matched: list[tuple[CaptionInfo, LabelOCRResult]] = []

        for main_name, labels in label_map.items():
            normalized_name = self._normalize_name_for_match(main_name)
            if not normalized_name:
                continue

            # Check if one contains the other
            if (
                normalized_component == normalized_name
                or (
                    normalized_component in normalized_name
                    or normalized_name in normalized_component
                )
            ):
                matched.extend(labels)

        return matched

    def _find_matching_captions(
        self, component_name: str, caption_names: list[str]
    ) -> list[str]:
        """Find matching captions for a component.

        Args:
            component_name: Component name to match
            caption_names: List of caption main names

        Returns:
            List of matching caption names
        """
        normalized_component = self._normalize_name_for_match(component_name)
        if not normalized_component:
            return []
        matched: list[str] = []

        for caption_name in caption_names:
            normalized_caption = self._normalize_name_for_match(caption_name)
            if not normalized_caption:
                continue

            # Exact match
            if normalized_component == normalized_caption:
                matched.append(caption_name)
            # Partial match - component name in caption or vice versa
            elif (
                normalized_component in normalized_caption
                or normalized_caption in normalized_component
            ):
                matched.append(caption_name)

        return matched

    def _get_component_field_value(
        self, component: ComponentRow, field_name: str
    ) -> str:
        """Get field value from component row.

        Args:
            component: Component row
            field_name: Standard field name

        Returns:
            Field value
        """
        if field_name == "部件名称":
            return component.component_name
        elif field_name == "规格型号":
            return component.model_spec
        elif field_name == "序列号批号":
            return component.serial_lot
        elif field_name == "生产日期":
            return component.production_date
        elif field_name == "失效日期":
            return component.expiration_date
        return ""

    def _get_ocr_field_value(
        self, field_name: str, ocr_result: LabelOCRResult
    ) -> str:
        """Get OCR value for a field.

        Args:
            field_name: Standard field name
            ocr_result: OCR result from label

        Returns:
            OCR field value
        """
        if field_name not in self.COLUMN_SYNONYMS:
            return ""

        # Try each OCR field name synonym
        for synonym in self.COLUMN_SYNONYMS[field_name]:
            # Map to internal field names used by OCR service
            internal_field = self._map_to_internal_field(synonym)
            if internal_field and ocr_result.has_field(internal_field):
                return ocr_result.get_field(internal_field) or ""

            # Also try direct field name
            if ocr_result.has_field(synonym):
                return ocr_result.get_field(synonym) or ""

        return ""

    def _map_to_internal_field(self, synonym: str) -> str | None:
        """Map column synonym to internal OCR field name.

        Args:
            synonym: Column synonym

        Returns:
            Internal field name or None
        """
        mapping = {
            "型号": "model_spec",
            "规格": "model_spec",
            "Model": "model_spec",
            "Spec": "model_spec",
            "批号": "batch_number",
            "LOT": "batch_number",
            "Lot": "batch_number",
            "序列号": "serial_number",
            "SN": "serial_number",
            "Serial": "serial_number",
            "MFG": "production_date",
            "MFD": "production_date",
            "Manufacturing Date": "production_date",
            "有效期至": "expiration_date",
            "EXP": "expiration_date",
            "Expiration": "expiration_date",
        }
        return mapping.get(synonym)

    def run_all_checks(
        self,
        sample_description_table: list[ComponentRow] | InspectionTable,
        label_ocr_results: list[tuple[CaptionInfo, LabelOCRResult]],
        photo_captions: list[str],
    ) -> dict[str, list[CheckResult]]:
        """Run all C04-C06 checks.

        Args:
            sample_description_table: Component rows or inspection table
            label_ocr_results: List of (caption info, OCR result) from photo pages
            photo_captions: List of photo caption texts

        Returns:
            Dictionary with check_id as key and list of results as value
        """
        results: dict[str, list[CheckResult]] = {
            "C04": [],
            "C05": [],
            "C06": [],
        }

        # C04: Sample description table check
        c04_result = self.check_c04_sample_description(
            sample_description_table,
            label_ocr_results,
        )
        results["C04"].append(c04_result)

        # C05: Photo coverage check
        c05_results = self.check_c05_photo_coverage(
            sample_description_table,
            photo_captions,
        )
        results["C05"].extend(c05_results)

        # C06: Chinese label coverage check
        c06_results = self.check_c06_chinese_label_coverage(
            sample_description_table,
            label_ocr_results,
        )
        results["C06"].extend(c06_results)

        return results


def create_report_checker(
    ocr_service: OCRService | None = None,
) -> ReportChecker:
    """Create report checker instance.

    Args:
        ocr_service: Optional OCR service

    Returns:
        ReportChecker instance
    """
    return ReportChecker(ocr_service=ocr_service)
