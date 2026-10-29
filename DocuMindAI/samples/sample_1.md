# Sample 1 - Question answered from document evidence

> Part A is **real output** from running the project offline on 2026-10-30.
> Part B is **illustrative only**. It was NOT produced by a live Groq call, because no API key or network was available.

**Document:** `sample_documents/sample_policy.txt`
**Question:** How many days per week can employees work remotely?

## Part A - Actual retrieval result (no API key, extractive fallback)

```
Retrieved: sample_policy.txt (relevance 0.322), sample_policy.txt (relevance 0.108)
Mode: fallback
Notice: No GROQ_API_KEY is configured, so no AI model was used. Showing the closest matching sentences instead (extractive fallback).
- Section 1: Remote Work Employees may work remotely up to three days per week after completing the 90-day probation period.  (sample_policy.txt)
```

## Part B - Illustrative AI-mode answer (what the UI is designed to show with a valid key)

```
Employees may work remotely up to three days per week, once they have completed the 90-day probation period [S1].

Sources cited
- [S1] sample_policy.txt (relevance 0.32)
```
