"""
Tests for OCR Service module.

Tests Chinese label recognition, field extraction, and Caption parsing.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.common_models import BoundingBox, TextBlock
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

    def test_extract_ref_and_lot_fallback_fields(self):
        """REF/LOT style labels should still yield model and batch fields."""
        service = OCRService()

        text = (
            "REF|NoVAEPP1206\n"
            "LOT2BL009\n"
            "生产日期：2025-12-03\n"
        )

        fields = service._extract_fields(text)
        assert fields.get("model_spec") == "NoVAEPP1206"
        assert fields.get("batch_number") == "2BL009"

    def test_extract_date_candidates_should_pick_earliest_as_production_date(self):
        """When only standalone dates exist, earliest date should be used as production date."""
        service = OCRService()

        text = "2027-12-02\n2025-12-03\n"
        fields = service._extract_fields(text)

        assert fields.get("production_date") == "2025-12-03"
        assert fields.get("expiration_date") == "2027-12-02"

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


class TestLLMEnhancement:
    """Test controlled VLM enhancement path for page-level label extraction."""

    @staticmethod
    def _patch_fake_fitz_open(monkeypatch):
        class _FakePixmap:
            def save(self, path: str):
                Path(path).write_bytes(b"fake-image")

        class _FakePage:
            def get_pixmap(self, matrix=None, clip=None, alpha=False):
                return _FakePixmap()

        class _FakeDoc:
            page_count = 1

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def __getitem__(self, index):
                return _FakePage()

        monkeypatch.setattr("app.services.ocr_service.fitz.open", lambda _: _FakeDoc())

    @pytest.mark.asyncio
    async def test_extract_label_from_page_should_focus_on_label_region_before_field_extraction(self, monkeypatch):
        service = OCRService()
        self._patch_fake_fitz_open(monkeypatch)

        monkeypatch.setattr(
            service,
            "process_image",
            lambda image_path, extract_fields=True: LabelOCRResult(
                raw_text="产品名称：一次性使用磁电定位心脏脉冲电场消融导管\n型号规格：NavAEPP1206\n批号：2BL009\n生产日期：2025-12-03",
                fields={
                    "product_name": "一次性使用磁电定位心脏脉冲电场消融导管",
                    "model_spec": "NavAEPP1206",
                    "batch_number": "2BL009",
                    "production_date": "2025-12-03",
                },
                confidence=0.92,
                success=True,
            ),
        )

        page = SimpleNamespace(
            raw_text=(
                "照片页说明\n"
                "图1 中文标签\n"
                "产品名称：一次性使用磁电定位心脏脉冲电场消融导管\n"
                "型号规格：NavAEPP1206\n"
                "批号：2BL009\n"
                "生产日期：2025-12-03\n"
                "其他干扰文字：检验方法见附录B\n"
            ),
            text_blocks=[
                TextBlock(
                    text="图1 中文标签",
                    bbox=BoundingBox(30, 40, 180, 70, 1),
                ),
                TextBlock(
                    text="产品名称：一次性使用磁电定位心脏脉冲电场消融导管",
                    bbox=BoundingBox(40, 120, 320, 145, 1),
                ),
                TextBlock(
                    text="型号规格：NavAEPP1206",
                    bbox=BoundingBox(40, 150, 240, 175, 1),
                ),
                TextBlock(
                    text="批号：2BL009",
                    bbox=BoundingBox(40, 180, 180, 205, 1),
                ),
                TextBlock(
                    text="生产日期：2025-12-03",
                    bbox=BoundingBox(40, 210, 220, 235, 1),
                ),
                TextBlock(
                    text="检验方法见附录B",
                    bbox=BoundingBox(60, 520, 220, 545, 1),
                ),
            ],
            page_number=1,
        )

        result = await service.extract_label_from_page(page=page, pdf_path="/tmp/fake-report.pdf", enable_llm=False)

        assert result is not None
        assert result.fields["product_name"] == "一次性使用磁电定位心脏脉冲电场消融导管"
        assert result.fields["model_spec"] == "NavAEPP1206"
        assert result.fields["batch_number"] == "2BL009"
        assert result.fields["production_date"] == "2025-12-03"
        assert result.metadata.get("label_region_detected") is True

    @pytest.mark.asyncio
    async def test_extract_label_from_page_applies_vlm_fix_when_needed(self, monkeypatch):
        service = OCRService()
        self._patch_fake_fitz_open(monkeypatch)
        monkeypatch.setattr("app.services.ocr_service.settings.llm_mode", "fallback")

        monkeypatch.setattr(
            service,
            "process_image",
            lambda image_path, extract_fields=True: LabelOCRResult(
                raw_text="规格型号：RMD01\n生产日期：2025?230",
                fields={"model_spec": "RMD01", "production_date": "2025?230"},
                confidence=0.61,
                success=True,
            ),
        )
        monkeypatch.setattr(
            service,
            "_extract_fields_with_vlm",
            AsyncMock(
                return_value={
                    "raw_text": "规格型号：RMD01\n生产日期：20251230",
                    "fields": {"model_spec": "RMD01", "production_date": "20251230"},
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                }
            ),
        )

        page = SimpleNamespace(raw_text="生产日期：2025?230", text_blocks=None, page_number=1)
        result = await service.extract_label_from_page(
            page=page,
            pdf_path="/tmp/fake-report.pdf",
            enable_llm=True,
        )

        assert result is not None
        assert result.fields.get("production_date") == "20251230"
        assert any("LLM增强已应用" in warning for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_extract_label_from_page_skips_vlm_when_quality_high(self, monkeypatch):
        service = OCRService()
        self._patch_fake_fitz_open(monkeypatch)
        monkeypatch.setattr("app.services.ocr_service.settings.llm_mode", "fallback")

        monkeypatch.setattr(
            service,
            "process_image",
            lambda image_path, extract_fields=True: LabelOCRResult(
                raw_text=(
                    "规格型号：RMD01\n生产日期：20251230\n"
                    "序列号：RMD251206002\n注册人：苏州元科医疗器械有限公司"
                ),
                fields={
                    "model_spec": "RMD01",
                    "production_date": "20251230",
                    "serial_number": "RMD251206002",
                    "registrant": "苏州元科医疗器械有限公司",
                },
                confidence=0.96,
                success=True,
            ),
        )
        llm_mock = AsyncMock(return_value={"fields": {"production_date": "20251230"}})
        monkeypatch.setattr(service, "_extract_fields_with_vlm", llm_mock)

        page = SimpleNamespace(raw_text="规格型号：RMD01", text_blocks=None, page_number=1)
        result = await service.extract_label_from_page(
            page=page,
            pdf_path="/tmp/fake-report.pdf",
            enable_llm=True,
        )

        assert result is not None
        assert result.fields.get("production_date") == "20251230"
        assert any("LLM增强跳过" in warning for warning in result.warnings)
        llm_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_extract_label_from_page_respects_disabled_mode(self, monkeypatch):
        service = OCRService()
        self._patch_fake_fitz_open(monkeypatch)
        monkeypatch.setattr("app.services.ocr_service.settings.llm_mode", "disabled")

        monkeypatch.setattr(
            service,
            "process_image",
            lambda image_path, extract_fields=True: LabelOCRResult(
                raw_text="规格型号：RMD01\n生产日期：20251230",
                fields={"model_spec": "RMD01", "production_date": "20251230"},
                confidence=0.55,
                success=True,
            ),
        )
        llm_mock = AsyncMock(return_value={"fields": {"production_date": "20251230"}})
        monkeypatch.setattr(service, "_extract_fields_with_vlm", llm_mock)

        page = SimpleNamespace(raw_text="规格型号：RMD01", text_blocks=None, page_number=1)
        result = await service.extract_label_from_page(
            page=page,
            pdf_path="/tmp/fake-report.pdf",
            enable_llm=True,
        )

        assert result is not None
        assert any("llm_mode=disabled" in warning for warning in result.warnings)
        llm_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_staged_vlm_routing_escalates_on_low_confidence(self, monkeypatch):
        service = OCRService()
        monkeypatch.setattr(service, "_get_primary_vlm_model", lambda: "qwen/qwen3-vl-8b-instruct")
        monkeypatch.setattr(service, "_get_secondary_vlm_model", lambda primary: "qwen/qwen3-vl-30b-a3b-instruct")

        async def fake_extract(image_path: str, base_text: str, model_name: str):
            if "8b" in model_name:
                return {
                    "fields": {"model_spec": "RMD01"},
                    "confidence": 0.45,
                    "uncertain_fields": ["production_date"],
                    "model": model_name,
                    "provider": "openrouter",
                }
            return {
                "fields": {
                    "model_spec": "RMD01",
                    "production_date": "20251230",
                    "serial_number": "RMD251206002",
                    "registrant": "苏州元科医疗器械有限公司",
                },
                "confidence": 0.93,
                "uncertain_fields": [],
                "model": model_name,
                "provider": "openrouter",
            }

        monkeypatch.setattr(service, "_extract_fields_with_vlm_model", fake_extract)
        result = await service._extract_fields_with_vlm("/tmp/fake.png", "base text")
        assert result.get("model") == "qwen/qwen3-vl-30b-a3b-instruct"
        assert "escalated" in str(result.get("routing", ""))

    @pytest.mark.asyncio
    async def test_staged_vlm_routing_keeps_primary_when_stronger(self, monkeypatch):
        service = OCRService()
        monkeypatch.setattr(service, "_get_primary_vlm_model", lambda: "qwen/qwen3-vl-8b-instruct")
        monkeypatch.setattr(service, "_get_secondary_vlm_model", lambda primary: "qwen/qwen3-vl-30b-a3b-instruct")

        async def fake_extract(image_path: str, base_text: str, model_name: str):
            if "8b" in model_name:
                return {
                    "fields": {
                        "model_spec": "RMD01",
                        "production_date": "20251230",
                        "serial_number": "RMD251206002",
                        "registrant": "苏州元科医疗器械有限公司",
                    },
                    "confidence": 0.96,
                    "uncertain_fields": [],
                    "model": model_name,
                    "provider": "openrouter",
                }
            return {
                "fields": {"model_spec": "RMD01"},
                "confidence": 0.21,
                "uncertain_fields": ["production_date", "serial_number"],
                "model": model_name,
                "provider": "openrouter",
            }

        monkeypatch.setattr(service, "_extract_fields_with_vlm_model", fake_extract)
        result = await service._extract_fields_with_vlm("/tmp/fake.png", "base text")
        assert result.get("model") == "qwen/qwen3-vl-8b-instruct"
        assert "primary-only" in str(result.get("routing", ""))
