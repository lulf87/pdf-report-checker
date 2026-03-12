"""
Text Normalizer for standardizing text before comparison.

Handles full-width/half-width unification, whitespace removal,
and natural line break merging.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Full-width to half-width character mappings
FULL_WIDTH_TO_HALF = {
    # Space
    "\u3000": " ",
    # Letters
    "\uff21": "A", "\uff22": "B", "\uff23": "C", "\uff24": "D", "\uff25": "E",
    "\uff26": "F", "\uff27": "G", "\uff28": "H", "\uff29": "I", "\uff2a": "J",
    "\uff2b": "K", "\uff2c": "L", "\uff2d": "M", "\uff2e": "N", "\uff2f": "O",
    "\uff30": "P", "\uff31": "Q", "\uff32": "R", "\uff33": "S", "\uff34": "T",
    "\uff35": "U", "\uff36": "V", "\uff37": "W", "\uff38": "X", "\uff39": "Y",
    "\uff3a": "Z",
    "\uff41": "a", "\uff42": "b", "\uff43": "c", "\uff44": "d", "\uff45": "e",
    "\uff46": "f", "\uff47": "g", "\uff48": "h", "\uff49": "i", "\uff4a": "j",
    "\uff4b": "k", "\uff4c": "l", "\uff4d": "m", "\uff4e": "n", "\uff4f": "o",
    "\uff50": "p", "\uff51": "q", "\uff52": "r", "\uff53": "s", "\uff54": "t",
    "\uff55": "u", "\uff56": "v", "\uff57": "w", "\uff58": "x", "\uff59": "y",
    "\uff5a": "z",
    # Numbers
    "\uff10": "0", "\uff11": "1", "\uff12": "2", "\uff13": "3", "\uff14": "4",
    "\uff15": "5", "\uff16": "6", "\uff17": "7", "\uff18": "8", "\uff19": "9",
    # Punctuation
    "\uff01": "!", "\uff02": "\"", "\uff03": "#", "\uff04": "$", "\uff05": "%",
    "\uff06": "&", "\uff07": "'", "\uff08": "(", "\uff09": ")", "\uff0a": "*",
    "\uff0b": "+", "\uff0c": ",", "\uff0d": "-", "\uff0e": ".", "\uff0f": "/",
    "\uff1a": ":", "\uff1b": ";", "\uff1c": "<", "\uff1d": "=", "\uff1e": ">",
    "\uff1f": "?", "\uff20": "@", "\uff3b": "[", "\uff3c": "\\", "\uff3d": "]",
    "\uff3e": "^", "\uff3f": "_", "\uff40": "`", "\uff5b": "{", "\uff5c": "|",
    "\uff5d": "}", "\uff5e": "~",
}

# Superscript/subscript and OCR-variant symbol mappings
SCRIPT_SYMBOL_MAP = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "⁺": "+", "⁻": "-",
    "×": "x",
    "－": "-", "–": "-", "—": "-", "−": "-",
    "＜": "<", "＞": ">",
    "≤": "<=", "≦": "<=", "⩽": "<=", "≥": ">=", "≧": ">=", "⩾": ">=",
}

# Pattern for natural line breaks (lines ending without terminal punctuation)
NATURAL_BREAK_PATTERN = re.compile(
    r"([^\n。！？；：\.\!\?;:])\n(?=[^\n\d])",
    re.MULTILINE,
)

# Pattern for multiple whitespace characters
MULTI_SPACE_PATTERN = re.compile(r"\s+")
# Pattern for spaces between Chinese characters introduced by OCR/layout
CJK_INNER_SPACE_PATTERN = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
# Pattern for "单位：X" style format annotations
UNIT_ANNOTATION_PATTERN = re.compile(r"(?:^|\s)单位\s*[：:]\s*[A-Za-z0-9μuΩΩ/%²³\-\.\(\)]+")


class TextNormalizer:
    """Normalizes text for consistent comparison."""

    def __init__(self, normalize_full_width: bool = True):
        """Initialize text normalizer.

        Args:
            normalize_full_width: Whether to convert full-width to half-width
        """
        self.normalize_full_width = normalize_full_width

    def normalize(self, text: str) -> str:
        """Apply all normalizations to text.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Step 1: Full-width to half-width conversion
        if self.normalize_full_width:
            text = self._convert_full_width(text)

        # Step 2: Merge natural line breaks
        text = self._merge_natural_breaks(text)

        # Step 3: Normalize common OCR symbol variants
        text = self._normalize_ocr_symbol_variants(text)

        # Step 3.5: Collapse duplicated leading headings from OCR line merge
        text = self._normalize_repeated_heading_prefix(text)

        # Step 4: Remove formatting annotations like "单位：V"
        text = self._remove_format_annotations(text)

        # Step 5: Remove extra whitespace
        text = self._remove_extra_whitespace(text)

        # Step 6: Normalize OCR noise in scientific notation/symbols
        text = self._normalize_scientific_notation(text)

        # Step 7: Remove spurious spaces inside Chinese tokens
        text = self._normalize_cjk_spacing(text)

        # Step 8: Normalize whitespace around punctuation
        text = self._normalize_punctuation_spacing(text)

        return text.strip()

    def _convert_full_width(self, text: str) -> str:
        """Convert full-width characters to half-width.

        Args:
            text: Input text

        Returns:
            Text with full-width characters converted
        """
        result = []
        for char in text:
            result.append(FULL_WIDTH_TO_HALF.get(char, char))
        return "".join(result)

    def _merge_natural_breaks(self, text: str) -> str:
        """Merge natural line breaks (not ending in punctuation).

        Args:
            text: Input text

        Returns:
            Text with natural breaks merged
        """
        # Replace natural breaks with space
        text = NATURAL_BREAK_PATTERN.sub(r"\1 ", text)
        return text

    def _remove_extra_whitespace(self, text: str) -> str:
        """Remove extra whitespace characters.

        Args:
            text: Input text

        Returns:
            Text with extra whitespace removed
        """
        # Replace multiple whitespace with single space
        text = MULTI_SPACE_PATTERN.sub(" ", text)
        return text

    def _normalize_punctuation_spacing(self, text: str) -> str:
        """Normalize spacing around punctuation marks.

        Args:
            text: Input text

        Returns:
            Text with normalized punctuation spacing
        """
        # Remove spaces before Chinese punctuation
        text = re.sub(r"\s+([，。！？；：])", r"\1", text)

        # Remove spaces after Chinese punctuation (except quotes)
        text = re.sub(r"([，。！？；：])\s+(?![\"'»»])", r"\1", text)

        # Heading style noise: "通用要求:应符合..." == "通用要求应符合..."
        text = re.sub(r"(?<=[\u4e00-\u9fffA-Za-z0-9\)])[:：](?=应符合)", "", text)

        return text

    def _normalize_cjk_spacing(self, text: str) -> str:
        """Remove spaces between adjacent Chinese characters."""
        return CJK_INNER_SPACE_PATTERN.sub("", text)

    def _remove_format_annotations(self, text: str) -> str:
        """Remove non-semantic format labels such as '单位：V'."""
        return UNIT_ANNOTATION_PATTERN.sub(" ", text)

    def _normalize_ocr_symbol_variants(self, text: str) -> str:
        """Normalize common OCR symbol confusions."""
        normalized = text.replace("Ω", "Ω")
        # Normalize quote variants to ASCII quotes for stable comparison.
        normalized = (
            normalized.replace("“", "\"")
            .replace("”", "\"")
            .replace("‘", "'")
            .replace("’", "'")
        )
        for src, dst in SCRIPT_SYMBOL_MAP.items():
            normalized = normalized.replace(src, dst)

        # OCR may misread ± as Chinese "士" in numeric contexts.
        normalized = re.sub(r"(?<=\d)\s*士\s*(?=\d)", "±", normalized)

        # OCR may output 'MQ' while intended unit is MΩ.
        normalized = re.sub(r"(?<=\d)MQ\b", "MΩ", normalized)
        normalized = re.sub(r"(?<=\d)M Q\b", "MΩ", normalized)
        return normalized

    def _normalize_scientific_notation(self, text: str) -> str:
        """Normalize frequent OCR noise in formulas, symbols, and units."""
        normalized = text

        # Common symbol variants for concentration expressions and units.
        normalized = normalized.replace("µ", "μ")
        normalized = re.sub(r"(?i)\bohm\b|欧姆", "Ω", normalized)
        normalized = re.sub(r"ρ\s*(?=\()", "p", normalized)
        # OCR may confuse leading numeric "1" as l/I in range expressions.
        normalized = re.sub(r"(?<=[<>=≤≥])\s*[lI|](?=\s*(?:μ|u))", "1", normalized)

        # Normalize inch marks in specification values: 0.038'' -> 0.038"
        normalized = re.sub(
            r"(\d(?:\.\d+)?)\s*(?:''|\"\"|″|“|”|＂)+",
            r'\1"',
            normalized,
        )

        # Remove accidental spaces inside common chemical fragments.
        normalized = re.sub(r"KMnO\s+(\d)", r"KMnO\1", normalized)
        normalized = re.sub(r"Pb\s*(\d)\s*([+\-])", r"Pb\1\2", normalized)
        normalized = re.sub(r"([A-Za-z])\s+(\d)", r"\1\2", normalized)
        normalized = re.sub(r"(\d)\s+([+\-])", r"\1\2", normalized)

        # Normalize concentration and unit spacing.
        normalized = re.sub(r"([cp])\s*\(\s*", r"\1(", normalized)
        normalized = re.sub(r"\s*\)", ")", normalized)
        normalized = re.sub(r"\s*=\s*", "=", normalized)
        normalized = re.sub(r"μ+\s*μ*\s*g\s*/\s*m\s*L", "μg/mL", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bu\s*g\s*/\s*m\s*L\b", "μg/mL", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bu\s*L\b", "μL", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(\d)\s+μg/mL", r"\1μg/mL", normalized)
        # Normalize microsecond unit variants in numeric contexts:
        # 1us / 1 u s / 1 μ u s -> 1μs
        normalized = re.sub(
            r"(?<=\d)\s*(?:μ|u)\s*(?:u\s*)?s(?=[^A-Za-z]|$)",
            "μs",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(r"(?<=\d)\s*ml\b", "mL", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bml\b", "mL", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<=\d)\s*ms\b", "ms", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bms\b", "ms", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<=\d)\s*ns\b", "ns", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bns\b", "ns", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<=\d)\s*Hz\b", "Hz", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<=\d)\s*V\b", "V", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<=\d)\s*A\b", "A", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<=\d)\s*Ω\b", "Ω", normalized)
        normalized = re.sub(r"([<>]=?)\s+(?=\d)", r"\1", normalized)
        normalized = re.sub(r"(?<=<)\s*=\s*", "=", normalized)
        normalized = re.sub(r"(?<=>)\s*=\s*", "=", normalized)
        normalized = re.sub(r"(?<=\d)\s*M(?:Q)?2\b", "MΩ", normalized)
        normalized = re.sub(r"(?<=\d)\s*K(?:Q)?2\b", "KΩ", normalized)
        normalized = re.sub(r"(?<=\d)\s*Q2\b", "Ω", normalized)
        normalized = re.sub(r"(?<=\d)\s*2(?=Ω\b)", "", normalized)
        normalized = re.sub(
            r"(电阻值)\s*([-+]?\d+(?:\.\d+)?)2(?=[。；;，,\s]|$)",
            r"\1<=\2Ω",
            normalized,
        )
        normalized = re.sub(r"(?<=[A-Za-z0-9μΩ/\]\)\+\-])\s+(?=[\u4e00-\u9fff])", "", normalized)

        # Targeted OCR drift in this domain: subscript digit split into nearby phrase.
        normalized = re.sub(r"KMnO\s*\)", "KMnO4)", normalized)
        normalized = re.sub(r"之\s*4\s*差", "之差", normalized)

        return normalized

    def _normalize_repeated_heading_prefix(self, text: str) -> str:
        """Collapse duplicated leading heading tokens caused by OCR merge.

        Examples:
        - 脚踏开关脚踏开关应符合... -> 脚踏开关应符合...
        - 脉冲宽度脉冲宽度>=0.5us... -> 脉冲宽度>=0.5us...
        """
        if not text:
            return text

        lines = text.split("\n")
        pattern = re.compile(
            r"^([\u4e00-\u9fffA-Za-z0-9/（）()]{2,20}?)\s*\1(?=(?:应|[<>≤≥=]))"
        )
        normalized_lines: list[str] = []
        for line in lines:
            prev = line
            while True:
                current = pattern.sub(r"\1", prev)
                if current == prev:
                    break
                prev = current
            normalized_lines.append(prev)
        return "\n".join(normalized_lines)

    def normalize_list(self, texts: list[str]) -> list[str]:
        """Normalize a list of texts.

        Args:
            texts: List of input texts

        Returns:
            List of normalized texts
        """
        return [self.normalize(text) for text in texts]

    def compare(self, text1: str, text2: str) -> bool:
        """Compare two texts after normalization.

        Args:
            text1: First text
            text2: Second text

        Returns:
            True if texts match after normalization
        """
        return self.normalize(text1) == self.normalize(text2)


# Default normalizer instance
_default_normalizer = TextNormalizer()


def normalize_text(text: str) -> str:
    """Convenience function to normalize text.

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    return _default_normalizer.normalize(text)


def compare_text(text1: str, text2: str) -> bool:
    """Convenience function to compare normalized texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        True if texts match after normalization
    """
    return _default_normalizer.compare(text1, text2)


def are_text_equal_normalized(text1: str, text2: str) -> bool:
    """Alias for compare_text for backward compatibility.

    Args:
        text1: First text
        text2: Second text

    Returns:
        True if texts match after normalization
    """
    return compare_text(text1, text2)
