# DocuMind AI - Actual Evaluation Results

Executed on 2026-10-30 in a sandbox with **Python 3.12.3**, **no internet access**, and these
packages available: scikit-learn 1.8.0, requests 2.33.1, python-dotenv 1.2.2, pypdf 5.9.0.
**Not installed in that sandbox:** `pytest`, `streamlit`, `PyMuPDF`, `groq`. This limits what could be verified
(see NOT RUN rows). Re-run everything on your own machine to confirm.

## Commands that were actually executed

```
python3 -m unittest discover -s tests -t . -v      ->  Ran 41 tests ... OK  (0 failures, 0 errors)
python3 evaluation/run_evaluation.py               ->  completed; observed output summarised below
```

## Results per test case

| ID | Observed result | Status | Notes |
|----|-----------------|--------|-------|
| TC-01 | `sample_policy.txt`: 204 words, 1,258 characters, 2 chunks, page = none | PASS | |
| TC-02 | 2-page PDF: 2 pages, 59 words, chunks on pages [1, 2] | PASS | Ran with the **pypdf** fallback reader. The PyMuPDF path is NOT RUN (not installed here). |
| TC-03 | Empty file, corrupted PDF, text-free PDF, `.docx`, binary-as-`.txt`, oversized file all raised `DocumentError` with readable messages | PASS | A stray `EOF marker not found` line from pypdf is printed to stderr for the corrupted PDF; harmless. |
| TC-04 | Stipend question: top passage contains `$500`, source `sample_policy.txt`, score 0.355. Remote-work question: top score 0.322 | PASS (retrieval) | The wording of an LLM-written answer was NOT RUN. Offline, the extractive fallback quoted the correct sentence. |
| TC-05 | CEO salary and capital of France: 0 passages, `no_evidence`, no API call. "Dental coverage": 1 weakly matching passage retrieved; the extractive fallback correctly refused to answer | PASS (retrieval and fallback) | How a real LLM behaves on weakly-related passages like the dental one is NOT RUN. It relies on the prompt rule and is unverified. |
| TC-06 | No key, 401, 429, 503, timeout, connection error, malformed body, HTTP 400: all returned a labelled fallback notice; fake key never appeared in output | PASS | Failures were **simulated with mocked HTTP**. No real request to Groq was made. |
| TC-07 | Meal allowance -> `sample_policy.pdf, page 1`; laptop replacement -> page 2 | PASS | |
| TC-08 | Expense question -> `.txt`; hotel question -> `.pdf` | PASS | |
| TC-09 | `""`, `"   "`, `"what is the"`, `None` -> no results, no crash | PASS | |
| TC-10 | Streamlit not installed; app could not be launched | **NOT RUN** | Substitute: `app.py` compiles, and its logic was executed once against a stubbed `streamlit` (bad PDF and empty file showed errors, valid TXT processed, question answered via fallback). A stub is not a real browser run. |
| TC-11 | No API key and no network | **NOT RUN** | The live Groq request format is based on Groq's OpenAI-compatible API and is untested against the real service. The default model name may need updating. |
| TC-12 | `pytest` not installed | **NOT RUN** | Tests are `unittest.TestCase` classes, which pytest collects natively; not confirmed. |
| TC-13 | In a throwaway git repo, `.env` and `.venv/` were untracked and `.env.example` tracked; no key-like strings found | PASS | |

## Known limitations observed

- TF-IDF matches words, not meaning. A question using different wording than the document can fail
  to retrieve the right passage, and a generic word can retrieve an unrelated one (e.g. "company").
- The extractive fallback is crude: it returns whole sentences and may include a heading glued to the sentence.
- Single-turn Q&A: previous chat messages are not sent to the model, so follow-up questions like "and the second one?" won't work.
- Scanned (image-only) PDFs are rejected because OCR is not implemented.
