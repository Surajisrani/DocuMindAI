# Sample 2 - Question the document cannot answer

> Part A is **real output** (2026-10-30, offline). Part B is **illustrative only**, not from a live API call.

**Documents loaded:** `sample_policy.txt` and `sample_policy.pdf`

## Part A - Actual results

Question: `What is the CEO's salary?`
```
Retrieved passages: 0
Mode: no_evidence (no API call made)
The document does not provide enough information to answer this question. No relevant passages were found in the uploaded documents.
```

Question: `Does the company offer dental coverage?` (one weakly matching passage was retrieved, so with a valid key the model would be asked)
```
Mode: fallback (no API key)
The document does not provide enough information to answer this question.
```

## Part B - Illustrative AI-mode behaviour for the dental question

The system prompt instructs the model to reply with the exact sentence below when the evidence does not contain the answer.
Whether a given model always obeys is **not verified** here.

```
The document does not provide enough information to answer this question.
```
