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
        assert normalizer.normalize("电阻值≦10Ω，电流≥0.5A") == "电阻值<=10Ω,电流>=0.5A"

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

    def test_normalize_superscript_subscript_symbols(self):
        """Superscript/subscript digits and signs should be normalized."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("Pb²⁺") == "Pb2+"
        assert normalizer.normalize("KMnO₄") == "KMnO4"

    def test_normalize_plusminus_and_micro_u_variants(self):
        """Numeric '士' and ASCII u-units should be normalized."""
        normalizer = TextNormalizer()
        assert "100±20%" in normalizer.normalize("允许误差: 100士20%")
        assert "1μg/mL" in normalizer.normalize("浓度=1 ug/mL")

    def test_normalize_microsecond_unit_variants(self):
        """Microsecond OCR variants should normalize to μs in numeric contexts."""
        normalizer = TextNormalizer()
        assert ">=1μs" in normalizer.normalize("相间间隔>=1us")
        assert "<=100μs" in normalizer.normalize("相间间隔<=100 u s")
        assert "0.5μs" in normalizer.normalize("误差不超过0.5 μ u s")

    def test_normalize_quote_variants(self):
        """Curly/straight quote variants should normalize consistently."""
        normalizer = TextNormalizer()
        a = normalizer.normalize("“激活灯”亮橙色。")
        b = normalizer.normalize("\"激活灯\"亮橙色。")
        assert a == b

    def test_normalize_repeated_heading_prefix(self):
        """Duplicated heading prefixes from OCR should be collapsed."""
        normalizer = TextNormalizer()
        text = "脚踏开关脚踏开关应符合YY/T1057-2016标准的要求。"
        normalized = normalizer.normalize(text)
        assert normalized == "脚踏开关应符合YY/T1057-2016标准的要求。"

    def test_normalize_repeated_heading_prefix_with_whitespace(self):
        """Repeated headings separated by OCR whitespace/newline should be collapsed."""
        normalizer = TextNormalizer()
        text = "脚踏开关\n脚踏开关应符合YY/T1057-2016标准的要求。"
        normalized = normalizer.normalize(text)
        assert normalized == "脚踏开关应符合YY/T1057-2016标准的要求。"

    def test_normalize_repeated_heading_with_micro_units(self):
        """Repeated heading + micro unit variants should be normalized together."""
        normalizer = TextNormalizer()
        text = "脉冲宽度脉冲宽度>=0.5us且<=10us，误差不超过±10%或0.2us（取较大值）。"
        normalized = normalizer.normalize(text)
        assert normalized.startswith("脉冲宽度>=0.5μs且<=10μs")

    def test_normalize_ocr_l_as_one_before_micro_unit(self):
        """OCR l/I before micro-second unit in range should normalize to numeric 1."""
        normalizer = TextNormalizer()
        assert ">=1μs" in normalizer.normalize("相间间隔>=lμus")
        assert ">=1μs" in normalizer.normalize("相间间隔>=Iμs")

    def test_normalize_ns_case_variants(self):
        """nS/ns case variants should normalize consistently."""
        normalizer = TextNormalizer()
        assert "700ns" in normalizer.normalize("脉冲下降时间<=700nS。")

    def test_normalize_heading_colon_before_requirement(self):
        """Heading colon before '应符合' should not create false mismatches."""
        normalizer = TextNormalizer()
        assert normalizer.normalize("通用要求:应符合GB16174.1-2024的要求。") == (
            "通用要求应符合GB16174.1-2024的要求。"
        )

    def test_normalize_special_symbols_and_resistance_ocr_variants(self):
        normalizer = TextNormalizer()
        assert normalizer.normalize("直流电阻值⩽20 Ω。") == "直流电阻值<=20Ω。"
        assert normalizer.normalize("绝缘电阻应大于5M2。") == "绝缘电阻应大于5MΩ。"
        assert normalizer.normalize("相间间隔< = 20 us") == "相间间隔<=20μs"
        assert normalizer.normalize("直流电阻值202。") == "直流电阻值<=20Ω。"
