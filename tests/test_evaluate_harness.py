from pathlib import Path
import unittest

from tools.common import load_json
from tools.evaluate_harness import forward_prompts, validate_scenarios


ROOT = Path(__file__).resolve().parents[1]


class EvaluateHarnessTests(unittest.TestCase):
    def test_scenarios_route_to_existing_skills(self) -> None:
        payload = load_json(ROOT / "harness/evals/scenarios.json")
        self.assertEqual([], validate_scenarios(ROOT, payload))
        prompts = forward_prompts(ROOT, payload)
        self.assertEqual(len(payload["scenarios"]), len(prompts))
        context_gap = next(prompt for prompt in prompts if prompt["id"] == "E008-context-gap")
        self.assertIsNone(context_gap["skill_path"])

    def test_layered_domain_routing_keeps_target_rules_local(self) -> None:
        payload = load_json(ROOT / "harness/evals/scenarios.json")
        scenario = next(
            item for item in payload["scenarios"] if item["id"] == "E009-layered-domain-routing"
        )

        self.assertEqual("execute-engineering-loop", scenario["expected_primary_skill"])
        self.assertIn(
            "read the target repository AGENTS.md before planning commands",
            scenario["required_behaviors"],
        )
        self.assertIn(
            "promote S3NTINEL Spark rules into universal policy",
            scenario["forbidden_behaviors"],
        )
        self.assertNotIn("sentinel-spark35", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))

    def test_s3ntinel_fixture_separates_projects_roles_and_local_policy(self) -> None:
        fixture = load_json(ROOT / "harness/fixtures/s3ntinel-routing-evaluation.json")
        issue_sets = [set(project["issues"]) for project in fixture["github_projects"]]

        for index, issues in enumerate(issue_sets):
            for other in issue_sets[index + 1 :]:
                self.assertTrue(issues.isdisjoint(other))
        self.assertEqual("PASS", fixture["routing_probe"]["result"])
        self.assertEqual(3, fixture["routing_probe"]["read_calls"])
        self.assertEqual(231, fixture["pi_failure_probe"]["unavailable_tool_attempts"])
        self.assertEqual(0, fixture["pi_failure_probe"]["executed_unavailable_tools"])
        self.assertEqual(
            "APPROVE_CONTENT_ONLY",
            fixture["role_exercises"]["verifier"]["result"],
        )
        self.assertEqual("NOT_READY", fixture["role_exercises"]["release_steward"]["result"])
        self.assertTrue(all(item["scope"] == "repository-local" for item in fixture["local_rules"]))

    def test_governed_learning_scenario_preserves_authority_and_review_boundaries(self) -> None:
        payload = load_json(ROOT / "harness/evals/scenarios.json")
        scenario = next(
            item
            for item in payload["scenarios"]
            if item["id"] == "E010-governed-learning-provenance"
        )

        self.assertEqual("execute-engineering-loop", scenario["expected_primary_skill"])
        self.assertIn(
            "separate published, local committed, and uncommitted evidence tiers",
            scenario["required_behaviors"],
        )
        self.assertIn(
            "treat derived directive memory as approved policy",
            scenario["forbidden_behaviors"],
        )

    def test_kortex_fixture_keeps_learning_proposed_and_handoff_sanitized(self) -> None:
        fixture = load_json(
            ROOT / "harness/fixtures/kortex-governed-learning-evaluation.json"
        )
        domains = {item["domain"] for item in fixture["authority_trace"]}
        proposal = fixture["learn_phase"]["proposal"]
        handoff = fixture["durable_handoff"]
        boundary = fixture["boundary_evidence"]

        self.assertEqual({"code", "memory", "preferences", "architecture"}, domains)
        self.assertEqual("proposed", proposal["status"])
        self.assertTrue(proposal["human_review_required"])
        self.assertIsNone(proposal["authorized_by"])
        self.assertFalse(proposal["applied"])
        self.assertFalse(proposal["template_policy_changed"])
        self.assertTrue(handoff["sanitized"])
        self.assertFalse(handoff["contains_raw_transcript"])
        self.assertFalse(handoff["contains_hidden_reasoning"])
        self.assertNotIn("transcript", handoff)
        self.assertNotIn("prompt", handoff)
        self.assertNotIn("reasoning", handoff)
        self.assertEqual("PASS", fixture["result"])
        self.assertTrue(all(value == 0 for value in boundary.values()))
        self.assertTrue(
            all(item["scope"] == "kortex-local" for item in fixture["kortex_local_exceptions"])
        )
        self.assertEqual(
            ["R004", "R006"],
            [item["fixture"] for item in fixture["recovery_exercises"]],
        )
        self.assertTrue(
            all(item["result"] == "PASS" for item in fixture["recovery_exercises"])
        )
