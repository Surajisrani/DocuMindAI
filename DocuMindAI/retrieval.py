"""TF-IDF retrieval over document chunks (runs fully locally, no API needed)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from document_processor import Chunk

TOP_K = 4
MIN_SCORE = 0.08  # cosine similarity below this is treated as "no evidence"


@dataclass
class RetrievedPassage:
    chunk: Chunk
    score: float


def _stem(token: str) -> str:
    """Very small suffix stripper so 'remotely' matches 'remote', 'days' matches 'day'."""
    for suffix in ("ing", "ly", "ed", "s"):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            if suffix == "s" and token.endswith("ss"):
                continue
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> List[str]:
    """Lowercase, drop stop words, stem. Used by retrieval and the extractive fallback."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(t) for t in tokens if t not in ENGLISH_STOP_WORDS and len(t) > 1]


def _analyzer(text: str) -> List[str]:
    tokens = tokenize(text)
    return tokens + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


class Retriever:
    """Fit once on a list of chunks, then call search(question)."""

    def __init__(self, chunks: Sequence[Chunk]):
        self.chunks = list(chunks)
        self._vectorizer = None
        self._matrix = None
        if self.chunks:
            try:
                self._vectorizer = TfidfVectorizer(analyzer=_analyzer, sublinear_tf=True)
                self._matrix = self._vectorizer.fit_transform([c.text for c in self.chunks])
            except ValueError:  # empty vocabulary (e.g. text made only of stop words)
                self._vectorizer = None
                self._matrix = None

    def search(self, query: str, top_k: int = TOP_K, min_score: float = MIN_SCORE) -> List[RetrievedPassage]:
        if self._vectorizer is None or not query or not query.strip():
            return []
        if not tokenize(query):
            return []
        query_vec = self._vectorizer.transform([query])
        if query_vec.nnz == 0:  # no query term occurs in the documents
            return []
        scores = (self._matrix @ query_vec.T).toarray().ravel()
        order = scores.argsort()[::-1][:top_k]
        return [RetrievedPassage(self.chunks[i], float(scores[i])) for i in order if scores[i] >= min_score]
