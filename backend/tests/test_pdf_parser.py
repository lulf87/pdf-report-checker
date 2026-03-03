"""
Tests for PDF Parser module.

Tests electronic PDF extraction, table parsing, and scanned detection.
"""

from pathlib import Path

import pytest

from app.models.common_models import (
    BoundingBox,
    CellData,
    PDFDocument,
    PDFPage,
    TableData,
    TextBlock,
)
from app.services.pdf_parser import (
    PDFParser,
    is_scanned_pdf,
    parse_pdf,
    TEXT_DENSITY_THRESHOLD,
)


# Test fixtures
@pytest.fixture
def sample_pdf_path():
    """Path to sample PDF for testing."""
    # Use the actual sample files from 素材 directory
    base_path = Path(__file__).parent.parent.parent / "素材"
    # Try PTR sample first
    ptr_path = base_path / "ptr" / "1539" / "射频脉冲电场消融系统产品技术要求-20260102-Clean.pdf"
    if ptr_path.exists():
        return str(ptr_path)
    # Fallback to report sample
    report_path = base_path / "report" / "1539" / "QW2025-1539 Draft.pdf"
    if report_path.exists():
        return str(report_path)
    pytest.skip("No sample PDF files found in 素材 directory")


class TestPDFParser:
    """Test PDFParser class functionality."""

    def test_parser_initialization(self):
        """Test parser can be initialized with different parameters."""
        parser_default = PDFParser()
        assert parser_default.ocr_fallback is True
        assert parser_default.text_density_threshold == TEXT_DENSITY_THRESHOLD

        parser_no_ocr = PDFParser(ocr_fallback=False)
        assert parser_no_ocr.ocr_fallback is False

        parser_custom = PDFParser(text_density_threshold=100)
        assert parser_custom.text_density_threshold == 100

    def test_parse_pdf_structure(self, sample_pdf_path):
        """Test PDF parsing returns valid document structure."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        assert isinstance(doc, PDFDocument)
        assert doc.file_path == sample_pdf_path
        assert doc.total_pages > 0
        assert len(doc.pages) == doc.total_pages
        assert isinstance(doc.metadata, dict)

    def test_page_extraction(self, sample_pdf_path):
        """Test individual page extraction."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        # Check first page
        first_page = doc.get_page(1)
        assert first_page is not None
        assert first_page.page_number == 1
        assert first_page.width > 0
        assert first_page.height > 0
        assert isinstance(first_page.text_blocks, list)

    def test_text_block_properties(self, sample_pdf_path):
        """Test text block extraction and properties."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        # Find a page with text blocks
        for page in doc.pages:
            if page.text_blocks:
                block = page.text_blocks[0]
                assert isinstance(block.text, str)
                assert isinstance(block.bbox, BoundingBox)
                assert block.bbox.page == page.page_number
                assert block.font_size > 0
                assert isinstance(block.is_bold, bool)
                assert len(block) == len(block.text)
                break
        else:
            pytest.skip("No text blocks found in PDF")

    def test_scanned_detection(self, sample_pdf_path):
        """Test scanned page detection based on text density."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser(text_density_threshold=50)
        doc = parser.parse(sample_pdf_path)

        # Get scanned pages
        scanned_pages = doc.get_scanned_pages()
        assert isinstance(scanned_pages, list)

        # Each scanned page should have the flag set
        for page in scanned_pages:
            assert page.is_scanned is True
            assert page.text_density < parser.text_density_threshold

    def test_table_extraction(self, sample_pdf_path):
        """Test table extraction from PDF."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        # Check for tables
        all_tables = doc.get_all_tables()
        assert isinstance(all_tables, list)

        if all_tables:
            # Verify first table structure
            table = all_tables[0]
            assert isinstance(table, TableData)
            assert table.num_rows > 0
            assert table.num_cols > 0
            assert table.page > 0

            # Check headers
            assert isinstance(table.headers, list)

            # Check cell data
            if table.rows:
                first_row = table.rows[0]
                assert isinstance(first_row, list)
                if first_row:
                    cell = first_row[0]
                    assert isinstance(cell, CellData)
                    assert cell.row == 0
                    assert isinstance(cell.text, str)

    def test_bounding_box(self, sample_pdf_path):
        """Test bounding box calculations."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        # Find a page with text blocks
        for page in doc.pages:
            if page.text_blocks:
                block = page.text_blocks[0]
                bbox = block.bbox

                # Test properties
                assert bbox.width == bbox.x1 - bbox.x0
                assert bbox.height == bbox.y1 - bbox.y0
                assert bbox.area == bbox.width * bbox.height
                break
        else:
            pytest.skip("No text blocks found in PDF")


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_parse_pdf_function(self, sample_pdf_path):
        """Test parse_pdf convenience function."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        doc = parse_pdf(sample_pdf_path)
        assert isinstance(doc, PDFDocument)
        assert doc.total_pages > 0

    def test_parse_pdf_no_ocr(self, sample_pdf_path):
        """Test parse_pdf with OCR disabled."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        doc = parse_pdf(sample_pdf_path, use_ocr=False)
        assert isinstance(doc, PDFDocument)

    def test_is_scanned_pdf(self, sample_pdf_path):
        """Test is_scanned_pdf convenience function."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        result = is_scanned_pdf(sample_pdf_path)
        assert isinstance(result, bool)


class TestPageMethods:
    """Test PDFPage helper methods."""

    def test_page_has_text(self, sample_pdf_path):
        """Test PDFPage.has_text method."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        for page in doc.pages:
            result = page.has_text()
            assert isinstance(result, bool)
            if result:
                assert page.raw_text.strip()

    def test_page_has_tables(self, sample_pdf_path):
        """Test PDFPage.has_tables method."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        for page in doc.pages:
            result = page.has_tables()
            assert isinstance(result, bool)
            if result:
                assert len(page.tables) > 0


class TestTableMethods:
    """Test TableData helper methods."""

    def test_table_get_cell(self, sample_pdf_path):
        """Test TableData.get_cell method."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        for table in doc.get_all_tables():
            if table.num_rows > 0 and table.num_cols > 0:
                cell = table.get_cell(0, 0)
                assert cell is not None
                assert cell.row == 0
                assert cell.col == 0

                # Test out of bounds
                assert table.get_cell(-1, 0) is None
                assert table.get_cell(0, -1) is None
                assert table.get_cell(table.num_rows, 0) is None
                break
        else:
            pytest.skip("No tables found in PDF")

    def test_table_get_row_text(self, sample_pdf_path):
        """Test TableData.get_row_text method."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        for table in doc.get_all_tables():
            if table.num_rows > 0:
                row_text = table.get_row_text(0)
                assert isinstance(row_text, list)
                assert len(row_text) == table.num_cols
                for text in row_text:
                    assert isinstance(text, str)
                break
        else:
            pytest.skip("No tables found in PDF")

    def test_table_is_empty(self, sample_pdf_path):
        """Test TableData.is_empty method."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        for table in doc.get_all_tables():
            result = table.is_empty()
            assert isinstance(result, bool)
            if not result:
                assert table.num_rows > 0
            break


class TestDocumentMethods:
    """Test PDFDocument helper methods."""

    def test_get_page(self, sample_pdf_path):
        """Test PDFDocument.get_page method."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        # Test existing page
        page = doc.get_page(1)
        assert page is not None
        assert page.page_number == 1

        # Test non-existing page
        assert doc.get_page(0) is None
        assert doc.get_page(doc.total_pages + 1) is None

    def test_get_text_pages(self, sample_pdf_path):
        """Test PDFDocument.get_text_pages method."""
        if not sample_pdf_path:
            pytest.skip("No sample PDF available")

        parser = PDFParser()
        doc = parser.parse(sample_pdf_path)

        text_pages = doc.get_text_pages()
        assert isinstance(text_pages, list)
        for page in text_pages:
            assert page.has_text()


class TestCellData:
    """Test CellData model."""

    def test_cell_is_merged(self):
        """Test CellData.is_merged method."""
        # Normal cell
        cell1 = CellData(text="test", row=0, col=0)
        assert cell1.is_merged() is False

        # Merged cell
        cell2 = CellData(text="merged", row=0, col=0, row_span=2, col_span=1)
        assert cell2.is_merged() is True

        cell3 = CellData(text="merged", row=0, col=0, row_span=1, col_span=2)
        assert cell3.is_merged() is True


class TestTextBlock:
    """Test TextBlock model."""

    def test_text_block_is_empty(self):
        """Test TextBlock.is_empty method."""
        # Non-empty block
        block1 = TextBlock(
            text="sample text",
            bbox=BoundingBox(0, 0, 100, 20, 1),
        )
        assert block1.is_empty() is False

        # Empty block
        block2 = TextBlock(
            text="",
            bbox=BoundingBox(0, 0, 100, 20, 1),
        )
        assert block2.is_empty() is True

        # Whitespace only block
        block3 = TextBlock(
            text="   \n\t  ",
            bbox=BoundingBox(0, 0, 100, 20, 1),
        )
        assert block3.is_empty() is True
