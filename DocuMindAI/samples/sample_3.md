# Sample 3 - Document-processing errors and API failure

> Part A and Part B are **real output** from executing the project on 2026-10-30.
> The HTTP failures in Part B were **simulated with mocked responses**; no real Groq request was made.

## Part A - Rejected files (real)

```
'empty.txt' is empty (0 bytes).
'broken.pdf': The PDF could not be read. It may be corrupted.
'scan.pdf' contains no extractable text. If it is a scanned PDF, OCR is not supported.
'a.docx': unsupported file type '.docx'. Please upload a PDF or TXT file.
```

## Part B - API problems (real messages, simulated failures)

```
HTTP 401 -> AI answer unavailable: The Groq API key was rejected (invalid or unauthorised). Check GROQ_API_KEY. Showing the closest matching sentences instead (extractive fallback, not AI-generated).
HTTP 429 -> AI answer unavailable: Groq rate limit reached. Wait a moment and try again. Showing the closest matching sentences instead (extractive fallback, not AI-generated).
Timeout  -> AI answer unavailable: The request to Groq timed out. Showing the closest matching sentences instead (extractive fallback, not AI-generated).
Offline  -> AI answer unavailable: Could not connect to Groq. Check your internet connection. Showing the closest matching sentences instead (extractive fallback, not AI-generated).
```
