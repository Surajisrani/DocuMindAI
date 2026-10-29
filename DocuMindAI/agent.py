"""Grounded answer generation using the Groq API, with honest fallbacks.

answer_question() never raises for expected problems (missing key, rate limit,
network failure...). It returns an Answer whose `mode` says what really happened:

  "llm"          - answer written by the Groq model from the retrieved passages
  "fallback"     - LLM unavailable; deterministic extract of matching sentences
  "no_evidence"  - retrieval found nothing relevant; no LLM call was made
  "error"        - invalid input (e.g. empty question)
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import requests

from retrieval import RetrievedPassage, tokenize

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"  # override with GROQ_MODEL; Groq may retire models over time
REQUEST_TIMEOUT = 30
PLACEHOLDER_KEYS = {"", "your_groq_api_key_here", "your-api-key-here"}

INSUFFICIENT = "The document does not provide enough information to answer this question."

SYSTEM_PROMPT = (
    "You answer questions about uploaded documents using ONLY the numbered evidence "
    "passages supplied by the user. Rules:\n"
    "1. Use only facts stated in the passages. Do not use outside knowledge.\n"
    f"2. If the passages do not contain the answer, reply exactly: {INSUFFICIENT}\n"
    "3. Cite the passages you used with their tags, e.g. [S1] or [S2][S3].\n"
    "4. Never invent quotations, page numbers, filenames or facts.\n"
    "5. Be concise."
)


class GroqError(Exception):
    """Internal: carries a safe, user-readable reason why the API call failed."""


@dataclass
class Answer:
    text: str
    mode: str
    cited: List[Tuple[int, RetrievedPassage]] = field(default_factory=list)      # (S-number, passage)
    retrieved: List[RetrievedPassage] = field(default_factory=list)
    notice: Optional[str] = None
    model: Optional[str] = None


def get_api_key() -> Optional[str]:
    key = (os.getenv("GROQ_API_KEY") or "").strip()
    return None if key in PLACEHOLDER_KEYS else key


def get_model() -> str:
    return (os.getenv("GROQ_MODEL") or "").strip() or DEFAULT_MODEL


def build_messages(question: str, passages: Sequence[RetrievedPassage]) -> list:
    blocks = [f"[S{i}] ({p.chunk.label()})\n{p.chunk.text}" for i, p in enumerate(passages, 1)]
    user = "EVIDENCE PASSAGES:\n\n" + "\n\n".join(blocks) + f"\n\nQUESTION: {question}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def call_groq(question: str, passages: Sequence[RetrievedPassage], api_key: str,
              model: str, timeout: int = REQUEST_TIMEOUT) -> str:
    """Call Groq's OpenAI-compatible endpoint. Raises GroqError with a safe message."""
    payload = {"model": model, "messages": build_messages(question, passages),
               "temperature": 0, "max_tokens": 600}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=timeout)
    except requests.exceptions.Timeout:
        raise GroqError("The request to Groq timed out.") from None
    except requests.exceptions.ConnectionError:
        raise GroqError("Could not connect to Groq. Check your internet connection.") from None
    except requests.exceptions.RequestException:
        raise GroqError("The request to Groq failed.") from None

    status = resp.status_code
    if status in (401, 403):
        raise GroqError("The Groq API key was rejected (invalid or unauthorised). Check GROQ_API_KEY.")
    if status == 429:
        raise GroqError("Groq rate limit reached. Wait a moment and try again.")
    if status >= 500:
        raise GroqError(f"Groq service error (HTTP {status}). Try again later.")
    if status != 200:
        detail = ""
        try:
            detail = str(resp.json().get("error", {}).get("message", ""))[:200]
        except Exception:
            pass
        raise GroqError(f"Groq returned HTTP {status}. {detail}".strip())
    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception:
        raise GroqError("Groq returned an unexpected response format.") from None
    if not content or not content.strip():
        raise GroqError("Groq returned an empty answer.")
    return content.strip()


def extractive_fallback(question: str, passages: Sequence[RetrievedPassage], max_sentences: int = 3) -> str:
    """Deterministic, non-AI answer: the sentences that share the most terms with the question."""
    q_terms = set(tokenize(question))
    # A sentence must cover at least half of the question's content words; this stops
    # a single generic word (e.g. "company") from producing a misleading "answer".
    min_overlap = max(1, math.ceil(len(q_terms) / 2))
    scored = []
    for p_idx, passage in enumerate(passages):
        for sentence in re.split(r"(?<=[.!?])\s+|\n\s*\n", passage.chunk.text):
            overlap = len(q_terms & set(tokenize(sentence)))
            if overlap >= min_overlap:
                scored.append((-overlap, p_idx, sentence.strip(), passage))
    if not scored:
        return INSUFFICIENT
    scored.sort(key=lambda t: (t[0], t[1]))
    best = -scored[0][0]
    lines, seen = [], set()
    for neg_overlap, _, sentence, passage in scored:
        if -neg_overlap < best - 1 or sentence in seen:  # skip clearly weaker matches
            continue
        seen.add(sentence)
        lines.append(f"- {sentence}  ({passage.chunk.label()})")
        if len(lines) == max_sentences:
            break
    return "\n".join(lines)


def _cited_passages(text: str, passages: Sequence[RetrievedPassage]) -> List[Tuple[int, RetrievedPassage]]:
    numbers = sorted({int(n) for n in re.findall(r"\[S(\d+)\]", text)})
    return [(n, passages[n - 1]) for n in numbers if 1 <= n <= len(passages)]


def answer_question(question: str, passages: Sequence[RetrievedPassage],
                    api_key: Optional[str] = None, model: Optional[str] = None) -> Answer:
    question = (question or "").strip()
    if not question:
        return Answer("Please type a question.", "error")
    if not passages:
        return Answer(INSUFFICIENT + " No relevant passages were found in the uploaded documents.",
                      "no_evidence")

    passages = list(passages)
    key = get_api_key() if api_key is None else (None if api_key.strip() in PLACEHOLDER_KEYS else api_key.strip())
    model = model or get_model()

    if not key:
        return Answer(extractive_fallback(question, passages), "fallback", retrieved=passages,
                      notice="No GROQ_API_KEY is configured, so no AI model was used. "
                             "Showing the closest matching sentences instead (extractive fallback).")
    try:
        text = call_groq(question, passages, key, model)
    except GroqError as exc:
        return Answer(extractive_fallback(question, passages), "fallback", retrieved=passages,
                      notice=f"AI answer unavailable: {exc} Showing the closest matching sentences "
                             "instead (extractive fallback, not AI-generated).")
    return Answer(text, "llm", cited=_cited_passages(text, passages), retrieved=passages, model=model)
