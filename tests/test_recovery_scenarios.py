import json
import subprocess
import sys
import unittest
from pathlib import Path

from tools.recovery_scenarios import (
    fixture_paths,
    replay_fixture,
    replay_known_bad,
    validate_fixture,
)

ROOT = Path(__file__).resolve().parents[1]


class RecoveryScenarioTests(unittest.TestCase):
    def test_all_sanitized_recovery_fixtures_replay(self) -> None:
        paths = fixture_paths(ROOT)
        self.assertEqual([f"R{index:03d}.json" for index in range(1, 7)], [p.name for p in paths])
        for path in paths:
            with self.subTest(path=path.name):
                fixture = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual([], validate_fixture(fixture, path))
                self.assertTrue(replay_fixture(ROOT, fixture)["ok"])

    def test_fixture_rejects_unsanitized_or_raw_transcript_source(self) -> None:
        fixture = {
            "schema_version": "1.0",
            "id": "R999",
            "failure_class": "agent-crash",
            "source": {
                "kind": "public-dogfood",
                "reference": "report",
                "sanitized": False,
                "contains_raw_transcript": True,
            },
            "expected": {"terminal_state": "implement"},
        }
        errors = validate_fixture(fixture, Path("R999.json"))
        self.assertIn("R999.json: source.sanitized must be true", errors)
        self.assertIn("R999.json: source.contains_raw_transcript must be false", errors)

    def test_known_bad_replayers_preserve_minimized_failure_signatures(self) -> None:
        for case, signature in (
            ("pi-unbounded-unavailable-tools", "unbounded unavailable-tool retries"),
            ("adoption-partial-mutation", "partial mutation before preflight"),
        ):
            with self.subTest(case=case):
                code, payload = replay_known_bad(case)
                self.assertEqual(1, code)
                self.assertEqual(signature, payload["signature"])

    def test_cli_replays_complete_matrix(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/recovery_scenarios.py"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn('"ok": true', result.stdout)


if __name__ == "__main__":
    unittest.main()
