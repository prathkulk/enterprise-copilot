from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from docx import Document as DocxDocument
from pypdf import PdfReader


@dataclass
class ExtractionResult:
    extracted_text: str
    parser_metadata: dict[str, object]


class DocumentParser(Protocol):
    parser_name: str

    def parse(self, file_path: Path) -> ExtractionResult:
        ...


class TxtDocumentParser:
    parser_name = "txt"

    def parse(self, file_path: Path) -> ExtractionResult:
        extracted_text = file_path.read_text(encoding="utf-8", errors="ignore")
        return ExtractionResult(
            extracted_text=extracted_text,
            parser_metadata={
                "parser": self.parser_name,
                "page_markers_included": False,
                "character_count": len(extracted_text),
                "line_count": len(extracted_text.splitlines()),
            },
        )


class PdfDocumentParser:
    parser_name = "pdf"

    def parse(self, file_path: Path) -> ExtractionResult:
        reader = PdfReader(str(file_path))
        page_chunks: list[str] = []
        extracted_pages = 0

        for index, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                extracted_pages += 1
            page_chunks.append(f"[Page {index}]\n{page_text}")

        extracted_text = "\n\n".join(page_chunks).strip()
        return ExtractionResult(
            extracted_text=extracted_text,
            parser_metadata={
                "parser": self.parser_name,
                "page_markers_included": True,
                "page_count": len(reader.pages),
                "extracted_pages": extracted_pages,
                "character_count": len(extracted_text),
            },
        )


class DocxDocumentParser:
    parser_name = "docx"

    def parse(self, file_path: Path) -> ExtractionResult:
        document = DocxDocument(str(file_path))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        extracted_text = "\n\n".join(paragraphs)
        return ExtractionResult(
            extracted_text=extracted_text,
            parser_metadata={
                "parser": self.parser_name,
                "page_markers_included": False,
                "paragraph_count": len(paragraphs),
                "character_count": len(extracted_text),
            },
        )
