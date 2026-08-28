"""
Document parsing utilities for extracting clean text from supported file formats.

Supports: PDF, DOCX, PPTX, Markdown, TXT, HTML
"""

from abc import ABC, abstractmethod
from typing import Dict, Type

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pptx import Presentation
from pypdf import PdfReader


class FileParsingError(Exception):
    """Raised when a file cannot be parsed or is corrupted."""

    pass


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_bytes: bytes) -> str:
        """
        Extract clean plain text from file bytes.

        Args:
            file_bytes: Raw file content as bytes.

        Returns:
            Extracted plain text as string.

        Raises:
            FileParsingError: If file is corrupted or unparseable.
        """
        pass


class PDFParser(BaseParser):
    """Parser for PDF documents using pypdf."""

    def parse(self, file_bytes: bytes) -> str:
        """Extract text from PDF file."""
        try:
            from io import BytesIO

            pdf_file = BytesIO(file_bytes)
            reader = PdfReader(pdf_file)

            text_parts: list[str] = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return "\n".join(text_parts).strip()
        except Exception as e:
            raise FileParsingError(f"Failed to parse PDF: {str(e)}") from e


class DOCXParser(BaseParser):
    """Parser for Word documents using python-docx."""

    def parse(self, file_bytes: bytes) -> str:
        """Extract text from DOCX file."""
        try:
            from io import BytesIO

            docx_file = BytesIO(file_bytes)
            document = DocxDocument(docx_file)

            text_parts: list[str] = []
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            for table in document.tables:
                for row in table.rows:
                    row_text: list[str] = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text)
                    if row_text:
                        text_parts.append(" | ".join(row_text))

            return "\n".join(text_parts).strip()
        except Exception as e:
            raise FileParsingError(f"Failed to parse DOCX: {str(e)}") from e


class PPTXParser(BaseParser):
    """Parser for PowerPoint presentations using python-pptx."""

    def parse(self, file_bytes: bytes) -> str:
        """Extract text from PPTX file."""
        try:
            from io import BytesIO

            pptx_file = BytesIO(file_bytes)
            presentation = Presentation(pptx_file)

            text_parts: list[str] = []
            for slide_idx, slide in enumerate(presentation.slides):
                slide_text: list[str] = [f"[Slide {slide_idx + 1}]"]
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text.append(shape.text)
                if len(slide_text) > 1:
                    text_parts.append("\n".join(slide_text))

            return "\n".join(text_parts).strip()
        except Exception as e:
            raise FileParsingError(f"Failed to parse PPTX: {str(e)}") from e


class MarkdownParser(BaseParser):
    """Parser for Markdown files."""

    def parse(self, file_bytes: bytes) -> str:
        """Extract clean text from Markdown file."""
        try:
            text = file_bytes.decode("utf-8", errors="replace").strip()
            return text
        except Exception as e:
            raise FileParsingError(f"Failed to parse Markdown: {str(e)}") from e


class TXTParser(BaseParser):
    """Parser for plain text files."""

    def parse(self, file_bytes: bytes) -> str:
        """Decode and extract text from TXT file."""
        try:
            text = file_bytes.decode("utf-8", errors="replace").strip()
            return text
        except Exception as e:
            raise FileParsingError(f"Failed to parse TXT: {str(e)}") from e


class HTMLParser(BaseParser):
    """Parser for HTML files using BeautifulSoup4."""

    def parse(self, file_bytes: bytes) -> str:
        """Extract readable body text from HTML file."""
        try:
            html_text = file_bytes.decode("utf-8", errors="replace")
            soup = BeautifulSoup(html_text, "html.parser")

            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines)
        except Exception as e:
            raise FileParsingError(f"Failed to parse HTML: {str(e)}") from e


class DocumentParserFactory:
    """Factory for routing file types to appropriate parser implementations."""

    _parsers: Dict[str, Type[BaseParser]] = {
        "pdf": PDFParser,
        "docx": DOCXParser,
        "pptx": PPTXParser,
        "markdown": MarkdownParser,
        "txt": TXTParser,
        "html": HTMLParser,
    }

    @classmethod
    def get_parser(cls, file_type: str) -> BaseParser:
        """
        Get the appropriate parser for a given file type.

        Args:
            file_type: File type string (e.g., 'pdf', 'docx', 'pptx', 'markdown', 'txt', 'html').

        Returns:
            Instantiated parser of the appropriate type.

        Raises:
            FileParsingError: If file_type is not supported.
        """
        file_type_lower = file_type.lower().strip()
        if file_type_lower not in cls._parsers:
            raise FileParsingError(
                f"Unsupported file type: {file_type}. Supported types: {', '.join(cls._parsers.keys())}"
            )
        return cls._parsers[file_type_lower]()
