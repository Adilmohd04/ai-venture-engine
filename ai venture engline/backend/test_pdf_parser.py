"""Unit tests for PDFParser."""

import os
import tempfile

import pdfplumber
import pytest

from pdf_parser import PDFParser


@pytest.fixture
def parser():
    return PDFParser()


def _create_text_pdf(path: str, pages: list[str]) -> None:
    """Create a simple PDF with text pages using pdfplumber's underlying library."""
    from pdfminer.high_level import extract_text  # noqa: F401
    from pypdfium2 import PdfDocument

    doc = PdfDocument.new()
    for text in pages:
        page = doc.new_page(width=612, height=792)
        # pypdfium2 doesn't easily add text, so we use fpdf2 or reportlab
        # Instead, let's use a minimal PDF writer approach
        pass
    doc.close()


def _make_pdf_with_text(text_content: str, path: str) -> None:
    """Create a minimal valid PDF with text content at the given path."""
    # Minimal PDF with text stream
    content = text_content.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"4 0 obj<</Length "
    )
    stream = f"BT /F1 12 Tf 100 700 Td ({content}) Tj ET".encode()
    pdf_bytes += str(len(stream)).encode() + b">>stream\n" + stream + b"\nendstream\nendobj\n"
    pdf_bytes += b"xref\n0 6\n"
    pdf_bytes += b"0000000000 65535 f \n" * 6
    pdf_bytes += b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    with open(path, "wb") as f:
        f.write(pdf_bytes)


class TestExtractText:
    def test_extracts_text_from_valid_pdf(self, parser, tmp_path):
        pdf_path = str(tmp_path / "sample.pdf")
        _make_pdf_with_text("Hello World", pdf_path)
        result = parser.extract_text(pdf_path)
        assert "Hello World" in result

    def test_returns_empty_string_for_image_only_pdf(self, parser, tmp_path):
        """An image-only PDF (no text streams) should return empty string."""
        pdf_path = str(tmp_path / "image_only.pdf")
        # Minimal valid PDF with a page but no text content
        pdf_bytes = b"%PDF-1.4\n"
        pdf_bytes += b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        pdf_bytes += b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        pdf_bytes += b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        pdf_bytes += b"xref\n0 4\n"
        pdf_bytes += b"0000000000 65535 f \n" * 4
        pdf_bytes += b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        result = parser.extract_text(pdf_path)
        assert result == ""

    def test_raises_for_nonexistent_file(self, parser):
        with pytest.raises(ValueError, match="File not found"):
            parser.extract_text("/nonexistent/path.pdf")

    def test_raises_for_non_pdf_extension(self, parser, tmp_path):
        txt_path = str(tmp_path / "file.txt")
        with open(txt_path, "w") as f:
            f.write("not a pdf")
        with pytest.raises(ValueError, match="Not a PDF file"):
            parser.extract_text(txt_path)

    def test_raises_for_corrupt_pdf(self, parser, tmp_path):
        pdf_path = str(tmp_path / "corrupt.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"this is not a valid pdf at all")
        with pytest.raises(ValueError, match="Failed to parse PDF"):
            parser.extract_text(pdf_path)


class TestExtractStructured:
    def test_returns_dict_with_page_numbers(self, parser, tmp_path):
        pdf_path = str(tmp_path / "sample.pdf")
        _make_pdf_with_text("Page content", pdf_path)
        result = parser.extract_structured(pdf_path)
        assert isinstance(result, dict)
        assert 1 in result
        assert "Page content" in result[1]

    def test_raises_for_nonexistent_file(self, parser):
        with pytest.raises(ValueError, match="File not found"):
            parser.extract_structured("/nonexistent/path.pdf")

    def test_raises_for_non_pdf_extension(self, parser, tmp_path):
        txt_path = str(tmp_path / "file.txt")
        with open(txt_path, "w") as f:
            f.write("not a pdf")
        with pytest.raises(ValueError, match="Not a PDF file"):
            parser.extract_structured(txt_path)

    def test_raises_for_corrupt_pdf(self, parser, tmp_path):
        pdf_path = str(tmp_path / "corrupt.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"this is not a valid pdf at all")
        with pytest.raises(ValueError, match="Failed to parse PDF"):
            parser.extract_structured(pdf_path)

    def test_image_only_pages_map_to_empty_string(self, parser, tmp_path):
        pdf_path = str(tmp_path / "image_only.pdf")
        pdf_bytes = b"%PDF-1.4\n"
        pdf_bytes += b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        pdf_bytes += b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        pdf_bytes += b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        pdf_bytes += b"xref\n0 4\n"
        pdf_bytes += b"0000000000 65535 f \n" * 4
        pdf_bytes += b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        result = parser.extract_structured(pdf_path)
        assert result[1] == ""
