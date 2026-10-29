# DocuMind AI — Intelligent Document Research Assistant

DocuMind AI is a Python-based document question-answering assistant built with Streamlit and Groq.

# Features

- Upload PDF and TXT documents.
- Extract and clean document text.
- Retrieve relevant passages using lightweight TF-IDF-style retrieval.
- Generate answers using the Groq API.
- Display source filenames and PDF page references.
- Handle unsupported questions using evidence-aware responses.
- Provide an extractive fallback when AI synthesis is unavailable.
- Maintain chat history during the current session.

# Technology Stack

- Python
- Streamlit
- PyMuPDF
- Groq API
- pytest

# Project Structure

The current application files are inside the `DocuMindAI/` directory.

# Run Locally

Open the `DocuMindAI` project directory in VS Code, activate your virtual environment, and install the dependencies:

`pip install -r requirements.txt`

Configure your Groq API key in a local `.env` file. Set `GROQ_MODEL` to a model ID available to your account.

Start the application:

`python -m streamlit run app.py`

Run automated tests:

`python -m pytest -q`

# Security

Never commit `.env`, API keys, or your virtual environment to GitHub.

# Limitations

Scanned PDFs may require OCR. Verify retrieved evidence and citations before relying on generated answers.
