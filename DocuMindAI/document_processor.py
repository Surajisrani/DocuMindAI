"""Document validation, text extraction and chunking.

Turns an uploaded PDF or TXT file (raw bytes) into a ProcessedDocument made of
Chunk objects. Every chunk remembers its source filename and (for PDFs) page.
This module has no dependency on Streamlit.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

SUPPORTED_EXTENSIONS = (".pdf", ".txt")
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB
CHUNK_WORDS = 120    # target words per chunk
CHUNK_OVERLAP = 30   # words shared between neighbouring chunks


class DocumentError(Exception):
    """Raised with a user-friendly message when a file cannot be processed."""


@dataclass(frozen=True)
class Chunk:
    text: str
    source: str            # original filename
    page: Optional[int]    # 1-based page for PDFs, None for TXT
    chunk_id: int

    def label(self) -> str:
        return f"{self.source}, page {self.page}" if self.page else self.source


@dataclass
class ProcessedDocument:
    name: str
    file_type: str                  # "pdf" or "txt"
    num_pages: Optional[int]        # None for TXT
    num_chars: int
    num_words: int
    chunks: List[Chunk] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping windows of roughly `size` words.

    Blank lines (paragraph breaks) are kept as "\\n\\n"; other whitespace becomes one space.
    """
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("size must be > 0 and 0 <= overlap < size")
    # each item is a word followed by the separator that came after it
    items = [m.group(1) + ("\n\n" if m.group(2).count("\n") >= 2 else " ")
             for m in re.finditer(r"(\S+)(\s*)", text)]
    if not items:
        return []
    step = size - overlap
    chunks = []
    for start in range(0, len(items), step):
        chunks.append("".join(items[start:start + size]).strip())
        if start + size >= len(items):
            break
    return chunks


def pdf_backend() -> Optional[str]:
    """Name of the PDF library that will be used, or None if none is installed."""
    try:
        import fitz  # noqa: F401  (PyMuPDF)
        return "PyMuPDF"
    except ImportError:
        pass
    try:
        import pypdf  # noqa: F401
        return "pypdf"
    except ImportError:
        return None


def extract_pdf_pages(data: bytes) -> List[str]:
    """Return the text of each PDF page. Prefers PyMuPDF, falls back to pypdf."""
    backend = pdf_backend()
    if backend == "PyMuPDF":
        import fitz
        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                if doc.needs_pass:
                    raise DocumentError("This PDF is password-protected and cannot be read.")
                return [page.get_text("text") for page in doc]
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("The PDF could not be read. It may be corrupted.") from exc
    if backend == "pypdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise DocumentError("This PDF is password-protected and cannot be read.")
            return [(page.extract_text() or "") for page in reader.pages]
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("The PDF could not be read. It may be corrupted.") from exc
    raise DocumentError("No PDF library is installed. Run: pip install -r requirements.txt")


def decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise DocumentError("The text file uses an unsupported encoding.")


def process_file(filename: str, data: bytes) -> ProcessedDocument:
    """Validate, extract and chunk one uploaded file. Raises DocumentError on failure."""
    name = Path(filename or "").name
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DocumentError(f"'{name}': unsupported file type '{ext or 'none'}'. Please upload a PDF or TXT file.")
    if not data:
        raise DocumentError(f"'{name}' is empty (0 bytes).")
    if len(data) > MAX_FILE_BYTES:
        raise DocumentError(f"'{name}' is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")

    warnings: List[str] = []
    if ext == ".txt":
        if b"\x00" in data[:4096] and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
            raise DocumentError(f"'{name}' looks like a binary file, not plain text.")
        pages = [decode_text(data)]
        page_numbers: List[Optional[int]] = [None]
        num_pages = None
    else:
        try:
            pages = extract_pdf_pages(data)
        except DocumentError as exc:
            raise DocumentError(f"'{name}': {exc}") from exc
        page_numbers = list(range(1, len(pages) + 1))
        num_pages = len(pages)
        blank = [n for n, t in zip(page_numbers, pages) if not t.strip()]
        if blank and len(blank) < len(pages):
            warnings.append(f"{len(blank)} page(s) had no extractable text: {blank[:10]}")

    full_text = "\n".join(pages)
    if not full_text.strip():
        raise DocumentError(
            f"'{name}' contains no extractable text. If it is a scanned PDF, OCR is not supported."
        )

    chunks: List[Chunk] = []
    for page_no, page_text in zip(page_numbers, pages):
        for piece in chunk_text(page_text):
            chunks.append(Chunk(text=piece, source=name, page=page_no, chunk_id=len(chunks)))

    return ProcessedDocument(
        name=name,
        file_type=ext.lstrip("."),
        num_pages=num_pages,
        num_chars=len(full_text),
        num_words=len(full_text.split()),
        chunks=chunks,
        warnings=warnings,
    )
