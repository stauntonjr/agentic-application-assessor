import json
import sys
import tempfile
import unittest
from pathlib import Path

from tools.run_challenges import promote_challenge, replay, validate_challenge


class ChallengeTests(unittest.TestCase):
    def test_non_object_challenge_fails_closed_without_crashing(self) -> None:
        self.assertEqual(
            ["C999.json: challenge must be an object"],
            validate_challenge([], Path("C999.json")),
        )

    def test_current_oracle_passes_and_known_bad_fails_for_signature(self) -> None:
        challenge = {
            "id": "C001",
            "title": "Example",
            "escaped_defect": {"introduced_by": "fixture", "description": "example"},
            "affected_surfaces": ["public-interface"],
            "provenance": {
                "source_issue": "https://github.com/example/project/issues/1",
                "source_artifact": "sanitized report",
                "sanitized": True,
                "contains_raw_transcript": False,
            },
            "promotion": {
                "status": "candidate",
                "reviewed_by": None,
                "reviewed_at": None,
                "decision": None,
            },
            "oracle": {
                "argv": [sys.executable, "-c", "raise SystemExit(0)"],
                "success_exit_code": 0,
            },
            "known_bad": {
                "argv": [
                    sys.executable,
                    "-c",
                    "import sys; print('semantic mismatch'); raise SystemExit(1)",
                ],
                "success_exit_code": 0,
            },
            "expected_failure": {"exit_code": 1, "signature": "semantic mismatch"},
        }
        self.assertEqual([], validate_challenge(challenge, Path("C001.json")))
        result = replay(Path.cwd(), challenge)
        self.assertTrue(result["ok"])

    def test_candidate_cannot_claim_review_and_approval_requires_human(self) -> None:
        challenge = {
            "id": "C001",
            "title": "Example",
            "escaped_defect": {"introduced_by": "fixture", "description": "example"},
            "affected_surfaces": ["loop"],
            "provenance": {
                "source_issue": "https://github.com/example/project/issues/1",
                "source_artifact": "report",
                "sanitized": True,
                "contains_raw_transcript": False,
            },
            "promotion": {
                "status": "approved",
                "reviewed_by": "agent:reviewer",
                "reviewed_at": "2026-08-23T00:00:00Z",
                "decision": "retain",
            },
            "oracle": {"argv": [sys.executable, "-c", "pass"], "success_exit_code": 0},
            "known_bad": {
                "argv": [sys.executable, "-c", "raise SystemExit(1)"],
                "success_exit_code": 0,
            },
            "expected_failure": {"exit_code": 1, "signature": "failure"},
        }
        errors = validate_challenge(challenge, Path("C001.json"))
        self.assertIn("C001.json: approved challenge requires human reviewed_by", errors)

        challenge["promotion"] = {
            "status": "candidate",
            "reviewed_by": "human:owner",
            "reviewed_at": "2026-08-23T00:00:00Z",
            "decision": "retain",
        }
        errors = validate_challenge(challenge, Path("C001.json"))
        self.assertIn("C001.json: candidate challenge cannot claim review provenance", errors)

    def test_promotion_requires_explicit_human_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "harness/challenges/C001.json"
            path.parent.mkdir(parents=True)
            template = json.loads(
                (Path.cwd() / "harness/challenges/C001.json").read_text(encoding="utf-8")
            )
            path.write_text(json.dumps(template), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "human:IDENTITY"):
                promote_challenge(
                    root,
                    "C001",
                    reviewed_by="agent:reviewer",
                    decision="retain",
                )
            promoted = promote_challenge(
                root,
                "C001",
                reviewed_by="human:owner",
                decision="Retain the minimized public fixture",
            )
            data = json.loads(promoted.read_text(encoding="utf-8"))
            self.assertEqual("approved", data["promotion"]["status"])
            self.assertEqual("human:owner", data["promotion"]["reviewed_by"])

    def test_promotion_id_cannot_escape_challenge_directory(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "invalid challenge id"),
        ):
            promote_challenge(
                Path(directory),
                "../../outside",
                reviewed_by="human:owner",
                decision="invalid path probe",
            )


if __name__ == "__main__":
    unittest.main()
