"""Tests for agent.py (TC-06 and extras). The Groq HTTP call is mocked: no network is used."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

import agent
from agent import INSUFFICIENT, answer_question
from document_processor import process_file
from retrieval import Retriever

ROOT = Path(__file__).resolve().parent.parent
TXT = process_file("sample_policy.txt", (ROOT / "sample_documents" / "sample_policy.txt").read_bytes())
RETRIEVER = Retriever(TXT.chunks)
FAKE_KEY = "gsk_FAKE_SECRET_KEY_123"


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def ok(text):
    return FakeResponse(200, {"choices": [{"message": {"content": text}}]})


def passages(question="How many days per week can employees work remotely?"):
    return RETRIEVER.search(question)


class TestMissingCredentials(unittest.TestCase):
    def test_tc06_missing_api_key_uses_honest_fallback_without_calling_api(self):
        with patch.dict(os.environ, {}, clear=True), patch("agent.requests.post") as post:
            ans = answer_question("How many days per week can employees work remotely?", passages())
        post.assert_not_called()
        self.assertEqual(ans.mode, "fallback")
        self.assertIn("GROQ_API_KEY", ans.notice)
        self.assertIn("no AI model was used", ans.notice)
        self.assertIn("three days per week", ans.text)

    def test_placeholder_key_is_treated_as_missing(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "your_groq_api_key_here"}, clear=True), \
                patch("agent.requests.post") as post:
            ans = answer_question("How much is the home office stipend?", passages("home office stipend"))
        post.assert_not_called()
        self.assertEqual(ans.mode, "fallback")


class TestApiFailures(unittest.TestCase):
    def run_with(self, **post_kwargs):
        with patch("agent.requests.post", **post_kwargs):
            return answer_question("How many days per week can employees work remotely?",
                                   passages(), api_key=FAKE_KEY)

    def check_fallback(self, ans, expected_fragment):
        self.assertEqual(ans.mode, "fallback")
        self.assertIn(expected_fragment, ans.notice)
        self.assertIn("not AI-generated", ans.notice)
        self.assertNotIn(FAKE_KEY, ans.notice + ans.text)

    def test_tc06_invalid_key_401(self):
        self.check_fallback(self.run_with(return_value=FakeResponse(401, {})), "rejected")

    def test_tc06_rate_limit_429(self):
        self.check_fallback(self.run_with(return_value=FakeResponse(429, {})), "rate limit")

    def test_tc06_server_error_500(self):
        self.check_fallback(self.run_with(return_value=FakeResponse(503, {})), "service error")

    def test_tc06_timeout(self):
        self.check_fallback(self.run_with(side_effect=requests.exceptions.Timeout()), "timed out")

    def test_tc06_network_failure(self):
        self.check_fallback(self.run_with(side_effect=requests.exceptions.ConnectionError()), "connect")

    def test_malformed_response_body(self):
        self.check_fallback(self.run_with(return_value=FakeResponse(200, {"unexpected": True})),
                            "unexpected response")

    def test_other_http_error_shows_status(self):
        resp = FakeResponse(400, {"error": {"message": "model not found"}})
        self.check_fallback(self.run_with(return_value=resp), "HTTP 400")


class TestSuccessfulAnswer(unittest.TestCase):
    def test_llm_answer_is_labelled_llm_and_cites_valid_sources_only(self):
        found = passages()
        with patch("agent.requests.post", return_value=ok("Up to three days per week [S1]. See also [S9].")) as post:
            ans = answer_question("How many days per week can employees work remotely?", found,
                                  api_key=FAKE_KEY, model="test-model")
        self.assertEqual(ans.mode, "llm")
        self.assertEqual(ans.model, "test-model")
        self.assertEqual([n for n, _ in ans.cited], [1])           # [S9] does not exist -> ignored
        self.assertIs(ans.cited[0][1], found[0])
        self.assertIsNone(ans.notice)
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {FAKE_KEY}")
        self.assertEqual(kwargs["json"]["temperature"], 0)
        self.assertEqual(kwargs["json"]["model"], "test-model")

    def test_prompt_contains_evidence_question_and_grounding_rules(self):
        found = passages()
        messages = agent.build_messages("How many days?", found)
        self.assertIn(INSUFFICIENT, messages[0]["content"])
        self.assertIn("ONLY", messages[0]["content"])
        self.assertIn("[S1] (sample_policy.txt)", messages[1]["content"])
        self.assertIn("three days per week", messages[1]["content"])
        self.assertIn("QUESTION: How many days?", messages[1]["content"])

    def test_model_saying_insufficient_info_is_passed_through(self):
        with patch("agent.requests.post", return_value=ok(INSUFFICIENT)):
            ans = answer_question("Does the company offer dental coverage?", passages(), api_key=FAKE_KEY)
        self.assertEqual(ans.mode, "llm")
        self.assertEqual(ans.text, INSUFFICIENT)
        self.assertEqual(ans.cited, [])


class TestUnsupportedAndEdgeCases(unittest.TestCase):
    def test_tc05_no_passages_means_no_answer_and_no_api_call(self):
        with patch("agent.requests.post") as post:
            ans = answer_question("What is the CEO's salary?", RETRIEVER.search("What is the CEO's salary?"),
                                  api_key=FAKE_KEY)
        post.assert_not_called()
        self.assertEqual(ans.mode, "no_evidence")
        self.assertIn(INSUFFICIENT, ans.text)

    def test_tc05_fallback_does_not_answer_from_a_single_generic_word(self):
        q = "Does the company offer dental coverage?"
        with patch.dict(os.environ, {}, clear=True):
            ans = answer_question(q, Retriever(TXT.chunks).search(q) or passages())
        self.assertEqual(ans.text, INSUFFICIENT)

    def test_empty_question(self):
        self.assertEqual(answer_question("   ", passages()).mode, "error")

    def test_model_default_and_override(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(agent.get_model(), agent.DEFAULT_MODEL)
        with patch.dict(os.environ, {"GROQ_MODEL": "my-model"}, clear=True):
            self.assertEqual(agent.get_model(), "my-model")


if __name__ == "__main__":
    unittest.main()
