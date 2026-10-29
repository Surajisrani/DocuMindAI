# DocuMind AI - Test Cases

Test data: `sample_documents/sample_policy.txt` (fictional "Northwind Analytics" handbook) and an
in-memory 2-page PDF built by `tests/pdf_helper.py` (also saved as `sample_documents/sample_policy.pdf`).

| ID | Scenario | Expected behaviour | Automated by |
|----|----------|--------------------|--------------|
| TC-01 | Process a valid TXT file | Text extracted, chunked, statistics reported, no page numbers | `test_document_processor.py::test_tc01_*` |
| TC-02 | Process a valid 2-page PDF | Per-page text, chunks carry page 1 and 2 | `test_tc02_*` |
| TC-03 | Empty file, whitespace-only TXT, corrupted PDF, text-free PDF, unsupported `.docx`, binary file named `.txt`, oversized file | Each rejected with a clear `DocumentError`; no crash | `test_tc03_*`, `test_oversized_*` |
| TC-04 | "How much is the home office stipend?" (answer present) | Top passage contains `$500`, with source filename | `test_retrieval.py::test_tc04_*` |
| TC-05 | "What is the CEO's salary?" / "What is the capital of France?" (not in document) | No passages retrieved, no answer invented, "not enough information" message, no API call | `test_tc05_*` (retrieval and agent) |
| TC-06 | No API key; HTTP 401; HTTP 429; HTTP 5xx; timeout; no network; malformed response | Clear notice, labelled extractive fallback, key never leaked | `test_agent.py::test_tc06_*` (HTTP is mocked) |
| TC-07 | Page references for PDFs | Meal-allowance answer is on page 1, laptop-replacement on page 2 | `test_tc04_pdf_results_carry_page_numbers` |
| TC-08 | Two documents loaded together | Each question retrieves from the correct file | `test_multiple_documents_*` |
| TC-09 | Empty / stop-word-only question | No results, no crash | `test_empty_and_stopword_only_*` |
| TC-10 | Launch the Streamlit app and use the UI | App starts; upload, question, answer and errors display | Manual (see README) |
| TC-11 | Live Groq answer | Answer written by the model, cites `[S#]`, says "not enough information" when unsupported | Manual, needs a real key |
| TC-12 | Run suite with `pytest` | Same results as `unittest` | `python -m pytest -v` |
| TC-13 | `.gitignore` excludes `.env`, `.venv`, caches | Those files untracked, `.env.example` tracked | Manual `git` check |

Also covered by unit tests: chunk overlap and sizes, invalid chunk parameters, Windows-1252 text,
filename path stripping, blank page warning, grounded prompt contents, ignoring invalid `[S9]` citations,
default/override of `GROQ_MODEL`, placeholder API key treated as missing.
