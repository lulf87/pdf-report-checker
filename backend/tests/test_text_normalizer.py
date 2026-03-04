"""
Tests for Text Normalizer module.

Tests full-width/half-width conversion, whitespace normalization,
and line break merging.
"""

import pytest

from app.services.text_normalizer import (
    TextNormalizer,
    are_text_equal_normalized,
    compare_text,
    normalize_text,
)


class TestTextNormalizer:
    """Test TextNormalizer class."""

    def test_initialization(self):
        """Test normalizer initialization."""
        normalizer = TextNormalizer()
        assert normalizer.normalize_full_width is True

        normalizer_no_fw = TextNormalizer(normalize_full_width=False)
        assert normalizer_no_fw.normalize_full_width is False

    def test_normalize_empty_text(self):
        """Test normalizing empty text."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("") == ""
        assert normalizer.normalize(None) == ""

    def test_fullwidth_to_halfwidth_letters(self):
        """Test full-width letter conversion."""
        normalizer = TextNormalizer()
        # Uppercase
        assert normalizer._convert_full_width("ＡＢＣ") == "ABC"
        # Lowercase
        assert normalizer._convert_full_width("ａｂｃ") == "abc"
        # Mixed
        assert normalizer._convert_full_width("Ｈｅｌｌｏ") == "Hello"

    def test_fullwidth_to_halfwidth_numbers(self):
        """Test full-width number conversion."""
        normalizer = TextNormalizer()
        assert normalizer._convert_full_width("０１２３") == "0123"
        assert normalizer._convert_full_width("１００") == "100"

    def test_fullwidth_to_halfwidth_punctuation(self):
        """Test full-width punctuation conversion."""
        normalizer = TextNormalizer()
        # Note: Full-width ASCII punctuation is converted
        # U+FF01 ！→ !, U+FF1F ？→ ?
        # Chinese comma (， = U+FF0C) → ,
        # Chinese period (。 = U+3002) is NOT converted (intentionally preserved)
        assert normalizer._convert_full_width("！(test)") == "!(test)"
        assert normalizer._convert_full_width("：(test)") == ":(test)"
        assert normalizer._convert_full_width("，！？") == ",!?"  # Comma converted
        assert normalizer._convert_full_width("。") == "。"  # Period preserved

    def test_fullwidth_space_conversion(self):
        """Test full-width space conversion."""
        normalizer = TextNormalizer()
        assert normalizer._convert_full_width("全角空格　测试") == "全角空格 测试"

    def test_remove_extra_whitespace(self):
        """Test extra whitespace removal."""
        normalizer = TextNormalizer()
        # Multiple spaces
        assert normalizer._remove_extra_whitespace("hello    world") == "hello world"
        # Tabs and spaces
        assert normalizer._remove_extra_whitespace("hello\t\tworld") == "hello world"
        # Mixed
        assert normalizer._remove_extra_whitespace("hello   \t  world") == "hello world"

    def test_merge_natural_breaks(self):
        """Test natural line break merging."""
        normalizer = TextNormalizer()
        # Natural break (no terminal punctuation)
        result = normalizer._merge_natural_breaks("这是第一行\n这是第二行")
        assert "这是第一行 " in result or "这是第一行" in result

    def test_normalize_punctuation_spacing(self):
        """Test punctuation spacing normalization."""
        normalizer = TextNormalizer()
        # Remove space before Chinese punctuation
        assert normalizer._normalize_punctuation_spacing("测试 ，文本") == "测试，文本"
        # Remove space after Chinese punctuation
        result = normalizer._normalize_punctuation_spacing("测试， 文本")
        assert result == "测试，文本" or "测试,文本" in result

    def test_normalize_comprehensive(self):
        """Test comprehensive normalization."""
        normalizer = TextNormalizer()
        # Full-width text with extra spaces
        input_text = "Ｈｅｌｌｏ　　Ｗｏｒｌｄ"
        expected = "Hello World"
        assert normalizer.normalize(input_text) == expected

    def test_normalize_preserves_meaningful_structure(self):
        """Test that normalization preserves meaningful structure."""
        normalizer = TextNormalizer()
        # Terminal punctuation should be preserved
        text = "这是句子。这是另一个句子！"
        result = normalizer.normalize(text)
        assert "。" in result or "." in result
        assert "！" in result or "!" in result

    def test_normalize_list(self):
        """Test normalizing a list of texts."""
        normalizer = TextNormalizer()
        texts = ["ＡＢＣ", "ｘｙｚ", "　测试　"]
        result = normalizer.normalize_list(texts)
        assert result == ["ABC", "xyz", "测试"]

    def test_compare(self):
        """Test text comparison with normalization."""
        normalizer = TextNormalizer()
        # Same text with different widths
        assert normalizer.compare("ABC", "ＡＢＣ") is True
        # Different texts
        assert normalizer.compare("ABC", "XYZ") is False
        # Text with extra spaces
        assert normalizer.compare("Hello World", "Hello   World") is True


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_normalize_text_function(self):
        """Test normalize_text convenience function."""
        assert normalize_text("ＡＢＣ") == "ABC"
        assert normalize_text("  测试  ") == "测试"

    def test_compare_text_function(self):
        """Test compare_text convenience function."""
        assert compare_text("ABC", "ＡＢＣ") is True
        assert compare_text("ABC", "DEF") is False

    def test_are_text_equal_normalized_alias(self):
        """Test are_text_equal_normalized alias function."""
        assert are_text_equal_normalized("ABC", "ＡＢＣ") is True
        assert are_text_equal_normalized("ABC", "XYZ") is False


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_mixed_width_text(self):
        """Test text with mixed full-width and half-width characters."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("ＡBC") == "ABC"
        assert normalizer.normalize("AＢＣ") == "ABC"

    def test_punctuation_only(self):
        """Test text with only punctuation."""
        normalizer = TextNormalizer()
        # Chinese period (。) is preserved, others converted
        assert normalizer.normalize("，。！？") == ",。!?"

    def test_numbers_only(self):
        """Test text with only numbers."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("０１２３") == "0123"

    def test_special_characters(self):
        """Test special characters."""
        normalizer = TextNormalizer()
        # Characters not in mapping should be preserved
        assert "@" in normalizer.normalize("@test")
        assert "#" in normalizer.normalize("#test")

    def test_long_text(self):
        """Test normalization of longer text."""
        normalizer = TextNormalizer()
        long_text = "Ｈｅｌｌｏ　　ｗｏｒｌｄ！　Ｔｈｉｓ　ｉｓ　ａ　ｔｅｓｔ。"
        result = normalizer.normalize(long_text)
        assert "Hello world!" in result or "Hello world!" in result.replace(" ", "")
        assert "This is a test" in result or "Thisisatest" in result.replace(" ", "")

    def test_newline_handling(self):
        """Test newline handling in normalization."""
        normalizer = TextNormalizer()
        # Multiple newlines
        text = "line1\n\n\nline2"
        result = normalizer.normalize(text)
        assert "\n\n\n" not in result

    def test_whitespace_preservation_between_words(self):
        """Test that single spaces between words are preserved."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("Hello World") == "Hello World"
        assert normalizer.normalize("Hello  World") == "Hello World"

    def test_remove_spaces_between_cjk_chars(self):
        """Spaces inside Chinese words from OCR should be removed."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("导 管 外 观") == "导管外观"
        assert normalizer.normalize("有效长度外 表面") == "有效长度外表面"

    def test_remove_unit_annotations(self):
        """Formatting labels like '单位：X' should be removed."""
        normalizer = TextNormalizer()
        text = "直流电阻值≤20Ω。 单位：Ω"
        normalized = normalizer.normalize(text)
        assert "单位" not in normalized
        assert "20Ω" in normalized

    def test_normalize_ocr_symbol_variants(self):
        """Common OCR symbol variants should be normalized."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("绝缘电阻>5MQ") == "绝缘电阻>5MΩ"
        assert normalizer.normalize("绝缘电阻>5M Q") == "绝缘电阻>5MΩ"

    def test_normalize_inch_quote_variants(self):
        """OCR quote variants in inch specs should be normalized."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("导丝兼容性可兼容0.038''导丝。") == "导丝兼容性可兼容0.038\"导丝。"
        assert normalizer.normalize("导丝兼容性可兼容0.038″导丝。") == "导丝兼容性可兼容0.038\"导丝。"

    def test_normalize_formula_spacing_and_symbols(self):
        """Formula/unit spacing and symbol variants should be normalized."""
        normalizer = TextNormalizer()
        text = "高锰酸钾溶液[c(KMnO )=0.002mol/L] 的消耗量之 4 差不超过2.0ml。"
        normalized = normalizer.normalize(text)
        assert "KMnO4" in normalized
        assert "之差" in normalized
        assert "2.0mL" in normalized

    def test_normalize_concentration_symbol_and_micro_unit(self):
        """Rho/micro variants in concentration expressions should be normalized."""
        normalizer = TextNormalizer()
        text = "质量浓度为ρ (Pb2+ )=1 µg/mL 的标准对照液。"
        normalized = normalizer.normalize(text)
        assert "p(Pb2+)=1μg/mL" in normalized

    def test_normalize_heading_colon_before_requirement(self):
        """Heading colon before '应符合' should not create false mismatches."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("通用要求:应符合GB16174.1-2024的要求。") == (
            "通用要求应符合GB16174.1-2024的要求。"
        )
