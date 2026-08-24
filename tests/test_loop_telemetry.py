import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.common import load_json, write_json
from tools.harness_check import Result, validate_telemetry
from tools.loop_telemetry import (
    METRICS,
    build_aggregate,
    build_summary,
    main,
    retry_count,
    validate_config,
    validate_input,
    validate_summary,
)


ROOT = Path(__file__).resolve().parents[1]


def loop_record() -> dict:
    return {
        "schema_version": "1.2",
        "run_id": "dogfood-loop",
        "revision": 2,
        "attempt_id": 1,
        "state": "reported",
        "started_at": "2026-08-23T10:00:00Z",
        "finished_at": "2026-08-23T12:00:00Z",
        "acceptance_criteria": [
            {"id": "AC1", "text": "one", "waiver": None},
            {"id": "AC2", "text": "two", "waiver": None},
        ],
        "checks": [
            {
                "revision": 2,
                "attempt_id": 1,
                "status": "passed",
                "criterion_ids": ["AC1"],
            }
        ],
        "attempt_history": [
            {"revision": 1, "attempt_id": 1, "outcome": "failed"},
            {"revision": 1, "attempt_id": 2, "outcome": "failed"},
            {"revision": 1, "attempt_id": 3, "outcome": "failed"},
        ],
    }


def telemetry_input() -> dict:
    return {
        "schema_version": "1.0",
        "run_id": "dogfood-loop",
        "observed_at": "2026-08-24T12:00:00Z",
        "human_corrections": {
            "value": 2,
            "origin": {"kind": "locally-measured", "method": "human-count"},
        },
        "escaped_defects": {
            "value": None,
            "origin": {"kind": "unavailable", "method": "not-collected"},
        },
        "active_intervals": [
            {"started_at": "2026-08-23T10:15:00Z", "ended_at": "2026-08-23T10:45:00Z"},
            {"started_at": "2026-08-23T11:15:00Z", "ended_at": "2026-08-23T11:30:00Z"},
        ],
        "accepted_change_cost": {
            "value": 1.25,
            "unit": "USD",
            "origin": {"kind": "provider-reported", "method": "provider-usage"},
        },
    }


class LoopTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_json(ROOT / "harness/telemetry.json")

    def test_config_is_opt_in_content_free_and_canonical(self) -> None:
        self.assertEqual([], validate_config(self.config))
        self.assertFalse(self.config["enabled_by_default"])
        self.assertFalse(self.config["content_capture"])
        self.assertEqual("stdout", self.config["default_output"])
        self.assertEqual("not-retained", self.config["raw_input_retention"])
        self.assertEqual(list(METRICS), [item["name"] for item in self.config["metrics"]])

        result = Result()
        validate_telemetry(ROOT, result)
        self.assertTrue(result.ok, result.errors)
        self.assertIn("outcome telemetry privacy defaults", result.checked)

    def test_harness_check_rejects_unsafe_telemetry_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unsafe = copy.deepcopy(self.config)
            unsafe["enabled_by_default"] = True
            unsafe["organization_export"] = "enabled"
            unsafe["forbidden_input_keys"].remove("prompt")
            write_json(root / "harness/telemetry.json", unsafe)

            result = Result()
            validate_telemetry(root, result)

            self.assertFalse(result.ok)
            self.assertTrue(any("enabled_by_default" in error for error in result.errors))
            self.assertTrue(any("organization_export" in error for error in result.errors))
            self.assertTrue(any("privacy terms" in error for error in result.errors))

            write_json(root / "harness/telemetry.json", [])
            malformed = Result()
            validate_telemetry(root, malformed)
            self.assertEqual(["telemetry config must be an object"], malformed.errors)

    def test_summary_separates_origins_and_uses_loop_evidence(self) -> None:
        record = loop_record()
        supplied = telemetry_input()

        self.assertEqual([], validate_input(supplied, self.config, record))
        summary = build_summary(record, supplied)
        self.assertEqual([], validate_summary(summary))
        measurements = {item["name"]: item for item in summary["measurements"]}

        self.assertEqual(2, retry_count(record))
        self.assertEqual(2, measurements["retries"]["value"])
        self.assertEqual("locally-measured", measurements["retries"]["origin"]["kind"])
        self.assertEqual(0.5, measurements["acceptance_pass_rate"]["value"])
        self.assertEqual(2700, measurements["cycle_time"]["value"])
        self.assertEqual(7200, measurements["elapsed_time"]["value"])
        self.assertEqual(
            "provider-reported", measurements["accepted_change_cost"]["origin"]["kind"]
        )
        self.assertEqual("unavailable", measurements["escaped_defects"]["completeness"])
        self.assertFalse(summary["privacy"]["content_captured"])
        self.assertFalse(summary["privacy"]["raw_input_retained"])
        self.assertEqual("2026-08-24T12:00:00Z", summary["observation_time"])

    def test_absent_optional_values_are_unavailable_not_inferred(self) -> None:
        record = loop_record()
        supplied = {"schema_version": "1.0", "run_id": "dogfood-loop"}

        summary = build_summary(record, supplied)
        measurements = {item["name"]: item for item in summary["measurements"]}

        for name in ("human_corrections", "escaped_defects", "cycle_time", "accepted_change_cost"):
            self.assertIsNone(measurements[name]["value"])
            self.assertEqual("unavailable", measurements[name]["origin"]["kind"])

    def test_in_progress_acceptance_is_unavailable_instead_of_false_zero(self) -> None:
        record = {**loop_record(), "state": "verify", "finished_at": None}
        with patch("tools.loop_telemetry.utc_now", return_value="2026-08-23T11:00:00Z"):
            summary = build_summary(record, {"schema_version": "1.0", "run_id": "dogfood-loop"})
        acceptance = next(
            item for item in summary["measurements"] if item["name"] == "acceptance_pass_rate"
        )
        self.assertIsNone(acceptance["value"])
        self.assertEqual("unavailable", acceptance["completeness"])
        self.assertEqual("2026-08-23T11:00:00Z", summary["observation_time"])

    def test_input_rejects_content_secret_unknown_and_inconsistent_fields(self) -> None:
        record = loop_record()
        hostile = {
            "schema_version": "1.0",
            "run_id": "dogfood-loop",
            "metadata": {"prompt": "private", "api_key": "secret"},
            "human_corrections": {
                "value": 1,
                "origin": {"kind": "unavailable", "method": "not-collected"},
            },
            "accepted_change_cost": "not-an-object",
        }

        errors = validate_input(hostile, self.config, record)
        self.assertTrue(any("forbidden content-bearing or secret field" in item for item in errors))
        self.assertTrue(any("unexpected fields: metadata" in item for item in errors))
        self.assertTrue(any("value must be null when unavailable" in item for item in errors))
        self.assertTrue(any("accepted_change_cost must be an object" in item for item in errors))

    def test_intervals_reject_overlap_and_escape_from_loop_boundary(self) -> None:
        supplied = {
            "schema_version": "1.0",
            "run_id": "dogfood-loop",
            "active_intervals": [
                {"started_at": "2026-08-23T09:59:00Z", "ended_at": "2026-08-23T10:30:00Z"},
                {"started_at": "2026-08-23T10:15:00Z", "ended_at": "2026-08-23T10:45:00Z"},
            ],
        }

        errors = validate_input(supplied, self.config, loop_record())
        self.assertIn("active_intervals must not overlap", errors)
        self.assertIn("active_intervals must stay inside the loop wall-clock boundary", errors)

    def test_observation_time_cannot_predate_terminal_loop(self) -> None:
        supplied = {
            "schema_version": "1.0",
            "run_id": "dogfood-loop",
            "observed_at": "2026-08-23T11:59:59Z",
        }

        errors = validate_input(supplied, self.config, loop_record())
        self.assertIn("observed_at must not precede the observed loop boundary", errors)

    def test_aggregate_removes_run_identity_and_keeps_units_separate(self) -> None:
        first = build_summary(loop_record(), telemetry_input())
        second_input = telemetry_input()
        second_input["accepted_change_cost"] = {
            "value": 30,
            "unit": "person-minute",
            "origin": {"kind": "inferred", "method": "manual-estimate"},
        }
        second = build_summary(
            {**loop_record(), "run_id": "second-loop"},
            {
                **second_input,
                "run_id": "second-loop",
            },
        )

        aggregate = build_aggregate([first, second])
        serialized = json.dumps(aggregate)
        cost = next(item for item in aggregate["metrics"] if item["name"] == "accepted_change_cost")

        self.assertNotIn("dogfood-loop", serialized)
        self.assertNotIn("second-loop", serialized)
        self.assertFalse(aggregate["privacy"]["run_identifiers_retained"])
        self.assertEqual(["USD", "person-minute"], [item["unit"] for item in cost["units"]])
        self.assertEqual({"inferred": 1, "provider-reported": 1}, cost["origins"])

    def test_summary_validation_fails_closed_before_aggregation(self) -> None:
        summary = build_summary(loop_record(), telemetry_input())
        cases = []

        invalid_identity = copy.deepcopy(summary)
        invalid_identity["run_id"] = "../escape"
        invalid_identity["revision"] = True
        invalid_identity["observation_time"] = "not-a-timestamp"
        cases.append(invalid_identity)

        invalid_value = copy.deepcopy(summary)
        invalid_value["measurements"][0]["value"] = float("nan")
        cases.append(invalid_value)

        invalid_origin = copy.deepcopy(summary)
        invalid_origin["measurements"][1]["origin"] = {
            "kind": "unavailable",
            "method": "loop-record",
        }
        cases.append(invalid_origin)

        invalid_cost = copy.deepcopy(summary)
        invalid_cost["measurements"][-1].update(
            {"value": None, "unit": "USD", "completeness": "unavailable"}
        )
        invalid_cost["measurements"][-1]["origin"] = {
            "kind": "unavailable",
            "method": "not-collected",
        }
        cases.append(invalid_cost)

        invalid_ratio = copy.deepcopy(summary)
        acceptance = invalid_ratio["measurements"][3]
        acceptance.update({"value": None, "completeness": "unavailable"})
        acceptance["origin"] = {"kind": "unavailable", "method": "not-collected"}
        cases.append(invalid_ratio)

        for case in cases:
            with self.subTest(case=case):
                self.assertTrue(validate_summary(case))

    def test_aggregate_cli_rejects_malformed_summary_and_writes_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = build_summary(loop_record(), telemetry_input())
            summary["measurements"][0]["value"] = float("inf")
            source = root / "summary.json"
            output = Path(".harness/telemetry/aggregate.json")
            write_json(source, summary)

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--root",
                        str(root),
                        "aggregate",
                        str(source),
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(1, result)
            self.assertFalse((root / output).exists())
            self.assertIn("finite and non-negative", stderr.getvalue())

    def test_output_rejects_symlink_ancestors_without_writing_outside(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            telemetry = root / ".harness" / "telemetry"
            telemetry.parent.mkdir()
            telemetry.symlink_to(outside, target_is_directory=True)
            source = root / "summary.json"
            write_json(source, build_summary(loop_record(), telemetry_input()))

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--root",
                        str(root),
                        "aggregate",
                        str(source),
                        "--output",
                        ".harness/telemetry/aggregate.json",
                    ]
                )

            self.assertEqual(1, result)
            self.assertFalse((outside / "aggregate.json").exists())

    def test_cli_defaults_to_stdout_and_explicit_writes_stay_local(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "harness/telemetry.json", self.config)
            write_json(root / ".harness/runs/dogfood-loop/run.json", loop_record())
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["--root", str(root), "summarize", "--run", "dogfood-loop"])
            self.assertEqual(0, result)
            self.assertEqual("loop-telemetry-summary", json.loads(stdout.getvalue())["kind"])
            self.assertFalse((root / ".harness/telemetry").exists())

            output = Path(".harness/telemetry/dogfood-loop.json")
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "--root",
                        str(root),
                        "summarize",
                        "--run",
                        "dogfood-loop",
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(0, result)
            self.assertTrue((root / output).is_file())

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--root",
                        str(root),
                        "summarize",
                        "--run",
                        "dogfood-loop",
                        "--output",
                        "outside.json",
                    ]
                )
            self.assertEqual(1, result)
            self.assertIn("must stay under .harness/telemetry", stderr.getvalue())

    def test_cli_rejects_malformed_config_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "harness/telemetry.json", [])
            write_json(root / ".harness/runs/dogfood-loop/run.json", loop_record())

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = main(["--root", str(root), "summarize", "--run", "dogfood-loop"])

            self.assertEqual(1, result)
            self.assertIn("telemetry config must be an object", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
