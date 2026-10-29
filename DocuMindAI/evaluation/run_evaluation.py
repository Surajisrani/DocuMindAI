"""Runs the offline evaluation scenarios and prints what actually happens.

Usage (from the project root):  python evaluation/run_evaluation.py
No API key or network is needed; the Groq call is only exercised for the failure
paths (missing key, mocked HTTP errors). It does NOT test a live Groq answer.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from agent import answer_question  # noqa: E402
from document_processor import DocumentError, pdf_backend, process_file  # noqa: E402
from retrieval import Retriever  # noqa: E402
from tests.pdf_helper import SAMPLE_PAGES, make_pdf  # noqa: E402

os.environ.pop("GROQ_API_KEY", None)
txt = process_file("sample_policy.txt", (ROOT / "sample_documents" / "sample_policy.txt").read_bytes())
pdf = process_file("sample_policy.pdf", make_pdf(SAMPLE_PAGES))
retriever = Retriever(txt.chunks + pdf.chunks)
print(f"PDF backend in use: {pdf_backend()}\n")


def show(title, value):
    print(f"[{title}]\n{value}\n")


show("TC-01 TXT", f"{txt.name}: type={txt.file_type} words={txt.num_words} chars={txt.num_chars} chunks={len(txt.chunks)}")
show("TC-02 PDF", f"{pdf.name}: type={pdf.file_type} pages={pdf.num_pages} words={pdf.num_words} chunks={len(pdf.chunks)} pages_in_chunks={sorted({c.page for c in pdf.chunks})}")

for label, name, data in [("empty file", "empty.txt", b""), ("corrupted PDF", "broken.pdf", b"%PDF-1.4 junk"),
                          ("text-free PDF", "scan.pdf", make_pdf([[], []])), ("unsupported type", "a.docx", b"x")]:
    try:
        process_file(name, data)
        show(f"TC-03 {label}", "NOT REJECTED (unexpected)")
    except DocumentError as exc:
        show(f"TC-03 {label}", f"DocumentError: {exc}")

for q in ["How many days per week can employees work remotely?", "What is the daily meal allowance for business travel?"]:
    hits = retriever.search(q)
    show("TC-04 retrieval", f"Q: {q}\n" + "\n".join(f"  {h.chunk.label()} score={h.score:.3f}" for h in hits))
    a = answer_question(q, hits)
    show("TC-04 answer (no key -> fallback)", f"mode={a.mode}\nnotice={a.notice}\n{a.text}")

for q in ["What is the CEO's salary?", "What is the capital of France?", "Does the company offer dental coverage?"]:
    hits = retriever.search(q)
    a = answer_question(q, hits)
    show("TC-05 unsupported", f"Q: {q}\nretrieved={len(hits)} passages -> mode={a.mode}\n{a.text}")

q = "How much is the home office stipend?"
hits = retriever.search(q)
a = answer_question(q, hits)
show("TC-06a missing key", f"mode={a.mode}\nnotice={a.notice}")


class R:
    def __init__(self, s): self.status_code = s
    def json(self): return {}


for label, kwargs in [("HTTP 401", dict(return_value=R(401))), ("HTTP 429", dict(return_value=R(429))),
                      ("timeout", dict(side_effect=requests.exceptions.Timeout())),
                      ("no network", dict(side_effect=requests.exceptions.ConnectionError()))]:
    with patch("agent.requests.post", **kwargs):
        a = answer_question(q, hits, api_key="gsk_FAKE_KEY")
    show(f"TC-06b mocked {label}", f"mode={a.mode}\nnotice={a.notice}")
