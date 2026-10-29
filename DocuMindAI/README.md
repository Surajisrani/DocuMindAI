# DocuMind AI - Intelligent Document Question-Answering Agent

Upload PDF or TXT documents, ask questions in plain English, and get answers **grounded in your documents**,
with source filenames and page numbers. If the documents don't contain the answer, DocuMind says so instead of guessing.

## Problem statement

Searching long policies, contracts or reports by hand is slow, and general chatbots happily invent answers.
DocuMind AI retrieves the relevant passages from *your* files first, then asks an LLM to answer **only from that evidence**.

## Features

- Upload one or more `.pdf` / `.txt` files; unsupported, empty, corrupted, password-protected and text-free files are rejected with clear messages
- Page-aware text extraction (PDF), chunking with overlap, per-file statistics
- Local TF-IDF retrieval (no embeddings, no database, no extra service)
- Grounded answers from the Groq API with `[S1]`-style citations that map to real retrieved passages
- Honest fallback: with no API key, or when the API fails, an **extractive fallback** shows matching sentences and is labelled as *not AI-generated*
- "Not enough information" response when retrieval finds nothing relevant (the LLM is not even called)
- Clear-session buttons, automated tests, evaluation documents

## Architecture

```
DocuMindAI/
    app.py                  Streamlit UI only
    document_processor.py   validation, PDF/TXT extraction, chunking
    retrieval.py            TF-IDF search, returns passages with source metadata
    agent.py                Groq call, grounding prompt, error handling, extractive fallback
    requirements.txt  .env.example  .gitignore  pytest.ini
    sample_documents/       sample_policy.txt, sample_policy.pdf (test data)
    evaluation/             test_cases.md, evaluation_results.md, run_evaluation.py
    samples/                sample_1.md, sample_2.md, sample_3.md (example outputs, labelled real vs illustrative)
    tests/                  test_document_processor.py, test_retrieval.py, test_agent.py, pdf_helper.py
```

Flow: upload -> `process_file` -> chunks -> `Retriever.search(question)` -> top passages -> `answer_question` -> answer + sources.

## Technology stack

Python, Streamlit, PyMuPDF (pypdf as automatic fallback reader), scikit-learn (TF-IDF), requests (Groq REST API),
python-dotenv, pytest. The Groq call uses plain HTTPS rather than the `groq` SDK, to keep dependencies small and mockable in tests.

## Prerequisites

- Python 3.10 or newer (developed and tested with 3.12)
- A free Groq API key from <https://console.groq.com/keys> (optional: the app works without it in fallback mode)

## Installation (Windows, PowerShell or Command Prompt)

```
cd DocuMindAI
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use Command Prompt.
On macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`.

## Configure the API key

```
copy .env.example .env
```

Open `.env` in a text editor and replace `your_groq_api_key_here` with your key. Optionally set `GROQ_MODEL`
(default `llama-3.1-8b-instant`). Groq retires models over time; if you get an HTTP 400 "model" error, pick a current model
from <https://console.groq.com/docs/models>. Never commit `.env` (it is git-ignored).

## Run

```
streamlit run app.py
```

Your browser opens at <http://localhost:8501>. Upload `sample_documents/sample_policy.txt` and ask, for example:
"How many days per week can employees work remotely?" or "What is the CEO's salary?"

## Run the tests

```
python -m pytest -v
```

No API key or internet is needed; Groq responses and failures are mocked. Without pytest installed you can also run
`python -m unittest discover -s tests -t . -v`. To print observed behaviour for the evaluation scenarios: `python evaluation/run_evaluation.py`.

## Evaluation summary

Actual results are in [`evaluation/evaluation_results.md`](evaluation/evaluation_results.md). On the development machine:
41 automated tests ran under `unittest` and all passed, covering TXT/PDF processing, rejection of bad files, retrieval with
source metadata, unsupported questions, multi-document search, and missing-key / API-failure handling (mocked).

**Not verified in that environment** (no internet, packages unavailable): launching the real Streamlit UI, the PyMuPDF code path,
running the suite under `pytest`, and any live Groq call. Please run these yourself and update the results file.

## Example usage

| You ask | DocuMind responds |
|---|---|
| How much is the home office stipend? | Grounded answer citing `sample_policy.txt` |
| What is the daily meal allowance for business travel? | Answer citing `sample_policy.pdf, page 1` |
| What is the CEO's salary? | "The document does not provide enough information to answer this question." |

See [`samples/`](samples/) for transcripts (each clearly marked *real* or *illustrative*).

## Limitations

- Keyword-based retrieval (TF-IDF): paraphrased questions may miss the right passage; generic words can retrieve weak matches
- Single-turn answers: earlier chat messages are not sent to the model
- No OCR: scanned PDFs are rejected; tables and multi-column layouts may extract poorly
- Documents live in memory for the session only; nothing is stored on disk
- Whether the LLM always obeys "use only the evidence" cannot be guaranteed; always check the cited passages
- Live Groq behaviour was not tested by the author of this repository's test suite (see above)

## Future improvements

Semantic embeddings, OCR for scans, conversation memory, highlighted source text, persistent index, answer-quality evaluation set, CI on GitHub Actions.

## Security notes

- The API key is read only from environment variables / `.env`; it is never hard-coded, logged, or shown in the UI or error messages
- `.env`, `.venv`, caches are in `.gitignore`; only `.env.example` (placeholders) is committed
- Uploaded text is sent to Groq when a key is configured; do not upload confidential documents unless that is acceptable to you
- Uploaded documents could contain instructions aimed at the model (prompt injection); the prompt tells the model to treat them as evidence only, which reduces but does not eliminate the risk
