import copy
import json
import unittest
from unittest.mock import patch

from scholar_compass.config import Settings
from scholar_compass.fixtures import DEMO_INPUT
from scholar_compass.planner import PLAN_SCHEMA, create_plan, openai_plan, rules_plan
from scholar_compass.providers import ProviderError
from scholar_compass.validation import ValidationError, validate_input, validate_plan


class Client:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, payload, headers=None):
        self.calls.append((url, payload, headers))
        return self.response


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.request = validate_input(copy.deepcopy(DEMO_INPUT))

    def test_background_glossary_changes_concepts_without_invented_papers(self):
        request = {**self.request, "keywords": "", "title": "医疗场景的分布式训练", "background": "研究联邦学习和可解释性。"}
        plan = rules_plan(request)
        self.assertIn("联邦学习", [c["name"] for c in plan["concepts"]])
        self.assertIn("federated learning", " ".join(plan["queries"]))
        self.assertEqual(set(PLAN_SCHEMA["required"]), set(plan) - {"planner", "warnings"})

    def test_demo_never_calls_openai_even_with_credentials_and_requested_llm(self):
        request = {**self.request, "planner": "openai"}
        with patch("scholar_compass.planner.openai_plan", side_effect=AssertionError("network")):
            plan = create_plan(request, Settings(openai_api_key="secret", openai_model="test"))
        self.assertEqual(plan["planner"], "demo")

    def test_untranslated_chinese_prompt_requests_english_keywords(self):
        plan = rules_plan({**self.request, "keywords": "", "title": "非常规晶体材料", "background": "分析新型材料的特征"})
        self.assertTrue(any("英文关键词" in w for w in plan["warnings"]))

    def test_openai_structured_plan_preserves_schema_and_does_not_send_secrets_in_payload(self):
        plan = rules_plan(self.request)
        plan = {k: v for k, v in plan.items() if k in PLAN_SCHEMA["required"]}
        client = Client({"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(plan)}]}]})
        result = openai_plan(self.request, Settings(openai_api_key="private", openai_model="selected-model"), client)
        url, payload, headers = client.calls[0]
        self.assertEqual(url, "https://api.openai.com/v1/responses")
        self.assertEqual(payload["text"]["format"]["schema"], PLAN_SCHEMA)
        self.assertIs(payload["store"], False)
        self.assertNotIn("private", json.dumps(payload))
        self.assertEqual(headers["Authorization"], "Bearer private")
        self.assertEqual(result["planner"], "openai")

    def test_refusal_incomplete_and_invalid_output_fail_explicitly(self):
        responses = [
            {"status": "incomplete"},
            {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "private"}]}]},
            {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "{}"}]}]},
        ]
        for response in responses:
            with self.subTest(response=response), self.assertRaises(ProviderError) as ctx:
                openai_plan(self.request, Settings(openai_api_key="private", openai_model="test"), Client(response))
            self.assertNotIn("private", str(ctx.exception))

    def test_live_llm_missing_configuration_fails_before_network(self):
        with self.assertRaises(ValidationError):
            create_plan({**self.request, "mode": "live", "planner": "openai"}, Settings())


class ValidationTests(unittest.TestCase):
    def test_request_bounds(self):
        changes = [
            {"title": ""}, {"background": "x" * 8001}, {"max_results": True}, {"max_results": 21},
            {"year_from": 2025, "year_to": 2020}, {"mode": "pretend-live"},
            {"weights": {"relevance": float("nan"), "citations": 25, "impact_factor": 15}},
            {"weights": {"relevance": 0, "citations": 0, "impact_factor": 100}},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                validate_input({**DEMO_INPUT, **change})

    def test_untrusted_edited_plan_has_bounded_queries_and_concepts(self):
        plan = rules_plan(validate_input(DEMO_INPUT))
        for change in ({"queries": ["x"] * 7}, {"concepts": []}, {"warnings": "bad"}, {"planner": "fake"}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                validate_plan({**plan, **change})


if __name__ == "__main__":
    unittest.main()
