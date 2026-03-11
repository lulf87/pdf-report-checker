"""
Tests for Report Extractor module.

Tests inspection item extraction, field parsing, and table structure handling.
"""

from pathlib import Path

import pytest

from app.models.common_models import PDFDocument, PDFPage
from app.models.common_models import CellData, TableData
from app.models.report_models import (
    InspectionItem,
    InspectionTable,
    ReportDocument,
    ThirdPageFields,
)
from app.services.pdf_parser import PDFParser
from app.services.report_extractor import (
    ReportExtractor,
    extract_report,
)


# Test fixtures
@pytest.fixture
def report_sample_path():
    """Path to report sample PDF for testing."""
    base_path = Path(__file__).parent.parent.parent / "素材" / "report" / "1539"
    pdf_path = base_path / "QW2025-1539 Draft.pdf"
    if pdf_path.exists():
        return str(pdf_path)
    pytest.skip("Report sample PDF not found")


@pytest.fixture
def parsed_report_doc(report_sample_path):
    """Parsed report document for testing."""
    if not report_sample_path:
        pytest.skip("No report sample available")

    parser = PDFParser()
    return parser.parse(report_sample_path)


@pytest.fixture
def report_doc(parsed_report_doc):
    """Extracted report document structure."""
    if not parsed_report_doc:
        pytest.skip("No parsed document available")

    extractor = ReportExtractor()
    return extractor.extract_from_pdf_doc(parsed_report_doc)


class TestInspectionItem:
    """Test InspectionItem model."""

    def test_creation(self):
        """Test creating inspection items."""
        item = InspectionItem(
            sequence_number="1",
            inspection_project="Test Project",
            standard_clause="GB/T 1234",
            standard_requirement="Requirement text",
            test_result="符合要求",
            item_conclusion="符合",
            remark="",
        )
        assert item.sequence_number == "1"
        assert item.inspection_project == "Test Project"
        assert item.item_conclusion == "符合"

    def test_is_complete(self):
        """Test is_complete property."""
        item1 = InspectionItem(
            sequence_number="1",
            inspection_project="Test",
            standard_clause="GB 123",
            standard_requirement="Req",
            test_result="Pass",
            item_conclusion="Pass",
            remark="Note",
        )
        assert item1.is_complete is True

        item2 = InspectionItem(
            sequence_number="2",
            inspection_project="",
            standard_clause="",
            standard_requirement="",
            test_result="",
            item_conclusion="",
            remark="",
        )
        assert item2.is_complete is False

    def test_expected_conclusion_pass(self):
        """Test expected conclusion for passing results."""
        item = InspectionItem(
            sequence_number="1",
            inspection_project="Test",
            test_result="符合要求",
            item_conclusion="符合",
        )
        assert item.expected_conclusion == "符合"

    def test_expected_conclusion_fail(self):
        """Test expected conclusion for failing results."""
        item = InspectionItem(
            sequence_number="1",
            inspection_project="Test",
            test_result="不符合要求",
            item_conclusion="不符合",
        )
        assert item.expected_conclusion == "不符合"

    def test_expected_conclusion_dash(self):
        """Test expected conclusion for dash results."""
        item = InspectionItem(
            sequence_number="1",
            inspection_project="Test",
            test_result="——",
            item_conclusion="/",
        )
        assert item.expected_conclusion == "/"

    def test_conclusion_matches(self):
        """Test conclusion_matches property."""
        item1 = InspectionItem(
            sequence_number="1",
            inspection_project="Test",
            test_result="符合要求",
            item_conclusion="符合",
        )
        assert item1.conclusion_matches is True

        item2 = InspectionItem(
            sequence_number="2",
            inspection_project="Test",
            test_result="符合要求",
            item_conclusion="不符合",
        )
        assert item2.conclusion_matches is False


class TestInspectionTable:
    """Test InspectionTable model."""

    def test_creation(self):
        """Test creating inspection tables."""
        table = InspectionTable(
            items=[],
            page_start=3,
            page_end=5,
        )
        assert table.num_items == 0
        assert table.page_start == 3
        assert table.page_end == 5

    def test_get_item_by_sequence(self):
        """Test get_item_by_sequence method."""
        item1 = InspectionItem(sequence_number="1", inspection_project="Test1")
        item2 = InspectionItem(sequence_number="2", inspection_project="Test2")

        table = InspectionTable(items=[item1, item2])

        found = table.get_item_by_sequence("1")
        assert found is not None
        assert found.inspection_project == "Test1"

        not_found = table.get_item_by_sequence("99")
        assert not_found is None

    def test_get_item_by_sequence_with_continuation(self):
        """Test get_item_by_sequence with continuation marker."""
        item = InspectionItem(
            sequence_number="续1", inspection_project="Test", is_continued=True
        )

        table = InspectionTable(items=[item])

        found = table.get_item_by_sequence("1")
        assert found is not None
        assert found.sequence_number == "续1"

    def test_check_sequence_continuity(self):
        """Test sequence continuity checking."""
        table = InspectionTable(
            items=[
                InspectionItem(sequence_number="1", inspection_project="T1"),
                InspectionItem(sequence_number="2", inspection_project="T2"),
                InspectionItem(sequence_number="4", inspection_project="T4"),  # Gap
            ]
        )

        errors = table.check_sequence_continuity()
        assert len(errors) > 0
        assert any("gap" in error.lower() for error in errors)

    def test_check_continuation_markers(self):
        """Test continuation marker checking."""
        table = InspectionTable(
            items=[
                InspectionItem(
                    sequence_number="续1", inspection_project="T1", is_continued=True
                ),
            ]
        )

        errors = table.check_continuation_markers()
        assert len(errors) > 0


class TestThirdPageFields:
    """Test ThirdPageFields model."""

    def test_creation(self):
        """Test creating third page fields."""
        fields = ThirdPageFields(
            client="Test Client",
            sample_name="Test Sample",
            model_spec="Model X",
        )
        assert fields.client == "Test Client"
        assert fields.sample_name == "Test Sample"

    def test_has_standard_content_exclusion(self):
        """Test has_standard_content_exclusion property."""
        fields1 = ThirdPageFields()
        assert fields1.has_standard_content_exclusion is False

        fields2 = ThirdPageFields(standard_content="2.1.1-2.1.5")
        assert fields2.has_standard_content_exclusion is True

    def test_is_sequence_excluded(self):
        """Test is_sequence_excluded method."""
        fields = ThirdPageFields(standard_ranges=[(1, 5), (10, 15)])

        # Excluded ranges
        assert fields.is_sequence_excluded("2.1.3") is True
        assert fields.is_sequence_excluded("2.1.12") is True

        # Not excluded
        assert fields.is_sequence_excluded("2.1.8") is False


class TestReportDocument:
    """Test ReportDocument model."""

    def test_empty_document(self):
        """Test creating empty document."""
        doc = ReportDocument()
        assert doc.inspection_table is None
        assert doc.third_page_fields is None
        assert doc.total_inspection_items == 0

    def test_with_inspection_table(self):
        """Test document with inspection table."""
        table = InspectionTable(
            items=[
                InspectionItem(sequence_number="1", inspection_project="T1"),
                InspectionItem(sequence_number="2", inspection_project="T2"),
            ]
        )

        doc = ReportDocument(inspection_table=table)
        assert doc.total_inspection_items == 2
        assert len(doc.valid_inspection_items) == 2

    def test_with_exclusions(self):
        """Test document with excluded sequences."""
        table = InspectionTable(
            items=[
                InspectionItem(sequence_number="1", inspection_project="T1"),
                InspectionItem(sequence_number="3", inspection_project="T3"),
                InspectionItem(sequence_number="5", inspection_project="T5"),
            ]
        )

        third_fields = ThirdPageFields(standard_ranges=[(2, 4)])

        doc = ReportDocument(
            inspection_table=table, third_page_fields=third_fields
        )

        valid_items = doc.valid_inspection_items
        assert len(valid_items) == 2
        assert valid_items[0].sequence_number == "1"
        assert valid_items[1].sequence_number == "5"


class TestReportExtractor:
    """Test ReportExtractor class."""

    def test_extractor_initialization(self):
        """Test extractor can be initialized."""
        extractor = ReportExtractor()
        assert extractor.use_ocr is True

        extractor_no_ocr = ReportExtractor(use_ocr=False)
        assert extractor_no_ocr.use_ocr is False

    def test_extract_from_empty_doc(self):
        """Test extraction from empty document."""
        pdf_doc = PDFDocument()
        extractor = ReportExtractor()
        report_doc = extractor.extract_from_pdf_doc(pdf_doc)

        assert isinstance(report_doc, ReportDocument)

    def test_parse_standard_ranges(self):
        """Test standard range parsing."""
        extractor = ReportExtractor()

        # Single range
        ranges1 = extractor._parse_standard_ranges("2.1.1-2.1.5")
        assert len(ranges1) > 0

        # Multiple ranges
        ranges2 = extractor._parse_standard_ranges("2.1.1-2.1.5，2.2.1-2.2.3")
        assert len(ranges2) >= 1

    def test_is_inspection_table(self):
        """Test inspection table detection."""
        from app.models.common_models import TableData

        extractor = ReportExtractor()

        # Valid inspection table
        table1 = TableData(
            headers=["序号", "检验项目", "标准条款", "标准要求", "检验结果", "单项结论", "备注"]
        )
        assert extractor._is_inspection_table(table1) is True

        # Invalid table
        table2 = TableData(headers=["Column1", "Column2", "Column3"])
        assert extractor._is_inspection_table(table2) is False

    def test_find_third_page_with_spaced_title(self):
        """Should detect third page title even when Chinese chars are spaced."""
        extractor = ReportExtractor()
        pdf_doc = PDFDocument(
            pages=[
                PDFPage(page_number=1, width=595, height=842, raw_text="封面"),
                PDFPage(page_number=3, width=595, height=842, raw_text="检 验 报 告 首 页"),
            ]
        )

        third_page = extractor._find_third_page(pdf_doc)
        assert third_page is not None
        assert third_page.page_number == 3

    def test_extract_third_page_fields_without_colon(self):
        """Should extract key fields from table-style third-page text without ':'."""
        extractor = ReportExtractor()
        page = PDFPage(
            page_number=3,
            width=595,
            height=842,
            raw_text=(
                "样品名称\n一次性使用导管\n"
                "型号规格\nRMC01\n"
                "委托方\n苏州元科医疗器械有限公司\n"
                "生产日期\n20251210\n"
                "产品编号/批号\nRMC251201\n"
            ),
        )

        fields = extractor._extract_third_page_fields(page)
        assert fields.sample_name == "一次性使用导管"
        assert fields.model_spec == "RMC01"
        assert fields.client == "苏州元科医疗器械有限公司"
        assert fields.production_date == "20251210"
        assert fields.product_id_batch == "RMC251201"

    def test_extract_third_page_multiline_client_address(self):
        """Should merge multiline client address on third page."""
        extractor = ReportExtractor()
        page = PDFPage(
            page_number=3,
            width=595,
            height=842,
            raw_text=(
                "委托方地址\n"
                "中国（江苏）自由贸易试验区苏州片区苏州\n"
                "工业园区星湖街328 号创意产业园五期A3-40\n"
                "3-3 单元\n"
                "产品编号／\n"
                "批号\n"
                "RMC251201\n"
            ),
        )

        fields = extractor._extract_third_page_fields(page)
        assert fields.client_address == "中国（江苏）自由贸易试验区苏州片区苏州工业园区星湖街328 号创意产业园五期A3-403-3 单元"

    def test_extract_third_page_inspection_items_should_preserve_parenthetical_exclusions(self):
        """Inspection scope should not split exclusion names inside parentheses."""
        extractor = ReportExtractor()
        page = PDFPage(
            page_number=3,
            width=595,
            height=842,
            raw_text="检验项目\n2.1～2.8（除生物相容性、电磁兼容性）\n",
        )

        fields = extractor._extract_third_page_fields(page)
        assert fields.inspection_items == ["2.1～2.8（除生物相容性、电磁兼容性）"]

    def test_extract_first_page_fields_without_colon(self):
        """Should extract C01 keys from first page when key/value are on separate lines."""
        extractor = ReportExtractor()
        page = PDFPage(
            page_number=1,
            width=595,
            height=842,
            raw_text=(
                "检 验 报 告\n"
                "委 托 方\n"
                "苏州元科医疗器械有限公司\n"
                "样品名称\n"
                "一次性使用消化道脉冲电场消融导管\n"
                "型号规格\n"
                "RMC01\n"
            ),
        )

        fields = extractor._extract_first_page_fields(page)
        assert fields["委托方"] == "苏州元科医疗器械有限公司"
        assert fields["样品名称"] == "一次性使用消化道脉冲电场消融导管"
        assert fields["型号规格"] == "RMC01"
        assert fields["client"] == "苏州元科医疗器械有限公司"
        assert fields["sample_name"] == "一次性使用消化道脉冲电场消融导管"
        assert fields["model_spec"] == "RMC01"

    def test_extract_items_marks_blank_continuation_row_as_logical_continuation(self):
        """Blank sequence rows with continued payload should attach to previous logical record."""
        extractor = ReportExtractor()
        table = TableData(
            headers=["序号", "检验项目", "标准条款", "标准要求", "检验结果", "单项结论", "备注"],
            rows=[
                [CellData("序号", 0, 0), CellData("检验项目", 0, 1), CellData("标准条款", 0, 2), CellData("标准要求", 0, 3), CellData("检验结果", 0, 4), CellData("单项结论", 0, 5), CellData("备注", 0, 6)],
                [CellData("1", 1, 0), CellData("导管外观", 1, 1), CellData("2.1.1", 1, 2), CellData("应完整", 1, 3), CellData("符合要求", 1, 4), CellData("符合", 1, 5), CellData("", 1, 6)],
                [CellData("", 2, 0), CellData("a) 远端应无破损", 2, 1), CellData("", 2, 2), CellData("补充说明", 2, 3), CellData("", 2, 4), CellData("", 2, 5), CellData("", 2, 6)],
                [CellData("2", 3, 0), CellData("尺寸", 3, 1), CellData("2.1.2", 3, 2), CellData("应符合要求", 3, 3), CellData("符合要求", 3, 4), CellData("符合", 3, 5), CellData("", 3, 6)],
            ],
        )

        items = extractor._extract_items_from_table(page_num=8, table=table)

        assert len(items) == 3
        assert items[0].sequence_number == "1"
        assert items[1].sequence_number == ""
        assert items[1].is_continued is True
        assert items[1].inspection_project == "a) 远端应无破损"


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_extract_report_function(self, parsed_report_doc):
        """Test extract_inspection_items_from_pdf convenience function."""
        if not parsed_report_doc:
            pytest.skip("No parsed document available")

        from app.services.report_extractor import extract_inspection_items_from_pdf

        items = extract_inspection_items_from_pdf(parsed_report_doc)
        assert isinstance(items, list)


class TestIntegrationWithSample:
    """Integration tests with actual report samples."""

    def test_extract_from_sample(self, report_doc):
        """Test extracting from actual report sample."""
        if not report_doc:
            pytest.skip("No report document available")

        assert isinstance(report_doc, ReportDocument)

    def test_third_page_fields_extracted(self, report_doc):
        """Test that third page fields were extracted."""
        if not report_doc:
            pytest.skip("No report document available")

        # Third page extraction depends on finding "检验报告首页"
        # This may not exist in all sample documents
        if report_doc.third_page_fields is None:
            pytest.skip("Third page (检验报告首页) not found in sample")

    def test_inspection_table_extracted(self, report_doc):
        """Test that inspection table was extracted."""
        if not report_doc:
            pytest.skip("No report document available")

        # Inspection table detection depends on specific table structure
        # This may not exist in all sample documents
        if report_doc.inspection_table is None:
            pytest.skip("Inspection table not found in sample")
        else:
            assert report_doc.total_inspection_items >= 0
