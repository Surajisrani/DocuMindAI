"""DocuMind AI - Streamlit user interface.

Run with:  streamlit run app.py
All real work lives in document_processor.py, retrieval.py and agent.py.
"""
import hashlib

import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # reads GROQ_API_KEY / GROQ_MODEL from a local .env file if present

from agent import answer_question, get_api_key, get_model  # noqa: E402
from document_processor import DocumentError, pdf_backend, process_file  # noqa: E402
from retrieval import Retriever  # noqa: E402

st.set_page_config(page_title="DocuMind AI", page_icon="📄", layout="wide")


def safe(text: str) -> str:
    """Streamlit renders $...$ as LaTeX; escape it so prices like $500 display normally."""
    return text.replace("$", "\\$")


def init_state() -> None:
    st.session_state.setdefault("cache", {})        # file hash -> ("ok", doc) or ("error", message)
    st.session_state.setdefault("messages", [])     # chat history
    st.session_state.setdefault("uploader_key", 0)  # changing it empties the uploader widget


def process_uploads(uploaded_files):
    """Process each uploaded file once; return a list of (filename, kind, payload)."""
    results, seen = [], set()
    for f in uploaded_files or []:
        data = f.getvalue()
        key = hashlib.sha1(f.name.encode() + data).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        if key not in st.session_state.cache:
            try:
                st.session_state.cache[key] = ("ok", process_file(f.name, data))
            except DocumentError as exc:
                st.session_state.cache[key] = ("error", str(exc))
            except Exception:  # never let one bad file crash the app
                st.session_state.cache[key] = ("error", f"Unexpected error while reading '{f.name}'.")
        kind, payload = st.session_state.cache[key]
        results.append((f.name, kind, payload))
    return results


def render_answer_details(answer) -> None:
    if answer.mode == "llm":
        st.caption(f"AI-generated answer (Groq model `{answer.model}`) based only on the retrieved passages.")
    elif answer.mode == "fallback":
        st.warning(safe(answer.notice or "Fallback answer."))
    elif answer.mode == "no_evidence":
        st.info("No relevant passages were found, so no answer was generated.")

    if answer.cited:
        st.markdown("**Sources cited**")
        for n, p in answer.cited:
            st.markdown(safe(f"- **[S{n}]** {p.chunk.label()} (relevance {p.score:.2f})"))
    elif answer.mode == "llm" and answer.retrieved:
        st.caption("The model did not cite specific passages. Review the retrieved evidence below.")
    elif answer.mode == "fallback":
        st.markdown("**Sources**")
        for p in answer.retrieved:
            st.markdown(safe(f"- {p.chunk.label()} (relevance {p.score:.2f})"))

    if answer.retrieved:
        with st.expander(f"Retrieved evidence ({len(answer.retrieved)} passages)"):
            for i, p in enumerate(answer.retrieved, 1):
                st.markdown(safe(f"**[S{i}] {p.chunk.label()}**  ·  relevance {p.score:.2f}"))
                st.text(p.chunk.text)


def sidebar() -> None:
    with st.sidebar:
        st.header("Settings")
        if get_api_key():
            st.success(f"Groq API key detected. Model: `{get_model()}`")
        else:
            st.warning(
                "No Groq API key found. Answers will use a simple extractive fallback "
                "(no AI). To enable AI answers: copy `.env.example` to `.env`, put your key "
                "in `GROQ_API_KEY`, and restart the app."
            )
        backend = pdf_backend()
        st.caption(f"PDF reader: {backend or 'none installed'}")
        if st.button("Clear documents and chat", use_container_width=True):
            st.session_state.cache = {}
            st.session_state.messages = []
            st.session_state.uploader_key += 1
            st.rerun()
        if st.button("Clear chat only", use_container_width=True):
            st.session_state.messages = []
            st.rerun()


def main() -> None:
    init_state()
    sidebar()

    st.title("📄 DocuMind AI")
    st.caption("Upload PDF or TXT documents and ask questions. Answers are grounded in your documents, "
               "with source references. If the documents don't contain the answer, DocuMind says so.")

    uploaded = st.file_uploader("Upload documents", type=["pdf", "txt"], accept_multiple_files=True,
                                key=f"uploader_{st.session_state.uploader_key}")
    results = process_uploads(uploaded)
    docs = [payload for _, kind, payload in results if kind == "ok"]

    for name, kind, payload in results:
        if kind == "error":
            st.error(payload)
        else:
            pages = f"{payload.num_pages} page(s) · " if payload.num_pages else ""
            st.success(f"**{payload.name}** processed: {pages}{payload.num_words:,} words · "
                       f"{payload.num_chars:,} characters · {len(payload.chunks)} chunks")
            for w in payload.warnings:
                st.warning(f"{payload.name}: {w}")

    if not docs:
        st.info("Upload at least one PDF or TXT file to begin. "
                "You can try `sample_documents/sample_policy.txt` from this project.")

    prompt = st.chat_input("Ask a question about your documents", disabled=not docs)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Searching your documents..."):
            chunks = [c for d in docs for c in d.chunks]
            answer = answer_question(prompt, Retriever(chunks).search(prompt))
        st.session_state.messages.append({"role": "assistant", "content": answer.text, "answer": answer})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(safe(msg["content"]))
            if msg.get("answer") is not None:
                render_answer_details(msg["answer"])


main()
