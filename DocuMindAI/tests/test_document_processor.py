"""Tests for document_processor.py (TC-01, TC-02, TC-03 and extras)."""
import unittest
from pathlib import Path

from document_processor import (DocumentError, chunk_text, pdf_backend, process_file)
from tests.pdf_helper import SAMPLE_PAGES, make_pdf

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_TXT = (ROOT / "sample_documents" / "sample_policy.txt").read_bytes()


class TestValidDocuments(unittest.TestCase):
    def test_tc01_valid_txt_is_processed(self):
        doc = process_file("sample_policy.txt", SAMPLE_TXT)
        self.assertEqual(doc.file_type, "txt")
        self.assertIsNone(doc.num_pages)
        self.assertGreater(doc.num_words, 100)
        self.assertGreater(len(doc.chunks), 0)
        self.assertTrue(all(c.source == "sample_policy.txt" and c.page is None for c in doc.chunks))
        self.assertIn("$500", " ".join(c.text for c in doc.chunks))

    def test_tc02_valid_pdf_is_processed_with_page_numbers(self):
        self.assertIsNotNone(pdf_backend(), "no PDF library installed")
        doc = process_file("policy.pdf", make_pdf(SAMPLE_PAGES))
        self.assertEqual(doc.file_type, "pdf")
        self.assertEqual(doc.num_pages, 2)
        self.assertEqual({c.page for c in doc.chunks}, {1, 2})
        page1 = " ".join(c.text for c in doc.chunks if c.page == 1)
        page2 = " ".join(c.text for c in doc.chunks if c.page == 2)
        self.assertIn("meal allowance", page1)
        self.assertIn("laptops", page2)
        self.assertEqual(doc.chunks[0].label(), "policy.pdf, page 1")

    def test_blank_page_in_pdf_gives_warning_not_error(self):
        doc = process_file("mixed.pdf", make_pdf([["Some real text on page one."], []]))
        self.assertEqual(doc.num_pages, 2)
        self.assertEqual(len(doc.warnings), 1)

    def test_txt_with_windows_encoding_is_decoded(self):
        doc = process_file("cafe.txt", "Caf\u00e9 opens at nine.".encode("cp1252"))
        self.assertIn("Caf\u00e9", doc.chunks[0].text)

    def test_directory_part_of_filename_is_dropped(self):
        doc = process_file("../../etc/notes.txt", b"hello world")
        self.assertEqual(doc.name, "notes.txt")


class TestRejectedDocuments(unittest.TestCase):
    def test_tc03_empty_file_rejected(self):
        with self.assertRaises(DocumentError):
            process_file("empty.txt", b"")

    def test_tc03_whitespace_only_txt_rejected(self):
        with self.assertRaises(DocumentError):
            process_file("blank.txt", b"  \n\t \n")

    def test_tc03_corrupted_pdf_rejected(self):
        with self.assertRaises(DocumentError) as ctx:
            process_file("broken.pdf", b"%PDF-1.4 this is not really a pdf")
        self.assertIn("broken.pdf", str(ctx.exception))

    def test_tc03_text_free_pdf_rejected(self):
        with self.assertRaises(DocumentError) as ctx:
            process_file("scan.pdf", make_pdf([[], []]))
        self.assertIn("no extractable text", str(ctx.exception))

    def test_tc03_unsupported_extension_rejected(self):
        with self.assertRaises(DocumentError) as ctx:
            process_file("report.docx", b"data")
        self.assertIn("unsupported", str(ctx.exception).lower())

    def test_tc03_binary_file_renamed_to_txt_rejected(self):
        with self.assertRaises(DocumentError):
            process_file("image.txt", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

    def test_oversized_file_rejected(self):
        with self.assertRaises(DocumentError):
            process_file("huge.txt", b"a" * (20 * 1024 * 1024 + 1))


class TestChunking(unittest.TestCase):
    def test_long_text_split_into_overlapping_chunks(self):
        text = " ".join(f"w{i}" for i in range(250))
        chunks = chunk_text(text, size=100, overlap=20)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(len(c.split()) <= 100 for c in chunks))
        self.assertEqual(set(chunks[0].split()[-20:]), set(chunks[1].split()[:20]))
        self.assertIn("w249", chunks[-1])

    def test_short_text_is_one_chunk_and_empty_text_is_none(self):
        self.assertEqual(chunk_text("just a few words"), ["just a few words"])
        self.assertEqual(chunk_text("   \n "), [])

    def test_invalid_parameters_raise(self):
        with self.assertRaises(ValueError):
            chunk_text("abc", size=10, overlap=10)


if __name__ == "__main__":
    unittest.main()
