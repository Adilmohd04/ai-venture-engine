"""PDF text extraction using pdfplumber."""

import os

import pdfplumber


class PDFParser:
    """Extracts text content from uploaded pitch deck PDFs."""

    def extract_text(self, file_path: str) -> str:
        """Extract all text from a PDF file.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Concatenated text from all pages, or empty string if no
            extractable text is found (image-only PDF).

        Raises:
            ValueError: If the file does not exist, is not a .pdf,
                or is corrupt/unreadable.
        """
        self._validate_path(file_path)

        try:
            with pdfplumber.open(file_path) as pdf:
                pages_text: list[str] = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                return "\n".join(pages_text)
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError(f"Failed to parse PDF: {exc}") from exc

    def extract_structured(self, file_path: str) -> dict:
        """Extract text with page-level structure.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Dict mapping page numbers (1-indexed) to their text content.
            Pages with no extractable text map to an empty string.

        Raises:
            ValueError: If the file does not exist, is not a .pdf,
                or is corrupt/unreadable.
        """
        self._validate_path(file_path)

        try:
            with pdfplumber.open(file_path) as pdf:
                result: dict[int, str] = {}
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    result[i] = text if text else ""
                return result
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError(f"Failed to parse PDF: {exc}") from exc

    @staticmethod
    def _validate_path(file_path: str) -> None:
        """Check that the file exists and has a .pdf extension.

        Raises:
            ValueError: If validation fails.
        """
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found: {file_path}")
        if not file_path.lower().endswith(".pdf"):
            raise ValueError(f"Not a PDF file: {file_path}")
