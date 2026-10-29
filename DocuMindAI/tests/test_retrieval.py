"""Tests for retrieval.py (TC-04, TC-05 and extras)."""
import unittest
from pathlib import Path

from document_processor import process_file
from retrieval import MIN_SCORE, Retriever, tokenize
from tests.pdf_helper import SAMPLE_PAGES, make_pdf

ROOT = Path(__file__).resolve().parent.parent
TXT = process_file("sample_policy.txt", (ROOT / "sample_documents" / "sample_policy.txt").read_bytes())
PDF = process_file("sample_policy.pdf", make_pdf(SAMPLE_PAGES))


class TestRetrieval(unittest.TestCase):
    def test_tc04_answerable_question_returns_evidence_with_source(self):
        results = Retriever(TXT.chunks).search("How much is the home office stipend?")
        self.assertTrue(results)
        top = results[0]
        self.assertIn("$500", top.chunk.text)
        self.assertEqual(top.chunk.source, "sample_policy.txt")
        self.assertIsNone(top.chunk.page)
        self.assertGreaterEqual(top.score, MIN_SCORE)

    def test_tc04_stemming_matches_word_variants(self):
        results = Retriever(TXT.chunks).search("Can employees work remotely?")
        self.assertIn("three days per week", results[0].chunk.text)

    def test_tc04_pdf_results_carry_page_numbers(self):
        retriever = Retriever(PDF.chunks)
        meal = retriever.search("What is the daily meal allowance for business travel?")[0]
        self.assertEqual((meal.chunk.source, meal.chunk.page), ("sample_policy.pdf", 1))
        laptop = retriever.search("How often are company laptops replaced?")[0]
        self.assertEqual(laptop.chunk.page, 2)

    def test_multiple_documents_are_searched_together(self):
        retriever = Retriever(TXT.chunks + PDF.chunks)
        self.assertEqual(retriever.search("When must expense reports be submitted?")[0].chunk.source,
                         "sample_policy.txt")
        self.assertEqual(retriever.search("What is the maximum hotel cost per night?")[0].chunk.source,
                         "sample_policy.pdf")

    def test_tc05_unsupported_question_returns_no_evidence(self):
        retriever = Retriever(TXT.chunks + PDF.chunks)
        self.assertEqual(retriever.search("What is the CEO's salary?"), [])

    def test_tc05_irrelevant_question_returns_no_evidence(self):
        retriever = Retriever(TXT.chunks + PDF.chunks)
        self.assertEqual(retriever.search("What is the capital of France?"), [])

    def test_empty_and_stopword_only_queries_return_nothing(self):
        retriever = Retriever(TXT.chunks)
        for query in ("", "   ", "what is the", None):
            self.assertEqual(retriever.search(query), [])

    def test_empty_retriever_returns_nothing(self):
        self.assertEqual(Retriever([]).search("anything"), [])

    def test_top_k_is_respected_and_scores_sorted(self):
        results = Retriever(TXT.chunks + PDF.chunks).search("employees work", top_k=1)
        self.assertLessEqual(len(results), 1)
        many = Retriever(TXT.chunks + PDF.chunks).search("employees company work days", top_k=3)
        scores = [r.score for r in many]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_tokenize_drops_stopwords_and_stems(self):
        self.assertEqual(tokenize("The employees are working remotely"), ["employee", "work", "remote"])


if __name__ == "__main__":
    unittest.main()
