"""
Tests for PTR Extractor module.

Tests Chapter 2 clause extraction, hierarchy parsing, and table reference detection.
"""

from pathlib import Path

import pytest

from app.models.common_models import PDFDocument, PDFPage
from app.models.ptr_models import (
    PTRClause,
    PTRClauseNumber,
    PTRDocument,
    PTRSubItem,
    PTRTable,
    PTRTableReference,
)
from app.services.pdf_parser import PDFParser
from app.services.ptr_extractor import (
    PTRExtractor,
    extract_ptr,
)
from tests.table_fixture_builder import build_table


# Test fixtures
@pytest.fixture
def ptr_sample_path():
    """Path to PTR sample PDF for testing."""
    base_path = Path(__file__).parent.parent.parent / "素材" / "ptr" / "1539"
    pdf_path = base_path / "射频脉冲电场消融系统产品技术要求-20260102-Clean.pdf"
    if pdf_path.exists():
        return str(pdf_path)
    pytest.skip("PTR sample PDF not found")


@pytest.fixture
def parsed_ptr_doc(ptr_sample_path):
    """Parsed PTR document for testing."""
    if not ptr_sample_path:
        pytest.skip("No PTR sample available")

    parser = PDFParser()
    return parser.parse(ptr_sample_path)


@pytest.fixture
def ptr_doc(parsed_ptr_doc):
    """Extracted PTR document structure."""
    if not parsed_ptr_doc:
        pytest.skip("No parsed document available")

    extractor = PTRExtractor()
    return extractor.extract(parsed_ptr_doc)


class TestPTRClauseNumber:
    """Test PTRClauseNumber model."""

    def test_from_string_simple(self):
        """Test parsing simple clause numbers."""
        num = PTRClauseNumber.from_string("2")
        assert num is not None
        assert num.parts == (2,)
        assert str(num) == "2"

    def test_from_string_nested(self):
        """Test parsing nested clause numbers."""
        num = PTRClauseNumber.from_string("2.1")
        assert num is not None
        assert num.parts == (2, 1)
        assert str(num) == "2.1"

        num = PTRClauseNumber.from_string("2.1.1")
        assert num is not None
        assert num.parts == (2, 1, 1)
        assert str(num) == "2.1.1"

        num = PTRClauseNumber.from_string("2.1.1.1")
        assert num is not None
        assert num.parts == (2, 1, 1, 1)
        assert str(num) == "2.1.1.1"

    def test_from_string_invalid(self):
        """Test parsing invalid clause numbers."""
        assert PTRClauseNumber.from_string("") is None
        assert PTRClauseNumber.from_string("abc") is None
        assert PTRClauseNumber.from_string("2.abc") is None

    def test_level_property(self):
        """Test level property."""
        assert PTRClauseNumber.from_string("2").level == 1
        assert PTRClauseNumber.from_string("2.1").level == 2
        assert PTRClauseNumber.from_string("2.1.1").level == 3
        assert PTRClauseNumber.from_string("2.1.1.1").level == 4

    def test_is_chapter_2(self):
        """Test is_chapter_2 property."""
        assert PTRClauseNumber.from_string("2").is_chapter_2 is True
        assert PTRClauseNumber.from_string("2.1").is_chapter_2 is False
        assert PTRClauseNumber.from_string("2.1.1").is_chapter_2 is False

    def test_parent_property(self):
        """Test parent property."""
        num = PTRClauseNumber.from_string("2.1.1")
        parent = num.parent
        assert parent is not None
        assert parent.parts == (2, 1)

        num = PTRClauseNumber.from_string("2")
        assert num.parent is None

    def test_comparison(self):
        """Test clause number comparison."""
        num1 = PTRClauseNumber.from_string("2.1")
        num2 = PTRClauseNumber.from_string("2.1.1")
        num3 = PTRClauseNumber.from_string("2.1")

        assert num1 < num2
        assert num1 == num3
        assert num2 > num1


class TestPTRSubItem:
    """Test PTRSubItem model."""

    def test_creation(self):
        """Test creating sub-items."""
        item = PTRSubItem(marker="a)", text="Sub-item content")
        assert item.marker == "a)"
        assert item.text == "Sub-item content"
        assert str(item) == "a) Sub-item content"

    def test_dash_marker(self):
        """Test dash marker sub-items."""
        item = PTRSubItem(marker="——", text="Dash item")
        assert item.marker == "——"
        assert item.text == "Dash item"


class TestPTRTableReference:
    """Test PTRTableReference model."""

    def test_creation(self):
        """Test creating table references."""
        ref = PTRTableReference(
            table_number=1,
            context="见表1",
            position=10,
        )
        assert ref.table_number == 1
        assert ref.context == "见表1"
        assert str(ref) == "表1"


class TestPTRClause:
    """Test PTRClause model."""

    def test_creation(self):
        """Test creating clauses."""
        number = PTRClauseNumber.from_string("2.1")
        clause = PTRClause(
            number=number,
            full_text="2.1 Test Clause",
            text_content="Test Clause",
            level=2,
        )
        assert clause.number == number
        assert clause.full_text == "2.1 Test Clause"
        assert clause.text_content == "Test Clause"
        assert clause.level == 2

    def test_has_table_references(self):
        """Test has_table_references method."""
        number = PTRClauseNumber.from_string("2.1")
        clause1 = PTRClause(
            number=number,
            full_text="2.1 Test",
            text_content="Test",
            level=2,
            table_references=[],
        )
        assert clause1.has_table_references() is False

        clause2 = PTRClause(
            number=number,
            full_text="2.1 Test 见表1",
            text_content="Test 见表1",
            level=2,
            table_references=[PTRTableReference(table_number=1)],
        )
        assert clause2.has_table_references() is True

    def test_get_all_table_numbers(self):
        """Test get_all_table_numbers method."""
        number = PTRClauseNumber.from_string("2.1")
        clause = PTRClause(
            number=number,
            full_text="2.1 Test",
            text_content="Test",
            level=2,
            table_references=[
                PTRTableReference(table_number=1),
                PTRTableReference(table_number=3),
            ],
        )
        assert clause.get_all_table_numbers() == [1, 3]


class TestPTRTable:
    """Test PTRTable model."""

    def test_creation(self):
        """Test creating tables."""
        table = PTRTable(
            table_number=1,
            caption="Test Table",
            headers=["Col1", "Col2"],
            rows=[["a", "b"], ["c", "d"]],
        )
        assert table.table_number == 1
        assert table.caption == "Test Table"
        assert table.num_rows == 2
        assert table.num_cols == 2

    def test_get_cell(self):
        """Test get_cell method."""
        table = PTRTable(
            table_number=1,
            headers=["Col1", "Col2"],
            rows=[["a", "b"], ["c", "d"]],
        )
        assert table.get_cell(0, 0) == "a"
        assert table.get_cell(1, 1) == "d"
        assert table.get_cell(2, 0) is None
        assert table.get_cell(0, 2) is None

    def test_find_row_by_header(self):
        """Test find_row_by_header method."""
        table = PTRTable(
            table_number=1,
            headers=["Parameter", "Value"],
            rows=[["Freq", "100MHz"], ["Power", "10W"]],
        )
        row = table.find_row_by_header("Freq")
        assert row is not None
        assert row[0] == "Freq"

        row = table.find_row_by_header("NotFound")
        assert row is None


class TestPTRDocument:
    """Test PTRDocument model."""

    def test_empty_document(self):
        """Test creating empty document."""
        doc = PTRDocument()
        assert len(doc.clauses) == 0
        assert len(doc.tables) == 0

    def test_get_clause_by_number(self):
        """Test get_clause_by_number method."""
        doc = PTRDocument()
        num = PTRClauseNumber.from_string("2.1")
        clause = PTRClause(
            number=num,
            full_text="2.1 Test",
            text_content="Test",
            level=2,
        )
        doc.clauses.append(clause)

        found = doc.get_clause_by_number(num)
        assert found is not None
        assert found == clause

        not_found = PTRClauseNumber.from_string("2.2")
        assert doc.get_clause_by_number(not_found) is None

    def test_get_clause_by_string(self):
        """Test get_clause_by_string method."""
        doc = PTRDocument()
        num = PTRClauseNumber.from_string("2.1")
        clause = PTRClause(
            number=num,
            full_text="2.1 Test",
            text_content="Test",
            level=2,
        )
        doc.clauses.append(clause)

        assert doc.get_clause_by_string("2.1") == clause
        assert doc.get_clause_by_string("2.2") is None

    def test_get_clauses_at_level(self):
        """Test get_clauses_at_level method."""
        doc = PTRDocument()
        doc.clauses = [
            PTRClause(
                number=PTRClauseNumber.from_string("2.1"),
                full_text="2.1 L1",
                text_content="L1",
                level=2,
            ),
            PTRClause(
                number=PTRClauseNumber.from_string("2.1.1"),
                full_text="2.1.1 L2",
                text_content="L2",
                level=3,
            ),
            PTRClause(
                number=PTRClauseNumber.from_string("2.2"),
                full_text="2.2 L1b",
                text_content="L1b",
                level=2,
            ),
        ]

        level2 = doc.get_clauses_at_level(2)
        assert len(level2) == 2

        level3 = doc.get_clauses_at_level(3)
        assert len(level3) == 1

    def test_get_all_referenced_table_numbers(self):
        """Test get_all_referenced_table_numbers method."""
        doc = PTRDocument()
        num = PTRClauseNumber.from_string("2.1")
        clause = PTRClause(
            number=num,
            full_text="2.1 Test",
            text_content="Test",
            level=2,
            table_references=[
                PTRTableReference(table_number=1),
                PTRTableReference(table_number=3),
                PTRTableReference(table_number=1),  # Duplicate
            ],
        )
        doc.clauses.append(clause)

        assert doc.get_all_referenced_table_numbers() == [1, 3]


class TestPTRExtractor:
    """Test PTRExtractor class."""

    def test_extractor_initialization(self):
        """Test extractor can be initialized."""
        extractor = PTRExtractor()
        assert extractor.strict is False

        extractor_strict = PTRExtractor(strict=True)
        assert extractor_strict.strict is True

    def test_extract_from_empty_doc(self):
        """Test extraction from empty document."""
        pdf_doc = PDFDocument()
        extractor = PTRExtractor()
        ptr_doc = extractor.extract(pdf_doc)

        assert isinstance(ptr_doc, PTRDocument)
        assert len(ptr_doc.clauses) == 0
        assert len(ptr_doc.tables) == 0

    def test_extract_clauses_from_ocr_style_lines(self):
        """Should parse OCR-style clause lines without strict spaces."""
        extractor = PTRExtractor()

        page = type("MockPage", (), {
            "page_number": 1,
            "raw_text": "\n".join(
                [
                    "2．性能指标",
                    "2.1.物理性能",
                    "2.1.1.1.导管外观",
                    "2.3.4酸碱度",
                    "2/8",
                ]
            ),
        })()

        clauses = extractor._extract_clauses_from_page(page)
        numbers = [str(c.number) for c in clauses]

        assert "2" in numbers
        assert "2.1" in numbers
        assert "2.1.1.1" in numbers
        assert "2.3.4" in numbers
        # Page counter should not be interpreted as clause.
        assert numbers.count("2") == 1

    def test_deduplicate_repeated_clause_numbers(self):
        """Repeated OCR heading clauses should be deduplicated by number."""
        extractor = PTRExtractor()
        clauses = [
            PTRClause(
                number=PTRClauseNumber.from_string("2"),
                full_text="2 性能指标",
                text_content="性能指标",
                level=1,
            ),
            PTRClause(
                number=PTRClauseNumber.from_string("2.1"),
                full_text="2.1 外观",
                text_content="外观",
                level=2,
            ),
            PTRClause(
                number=PTRClauseNumber.from_string("2"),
                full_text="2",
                text_content="2",
                level=1,
            ),
        ]

        deduped = extractor._deduplicate_clauses(clauses)
        numbers = [str(c.number) for c in deduped]
        assert numbers == ["2", "2.1"]
        assert deduped[0].text_content == "性能指标"

    def test_find_chapter2_pages_should_detect_deep_clause_lines(self):
        """Should detect chapter-2 page even when clause marker is not in top lines."""
        extractor = PTRExtractor()
        pdf_doc = PDFDocument(
            pages=[
                PDFPage(
                    page_number=1,
                    width=595.0,
                    height=842.0,
                    raw_text="\n".join(["封面信息"] * 30),
                ),
                PDFPage(
                    page_number=2,
                    width=595.0,
                    height=842.0,
                    raw_text="\n".join(
                        ["表格内容"] * 25
                        + ["2.1.2 脉冲幅度(V)：脉冲幅度应符合表1中的数值。"]
                    ),
                ),
            ]
        )
        chapter2_pages = extractor._find_chapter2_pages(pdf_doc)
        assert 2 in chapter2_pages


class TestTableReferenceExtraction:
    """Test table reference extraction logic."""

    def test_extract_table_references_simple(self):
        """Test extracting simple table references."""
        extractor = PTRExtractor()
        num = PTRClauseNumber.from_string("2.1")
        clause = PTRClause(
            number=num,
            full_text="2.1 Test",
            text_content="Test",
            level=2,
        )

        extractor._extract_table_references(clause, "参数见表1")
        assert len(clause.table_references) == 1
        assert clause.table_references[0].table_number == 1

    def test_extract_table_references_multiple(self):
        """Test extracting multiple table references."""
        extractor = PTRExtractor()
        num = PTRClauseNumber.from_string("2.1")
        clause = PTRClause(
            number=num,
            full_text="2.1 Test",
            text_content="Test",
            level=2,
        )

        extractor._extract_table_references(clause, "见表1和表3")
        assert len(clause.table_references) >= 1

    def test_extract_table_references_with_spaces(self):
        """Should detect spaced variants like '见表 1' and '表 1-2'."""
        extractor = PTRExtractor()
        clause = PTRClause(
            number=PTRClauseNumber.from_string("2.1"),
            full_text="2.1 Test",
            text_content="Test",
            level=2,
        )

        extractor._extract_table_references(clause, "参数应符合见表 1 中的数值，详见表 1-2。")
        refs = [ref.table_number for ref in clause.table_references]
        assert 1 in refs


class TestTableContinuationMerge:
    """Test cross-page continuation merge for complex PTR tables."""

    def test_merge_continuation_tables_should_keep_header_context(self):
        extractor = PTRExtractor()

        base = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["参数", "型号", "常规数值", "标准设置", "允许误差"],
                ["房室间期(ms)", "Edora 8 SR", "不适用", "", ""],
            ],
            page=3,
            position=(0, 100),
        )
        continuation = PTRTable(
            table_number=None,
            headers=["", "Edora 8 DR", "", "", ""],
            rows=[
                ["", "Edora 8 DR", "20...(5)...350", "180-170-160", "±20"],
            ],
            page=4,
            position=(0, 80),
        )

        merged = extractor._merge_continuation_tables([base, continuation])
        assert len(merged) == 1
        assert merged[0].table_number == 1
        assert len(merged[0].rows) >= 3
        # Continuation row should inherit parameter column context.
        assert merged[0].rows[-1][0] == "房室间期(ms)"


class TestCanonicalPtrTableConversion:
    """Test canonical normalization path inside PTR table conversion."""

    def test_convert_to_ptr_table_should_include_structured_fields(self):
        extractor = PTRExtractor()
        table_data = build_table(
            rows=[
                ["参数", "心房", "", "心室", ""],
                ["", "常规数值", "标准设置", "常规数值", "标准设置"],
                ["脉冲宽度(ms)", "0.1...(0.1)...1.5", "0.4", "0.1...(0.1)...1.5", "0.4"],
            ],
            table_number=1,
            headers=["参数", "心房", "", "心室", ""],
        )

        ptr_table = extractor._convert_to_ptr_table(table_data)
        assert ptr_table is not None
        assert ptr_table.structure_confidence is not None
        assert ptr_table.header_rows
        assert ptr_table.column_paths
        assert ptr_table.headers == [
            "参数",
            "心房 / 常规数值",
            "心房 / 标准设置",
            "心室 / 常规数值",
            "心室 / 标准设置",
        ]
        assert ptr_table.rows

    def test_convert_to_ptr_table_should_fallback_when_structure_confidence_low(self):
        extractor = PTRExtractor()
        table_data = build_table(
            rows=[
                ["", "", "", ""],
                ["", "", "", ""],
                ["随机文本A", "随机文本B", "123", "456"],
            ],
            table_number=3,
            headers=["", "", "", ""],
        )
        ptr_table = extractor._convert_to_ptr_table(table_data)
        assert ptr_table is not None
        assert ptr_table.metadata.get("normalizer") == "legacy_fallback"
        assert ptr_table.structure_confidence == 0.0

class TestSubItemExtraction:
    """Test sub-item extraction logic."""

    def test_extract_alpha_sub_items(self):
        """Test extracting alpha sub-items."""
        extractor = PTRExtractor()
        num = PTRClauseNumber.from_string("2.1")
        clause = PTRClause(
            number=num,
            full_text="2.1 Test",
            text_content="Test",
            level=2,
        )

        extractor._extract_sub_items(clause, "a) 第一项")
        assert len(clause.sub_items) == 1
        assert clause.sub_items[0].marker == "a)"
        assert clause.sub_items[0].text == "第一项"

    def test_extract_dash_sub_items(self):
        """Test extracting dash sub-items."""
        extractor = PTRExtractor()
        num = PTRClauseNumber.from_string("2.1")
        clause = PTRClause(
            number=num,
            full_text="2.1 Test",
            text_content="Test",
            level=2,
        )

        extractor._extract_sub_items(clause, "—— 备注内容")
        assert len(clause.sub_items) >= 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_extract_ptr_function(self, parsed_ptr_doc):
        """Test extract_ptr convenience function."""
        if not parsed_ptr_doc:
            pytest.skip("No parsed document available")

        ptr_doc = extract_ptr(parsed_ptr_doc)
        assert isinstance(ptr_doc, PTRDocument)


class TestIntegrationWithSample:
    """Integration tests with actual PTR samples."""

    def test_extract_from_sample(self, ptr_doc):
        """Test extracting from actual PTR sample."""
        if not ptr_doc:
            pytest.skip("No PTR document available")

        assert isinstance(ptr_doc, PTRDocument)
        # Should find some clauses from Chapter 2
        assert ptr_doc.chapter2_start is not None
        assert ptr_doc.chapter2_end is not None

    def test_clauses_have_valid_numbers(self, ptr_doc):
        """Test that extracted clauses have valid numbers."""
        if not ptr_doc or not ptr_doc.clauses:
            pytest.skip("No clauses found")

        for clause in ptr_doc.clauses[:10]:  # Check first 10
            assert clause.number is not None
            assert clause.number.parts[0] == 2  # Must be Chapter 2

    def test_tables_extracted(self, ptr_doc):
        """Test that tables were extracted."""
        if not ptr_doc:
            pytest.skip("No PTR document available")

        assert isinstance(ptr_doc.tables, list)
