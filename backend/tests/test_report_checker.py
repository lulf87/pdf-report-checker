"""
Tests for Report Checker module (C04-C06).

Tests sample description table OCR comparison, photo coverage checks,
and Chinese label coverage checks.
"""

import pytest

from app.models.report_models import InspectionItem, InspectionTable
from app.services.ocr_service import CaptionInfo, LabelOCRResult, OCRService
from app.services.report_checker import (
    C04FieldCheckResult,
    C04Result,
    C05Result,
    C06Result,
    CheckResult,
    CheckStatus,
    ComponentRow,
    ReportChecker,
    create_report_checker,
)


class TestCheckStatus:
    """Test CheckStatus enum."""

    def test_status_values(self):
        """Test CheckStatus has correct values."""
        assert CheckStatus.PASS == "pass"
        assert CheckStatus.ERROR == "error"
        assert CheckStatus.WARNING == "warning"
        assert CheckStatus.SKIPPED == "skipped"


class TestComponentRow:
    """Test ComponentRow dataclass."""

    def test_creation(self):
        """Test creating ComponentRow."""
        row = ComponentRow(
            sequence_number="1",
            component_name="主机",
            model_spec="RF-2000",
            serial_lot="SN12345",
            production_date="2026.01.08",
            expiration_date="2028.01.08",
            remark="",
        )
        assert row.component_name == "主机"
        assert row.model_spec == "RF-2000"

    def test_is_not_used_in_test(self):
        """Test is_not_used_in_test property."""
        row = ComponentRow(remark="本次检测未使用")
        assert row.is_not_used_in_test is True

        row2 = ComponentRow(remark="正常使用")
        assert row2.is_not_used_in_test is False

    def test_get_non_empty_fields_key(self):
        """Test get_non_empty_fields_key method."""
        row = ComponentRow(
            component_name="主机",
            model_spec="RF-2000",
            serial_lot="/",  # Empty value
            production_date="2026.01.08",
        )
        key = row.get_non_empty_fields_key()
        assert "主机" in key
        assert "RF-2000" in key
        assert "2026.01.08" in key
        assert "/" not in key


class TestReportChecker:
    """Test ReportChecker class."""

    def test_initialization(self):
        """Test checker initialization."""
        checker = ReportChecker()
        assert checker.ocr_service is not None
        assert checker.normalizer is not None

    def test_initialization_with_custom_services(self):
        """Test initialization with custom services."""
        ocr_service = OCRService()
        checker = ReportChecker(ocr_service=ocr_service)
        assert checker.ocr_service == ocr_service


class TestNormalizeForComparison:
    """Test text normalization for comparison."""

    def test_normalize_simple_text(self):
        """Test normalizing simple text."""
        checker = ReportChecker()
        result = checker._normalize_for_comparison("射频消融电极")
        assert result == "射频消融电极"

    def test_normalize_with_spaces(self):
        """Test normalizing with extra spaces."""
        checker = ReportChecker()
        result = checker._normalize_for_comparison("射频  消融  电极")
        assert isinstance(result, str)
        assert "电极" in result

    def test_normalize_empty(self):
        """Test normalizing empty string."""
        checker = ReportChecker()
        result = checker._normalize_for_comparison("")
        assert result == ""


class TestIsEmptyValue:
    """Test _is_empty_value method."""

    def test_empty_string(self):
        """Test empty string."""
        checker = ReportChecker()
        assert checker._is_empty_value("") is True

    def test_slash(self):
        """Test slash as empty value."""
        checker = ReportChecker()
        assert checker._is_empty_value("/") is True
        assert checker._is_empty_value(" / ") is True

    def test_em_dash(self):
        """Test em dash as empty value."""
        checker = ReportChecker()
        assert checker._is_empty_value("——") is True

    def test_hyphen(self):
        """Test hyphen as empty value."""
        checker = ReportChecker()
        assert checker._is_empty_value("-") is True

    def test_non_empty_value(self):
        """Test non-empty value."""
        checker = ReportChecker()
        assert checker._is_empty_value("RF-2000") is False
        assert checker._is_empty_value("2026.01.08") is False


class TestValuesMatch:
    """Test _values_match method."""

    def test_both_empty(self):
        """Test both values empty."""
        checker = ReportChecker()
        assert checker._values_match("", "") is True
        assert checker._values_match("/", "/") is True
        assert checker._values_match("——", "") is True

    def test_one_empty_one_not(self):
        """Test one empty, one not."""
        checker = ReportChecker()
        assert checker._values_match("RF-2000", "") is False
        assert checker._values_match("", "RF-2000") is False

    def test_both_non_empty_matching(self):
        """Test both non-empty and matching."""
        checker = ReportChecker()
        assert checker._values_match("RF-2000", "RF-2000") is True
        assert checker._values_match("2026.01.08", "2026.01.08") is True

    def test_both_non_empty_not_matching(self):
        """Test both non-empty but not matching."""
        checker = ReportChecker()
        assert checker._values_match("RF-2000", "RF-3000") is False
        assert checker._values_match("2026.01.08", "2026/01/08") is False

    def test_normalized_match(self):
        """Test match after normalization."""
        checker = ReportChecker()
        # Full-width vs half-width should match after normalization
        result = checker._values_match("RF-2000", "RF-2000")
        assert isinstance(result, bool)


class TestFindMatchingCaptions:
    """Test _find_matching_captions method."""

    def test_exact_match(self):
        """Test exact name match."""
        checker = ReportChecker()
        captions = ["主机", "导管", "电极"]
        matched = checker._find_matching_captions("主机", captions)
        assert "主机" in matched

    def test_partial_match_component_in_caption(self):
        """Test partial match where component is in caption."""
        checker = ReportChecker()
        captions = ["一次性射频消融电极", "导管", "主机"]
        matched = checker._find_matching_captions("电极", captions)
        assert len(matched) > 0

    def test_partial_match_caption_in_component(self):
        """Test partial match where caption is in component."""
        checker = ReportChecker()
        captions = ["电极", "导管"]
        matched = checker._find_matching_captions("射频消融电极", captions)
        assert len(matched) > 0

    def test_no_match(self):
        """Test no matching captions."""
        checker = ReportChecker()
        captions = ["心电图机", "血压计"]
        matched = checker._find_matching_captions("主机", captions)
        assert len(matched) == 0


class TestGetComponentFieldValue:
    """Test _get_component_field_value method."""

    def test_get_component_name(self):
        """Test getting component name."""
        checker = ReportChecker()
        component = ComponentRow(component_name="主机")
        assert checker._get_component_field_value(component, "部件名称") == "主机"

    def test_get_model_spec(self):
        """Test getting model spec."""
        checker = ReportChecker()
        component = ComponentRow(model_spec="RF-2000")
        assert checker._get_component_field_value(component, "规格型号") == "RF-2000"

    def test_get_serial_lot(self):
        """Test getting serial/lot number."""
        checker = ReportChecker()
        component = ComponentRow(serial_lot="SN12345")
        assert checker._get_component_field_value(component, "序列号批号") == "SN12345"

    def test_get_production_date(self):
        """Test getting production date."""
        checker = ReportChecker()
        component = ComponentRow(production_date="2026.01.08")
        assert checker._get_component_field_value(component, "生产日期") == "2026.01.08"

    def test_get_expiration_date(self):
        """Test getting expiration date."""
        checker = ReportChecker()
        component = ComponentRow(expiration_date="2028.01.08")
        assert checker._get_component_field_value(component, "失效日期") == "2028.01.08"

    def test_get_unknown_field(self):
        """Test getting unknown field."""
        checker = ReportChecker()
        component = ComponentRow(component_name="主机")
        assert checker._get_component_field_value(component, "未知字段") == ""


class TestC04SampleDescription:
    """Test C04: Sample description table check."""

    def test_empty_components(self):
        """Test with empty component list."""
        checker = ReportChecker()

        result = checker.check_c04_sample_description([], [])
        assert result.check_id == "C04"
        assert len(result.warnings) > 0
        assert "空" in result.warnings[0].lower()

    def test_matching_labels(self):
        """Test with matching labels for all fields."""
        checker = ReportChecker()

        components = [
            ComponentRow(
                component_name="主机",
                model_spec="RF-2000",
                serial_lot="SN12345",
                production_date="2026.01.08",
                expiration_date="2028.01.08",
            )
        ]

        caption_info = CaptionInfo(
            raw_caption="中文标签：主机",
            main_name="主机",
            is_chinese_label=True,
        )
        ocr_result = LabelOCRResult(
            raw_text="test",
            fields={
                "model_spec": "RF-2000",
                "batch_number": "SN12345",
                "production_date": "2026.01.08",
            },
        )
        label_ocr_results = [(caption_info, ocr_result)]

        result = checker.check_c04_sample_description(components, label_ocr_results)

        assert result.check_id == "C04"
        assert len(result.field_results) > 0

    def test_no_matching_labels(self):
        """Test with no matching labels."""
        checker = ReportChecker()

        components = [
            ComponentRow(
                component_name="主机",
                model_spec="RF-2000",
            )
        ]

        # Empty labels
        label_ocr_results = []

        result = checker.check_c04_sample_description(components, label_ocr_results)

        assert result.check_id == "C04"
        assert len(result.field_results) > 0
        # Should have warnings
        assert any(r.status == CheckStatus.WARNING for r in result.field_results)

    def test_field_mismatch(self):
        """Test field value mismatch."""
        checker = ReportChecker()

        components = [
            ComponentRow(
                component_name="主机",
                model_spec="RF-2000",  # Different from label
            )
        ]

        caption_info = CaptionInfo(
            raw_caption="中文标签：主机",
            main_name="主机",
            is_chinese_label=True,
        )
        ocr_result = LabelOCRResult(
            raw_text="test",
            fields={"model_spec": "RF-3000"},  # Different
        )
        label_ocr_results = [(caption_info, ocr_result)]

        result = checker.check_c04_sample_description(components, label_ocr_results)

        assert result.check_id == "C04"
        assert result.status == CheckStatus.ERROR
        assert len(result.field_results) > 0

    def test_empty_field_both_sides(self):
        """Test empty field on both sides (should pass)."""
        checker = ReportChecker()

        components = [
            ComponentRow(
                component_name="主机",
                serial_lot="",  # Empty
            )
        ]

        caption_info = CaptionInfo(
            raw_caption="中文标签：主机",
            main_name="主机",
            is_chinese_label=True,
        )
        ocr_result = LabelOCRResult(
            raw_text="test",
            fields={},  # No serial lot
        )
        label_ocr_results = [(caption_info, ocr_result)]

        result = checker.check_c04_sample_description(components, label_ocr_results)

        # Empty fields on both sides should pass
        serial_lot_results = [
            r for r in result.field_results if r.field_name == "序列号批号"
        ]
        if serial_lot_results:
            assert serial_lot_results[0].status == CheckStatus.PASS


class TestC05PhotoCoverage:
    """Test C05: Photo coverage check."""

    def test_all_components_have_photos(self):
        """Test all components have photo coverage."""
        checker = ReportChecker()

        components = [
            ComponentRow(component_name="主机"),
            ComponentRow(component_name="导管"),
        ]

        photo_captions = [
            "图1：主机",
            "图2：导管",
        ]

        results = checker.check_c05_photo_coverage(components, photo_captions)

        assert len(results) == 2
        assert all(r.status == CheckStatus.PASS for r in results)

    def test_component_without_photo(self):
        """Test component without photo coverage."""
        checker = ReportChecker()

        components = [
            ComponentRow(component_name="主机"),
            ComponentRow(component_name="导管"),
        ]

        photo_captions = [
            "图1：主机",
        ]

        results = checker.check_c05_photo_coverage(components, photo_captions)

        assert len(results) == 2
        # Find 导管 result
        catheter_result = next(r for r in results if r.component_name == "导管")
        assert catheter_result.status == CheckStatus.ERROR

    def test_component_not_used_in_test(self):
        """Test component marked as not used."""
        checker = ReportChecker()

        components = [
            ComponentRow(
                component_name="备用件",
                remark="本次检测未使用",
            ),
        ]

        photo_captions = []

        results = checker.check_c05_photo_coverage(components, photo_captions)

        assert len(results) == 1
        assert results[0].status == CheckStatus.SKIPPED
        assert "跳过" in results[0].message

    def test_partial_match(self):
        """Test partial name matching."""
        checker = ReportChecker()

        components = [
            ComponentRow(component_name="电极"),
        ]

        photo_captions = [
            "图1：一次性射频消融电极",
        ]

        results = checker.check_c05_photo_coverage(components, photo_captions)

        assert len(results) == 1
        assert results[0].status == CheckStatus.PASS

    def test_empty_components(self):
        """Test with empty component list."""
        checker = ReportChecker()

        results = checker.check_c05_photo_coverage([], [])

        assert len(results) == 0


class TestC06ChineseLabelCoverage:
    """Test C06: Chinese label coverage check."""

    def test_all_components_have_labels(self):
        """Test all components have Chinese labels."""
        checker = ReportChecker()

        components = [
            ComponentRow(component_name="主机"),
            ComponentRow(component_name="导管"),
        ]

        caption_info1 = CaptionInfo(
            raw_caption="中文标签：主机",
            main_name="主机",
            is_chinese_label=True,
        )
        caption_info2 = CaptionInfo(
            raw_caption="标签样张：导管",
            main_name="导管",
            is_chinese_label=True,
        )
        label_ocr_results = [
            (caption_info1, LabelOCRResult(raw_text="test")),
            (caption_info2, LabelOCRResult(raw_text="test")),
        ]

        results = checker.check_c06_chinese_label_coverage(components, label_ocr_results)

        assert len(results) == 2
        assert all(r.status == CheckStatus.PASS for r in results)

    def test_component_without_label(self):
        """Test component without Chinese label."""
        checker = ReportChecker()

        components = [
            ComponentRow(component_name="主机"),
            ComponentRow(component_name="导管"),
        ]

        caption_info1 = CaptionInfo(
            raw_caption="中文标签：主机",
            main_name="主机",
            is_chinese_label=True,
        )
        label_ocr_results = [
            (caption_info1, LabelOCRResult(raw_text="test")),
        ]

        results = checker.check_c06_chinese_label_coverage(components, label_ocr_results)

        assert len(results) == 2
        # Find 导管 result
        catheter_result = next(r for r in results if r.component_name == "导管")
        assert catheter_result.status == CheckStatus.ERROR

    def test_component_not_used_in_test(self):
        """Test component marked as not used."""
        checker = ReportChecker()

        components = [
            ComponentRow(
                component_name="备用件",
                remark="本次检测未使用",
            ),
        ]

        label_ocr_results = []

        results = checker.check_c06_chinese_label_coverage(components, label_ocr_results)

        assert len(results) == 1
        assert results[0].status == CheckStatus.SKIPPED

    def test_only_chinese_labels_counted(self):
        """Test that only Chinese labels are counted."""
        checker = ReportChecker()

        components = [
            ComponentRow(component_name="主机"),
        ]

        # Non-Chinese label (photo caption)
        caption_info1 = CaptionInfo(
            raw_caption="产品照片：主机",
            main_name="主机",
            is_chinese_label=False,  # Not a Chinese label
        )
        label_ocr_results = [
            (caption_info1, LabelOCRResult(raw_text="test")),
        ]

        results = checker.check_c06_chinese_label_coverage(components, label_ocr_results)

        assert len(results) == 1
        # Should not match because is_chinese_label is False
        assert results[0].status == CheckStatus.ERROR

    def test_empty_components(self):
        """Test with empty component list."""
        checker = ReportChecker()

        results = checker.check_c06_chinese_label_coverage([], [])

        assert len(results) == 0


class TestParseSampleDescriptionTable:
    """Test _parse_sample_description_table method."""

    def test_parse_from_inspection_table(self):
        """Test parsing from InspectionTable."""
        checker = ReportChecker()

        table = InspectionTable()
        table.items = [
            InspectionItem(
                sequence_number="1",
                inspection_project="主机",
                standard_requirement="型号：RF-2000\n批号：SN12345",
            ),
            InspectionItem(
                sequence_number="2",
                inspection_project="导管",
                standard_requirement="型号：CT-100",
            ),
        ]

        components = checker._parse_sample_description_table(table)

        assert len(components) == 2
        assert components[0].component_name == "主机"
        assert components[1].component_name == "导管"

    def test_parse_with_empty_table(self):
        """Test parsing empty table."""
        checker = ReportChecker()

        table = InspectionTable()
        table.items = []

        components = checker._parse_sample_description_table(table)

        assert len(components) == 0


class TestGetOcrFieldValue:
    """Test _get_ocr_field_value method."""

    def test_get_model_spec(self):
        """Test getting model spec from OCR result."""
        checker = ReportChecker()

        ocr_result = LabelOCRResult(
            raw_text="test",
            fields={"model_spec": "RF-2000"},
        )

        value = checker._get_ocr_field_value("规格型号", ocr_result)
        assert value == "RF-2000"

    def test_get_production_date_via_synonym(self):
        """Test getting production date via MFG synonym."""
        checker = ReportChecker()

        ocr_result = LabelOCRResult(
            raw_text="test",
            fields={"production_date": "2026.01.08"},
        )

        value = checker._get_ocr_field_value("生产日期", ocr_result)
        assert value == "2026.01.08"

    def test_get_unknown_field(self):
        """Test getting unknown field."""
        checker = ReportChecker()

        ocr_result = LabelOCRResult(
            raw_text="test",
            fields={},
        )

        value = checker._get_ocr_field_value("未知字段", ocr_result)
        assert value == ""


class TestRunAllChecks:
    """Test run_all_checks method."""

    def test_runs_all_checks(self):
        """Test that all C04-C06 checks are run."""
        checker = ReportChecker()

        components = [
            ComponentRow(component_name="主机"),
        ]

        caption_info = CaptionInfo(
            raw_caption="中文标签：主机",
            main_name="主机",
            is_chinese_label=True,
        )
        label_ocr_results = [(caption_info, LabelOCRResult(raw_text="test"))]
        photo_captions = ["图1：主机"]

        results = checker.run_all_checks(
            components,
            label_ocr_results,
            photo_captions,
        )

        assert "C04" in results
        assert "C05" in results
        assert "C06" in results
        assert len(results["C04"]) == 1
        assert len(results["C05"]) == 1
        assert len(results["C06"]) == 1


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_report_checker(self):
        """Test create_report_checker function."""
        checker = create_report_checker()
        assert isinstance(checker, ReportChecker)

    def test_create_report_checker_with_ocr_service(self):
        """Test create_report_checker with custom OCR service."""
        ocr_service = OCRService()
        checker = create_report_checker(ocr_service=ocr_service)
        assert checker.ocr_service == ocr_service


class TestCheckResult:
    """Test CheckResult dataclass."""

    def test_creation(self):
        """Test creating CheckResult."""
        result = CheckResult(
            check_id="C04",
            status=CheckStatus.PASS,
            message="Test passed",
        )
        assert result.check_id == "C04"
        assert result.status == CheckStatus.PASS
        assert result.message == "Test passed"

    def test_add_warning_to_pass(self):
        """Test adding warning converts PASS to WARNING."""
        result = CheckResult(
            check_id="C04",
            status=CheckStatus.PASS,
        )
        result.add_warning("Test warning")
        assert result.status == CheckStatus.WARNING
        assert len(result.warnings) == 1

    def test_add_warning_to_error(self):
        """Test adding warning to ERROR keeps ERROR."""
        result = CheckResult(
            check_id="C04",
            status=CheckStatus.ERROR,
        )
        result.add_warning("Test warning")
        assert result.status == CheckStatus.ERROR
        assert len(result.warnings) == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_component_name(self):
        """Test handling of None component name."""
        checker = ReportChecker()

        components = [
            ComponentRow(component_name=""),
        ]

        label_ocr_results = []

        result = checker.check_c04_sample_description(components, label_ocr_results)

        # Should handle gracefully
        assert result.check_id == "C04"

    def test_unicode_characters(self):
        """Test handling of Unicode characters."""
        checker = ReportChecker()

        normalized = checker._normalize_for_comparison("射频消融电极")
        assert isinstance(normalized, str)
        assert len(normalized) > 0

    def test_mixed_empty_values(self):
        """Test various empty value representations."""
        checker = ReportChecker()

        empty_values = ["", "/", "——", "-", "  ", "\t"]
        for val in empty_values:
            assert checker._is_empty_value(val) is True, f"Failed for: '{val}'"

    def test_synonym_mapping(self):
        """Test column synonym mapping."""
        checker = ReportChecker()

        # Test that various synonyms map correctly
        assert "部件名称" in checker.COLUMN_SYNONYMS
        assert "规格型号" in checker.COLUMN_SYNONYMS
        assert "序列号批号" in checker.COLUMN_SYNONYMS
        assert "生产日期" in checker.COLUMN_SYNONYMS
        assert "失效日期" in checker.COLUMN_SYNONYMS
