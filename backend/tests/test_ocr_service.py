"""
Tests for OCR Service module.

Tests Chinese label recognition, field extraction, and Caption parsing.
"""

import pytest

from app.services.ocr_service import (
    CaptionInfo,
    LabelOCRResult,
    OCRService,
    extract_label_fields,
    parse_caption_main_name,
)


class TestCaptionInfo:
    """Test CaptionInfo model."""

    def test_creation(self):
        """Test creating CaptionInfo."""
        info = CaptionInfo(
            raw_caption="图1: 中文标签：射频消融电极",
            main_name="射频消融电极",
            is_chinese_label=True,
        )
        assert info.raw_caption == "图1: 中文标签：射频消融电极"
        assert info.main_name == "射频消融电极"
        assert info.is_chinese_label is True


class TestOCRService:
    """Test OCRService class."""

    def test_initialization(self):
        """Test OCR service initialization."""
        service = OCRService()
        assert service.language == "ch"
        assert service.use_angle_cls is True

    def test_parse_caption_chinese_label(self):
        """Test parsing Chinese label captions."""
        service = OCRService()

        # Chinese label with caption number
        info = service.parse_caption("图1: 中文标签：射频消融电极")
        assert info.is_chinese_label is True
        assert info.caption_number == "1"
        # Main name should have label keyword removed
        assert "射频消融电极" in info.main_name

    def test_parse_caption_direction_removal(self):
        """Test direction indicator removal."""
        service = OCRService()

        # Direction indicators should be removed
        info1 = service.parse_caption("左侧显示：电极")
        assert "左侧显示" not in info1.main_name

        info2 = service.parse_caption("正面图：产品")
        assert "正面图" not in info2.main_name

    def test_parse_caption_category_removal(self):
        """Test category indicator removal."""
        service = OCRService()

        # Category indicators should be removed
        info = service.parse_caption("中文标签样张：产品")
        assert "中文标签样张" not in info.main_name

    def test_extract_main_name_simple(self):
        """Test extracting main name from simple caption."""
        service = OCRService()

        result = service.extract_main_name_from_caption("射频消融电极")
        assert "射频消融电极" in result or result == "射频消融电极"

    def test_extract_main_name_with_number_prefix(self):
        """Test extracting main name with number prefix."""
        service = OCRService()

        result = service.extract_main_name_from_caption("1. 射频消融电极")
        assert "1." not in result

    def test_extract_main_name_with_no_sign_prefix(self):
        """Test extracting main name with № prefix."""
        service = OCRService()

        result = service.extract_main_name_from_caption("№2 一次性使用消化道脉冲电场消融导管 中文标签")
        assert "№2" not in result
        assert "一次性使用消化道脉冲电场消融导管" in result

    def test_is_chinese_label_detection(self):
        """Test Chinese label detection."""
        service = OCRService()

        # Should detect Chinese labels
        assert service._is_chinese_label("中文标签") is True
        assert service._is_chinese_label("标签样张") is True
        assert service._is_chinese_label("铭牌") is True

        # Should not detect non-label text
        assert service._is_chinese_label("产品照片") is False


class TestFieldExtraction:
    """Test field extraction from OCR text."""

    def test_extract_model_spec(self):
        """Test extracting model/spec field."""
        service = OCRService()

        text = "型号：RF-2000"
        fields = service._extract_fields(text)
        assert "model_spec" in fields or "model_spec" in fields
        assert fields.get("model_spec") or fields.get("model_spec")

    def test_extract_production_date(self):
        """Test extracting production date."""
        service = OCRService()

        # Various formats
        texts = [
            "生产日期：2026-01-08",
            "MFG: 2026/01/08",
            "制造日期：2026.01.08",
        ]

        for text in texts:
            fields = service._extract_fields(text)
            assert "production_date" in fields

    def test_extract_batch_number(self):
        """Test extracting batch/lot number."""
        service = OCRService()

        texts = [
            "批号：LOT20250101",
            "LOT: 12345",
            "Batch Number: BATCH-001",
        ]

        for text in texts:
            fields = service._extract_fields(text)
            assert "batch_number" in fields

    def test_extract_serial_number(self):
        """Test extracting serial number."""
        service = OCRService()

        texts = [
            "序列号：SN12345",
            "SN: ABC-123",
            "Serial Number: XYZ-789",
        ]

        for text in texts:
            fields = service._extract_fields(text)
            assert "serial_number" in fields

    def test_extract_multiple_fields(self):
        """Test extracting multiple fields from single text."""
        service = OCRService()

        text = """
        型号：RF-2000
        生产日期：2026-01-08
        批号：LOT12345
        序列号：SN67890
        """

        fields = service._extract_fields(text)
        assert len(fields) >= 4
        assert "model_spec" in fields or "model_spec" in fields
        assert "production_date" in fields
        assert "batch_number" in fields
        assert "serial_number" in fields

    def test_extract_multiline_registrant_address(self):
        """Test extracting multiline registrant address."""
        service = OCRService()

        text = (
            "注册人名称：苏州元科医疗器械有限公司\n"
            "注册人住所：中国（江苏）自由贸易试验区苏州片区苏州工业\n"
            "园区星湖街328号创意产业园五期A3-403-3单元\n"
            "注册人联系方式：0512-66092209\n"
        )
        fields = service._extract_fields(text)
        assert fields.get("registrant_address") == (
            "中国（江苏）自由贸易试验区苏州片区苏州工业"
            "园区星湖街328号创意产业园五期A3-403-3单元"
        )


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_extract_label_fields_function(self):
        """Test extract_label_fields convenience function."""
        # This would require actual image files, so we test with mock
        # For now, test that function exists
        assert callable(extract_label_fields)

    def test_parse_caption_main_name_function(self):
        """Test parse_caption_main_name convenience function."""
        result = parse_caption_main_name("图1: 产品标签")
        assert isinstance(result, str)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_caption_empty_text(self):
        """Test parsing empty caption."""
        service = OCRService()
        info = service.parse_caption("")
        assert info.main_name == ""

    def test_parse_caption_only_number(self):
        """Test caption with only number."""
        service = OCRService()
        info = service.parse_caption("图1")
        assert info.caption_number == "1"

    def test_parse_caption_no_number(self):
        """Test caption without number."""
        service = OCRService()
        info = service.parse_caption("产品标签：电极")
        assert info.caption_number == ""

    def test_extract_caption_info_prefers_label_candidate(self):
        """When multiple caption lines exist, should prefer explicit Chinese-label line."""
        service = OCRService()
        page_text = (
            "照片和说明\n"
            "№1 一次性使用消化道脉冲电场消融导管\n"
            "№2 一次性使用消化道脉冲电场消融导管 中文标签\n"
        )
        info = service.extract_caption_info(page_text)
        assert info is not None
        assert info.is_chinese_label is True
        assert "中文标签" in info.raw_caption
