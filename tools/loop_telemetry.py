#!/usr/bin/env python3
"""Build opt-in, content-free loop telemetry summaries and de-identified aggregates."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root, utc_now, write_json
    from .loop import active_criterion_ids, current_passed_criteria, load_run
except ImportError:  # Direct script execution.
    from common import load_json, repository_root, utc_now, write_json
    from loop import active_criterion_ids, current_passed_criteria, load_run


SCHEMA_VERSION = "1.0"
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
METRICS = (
    "human_corrections",
    "retries",
    "escaped_defects",
    "acceptance_pass_rate",
    "cycle_time",
    "elapsed_time",
    "accepted_change_cost",
)
ORIGINS = {"locally-measured", "provider-reported", "inferred", "unavailable"}
METHODS = {
    "human-count",
    "receipt-total",
    "provider-usage",
    "manual-estimate",
    "not-collected",
}
SUMMARY_METHODS = METHODS | {"loop-record", "active-intervals"}
COUNT_FIELDS = {"human_corrections", "escaped_defects"}
INPUT_KEYS = {
    "schema_version",
    "run_id",
    "observed_at",
    "human_corrections",
    "escaped_defects",
    "active_intervals",
    "accepted_change_cost",
}
COST_UNITS = {"USD", "person-minute", "compute-second", "unavailable"}


def validate_config(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return ["telemetry config must be an object"]
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"telemetry config schema_version must be {SCHEMA_VERSION}")
    expected = {
        "enabled_by_default": False,
        "ingestion": "explicit-cli-only",
        "default_output": "stdout",
        "raw_input_retention": "not-retained",
        "written_summary_retention": "caller-managed",
        "organization_export": "disabled",
        "content_capture": False,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            errors.append(f"telemetry config {key} must be {value!r}")
    if data.get("measurement_origins") != [
        "locally-measured",
        "provider-reported",
        "inferred",
        "unavailable",
    ]:
        errors.append("telemetry config measurement_origins are invalid")
    metrics = data.get("metrics")
    expected_metrics = [
        {"name": "human_corrections", "unit": "{correction}"},
        {"name": "retries", "unit": "{attempt}"},
        {"name": "escaped_defects", "unit": "{defect}"},
        {"name": "acceptance_pass_rate", "unit": "1"},
        {"name": "cycle_time", "unit": "s"},
        {"name": "elapsed_time", "unit": "s"},
        {"name": "accepted_change_cost", "unit": "input-defined"},
    ]
    if metrics != expected_metrics:
        errors.append("telemetry config metrics must contain the canonical seven metrics")
    try:
        forbidden = forbidden_keys(data)
    except ValueError as exc:
        errors.append(str(exc))
    else:
        required_forbidden = {"prompt", "transcript", "reasoning", "secret", "token"}
        if not required_forbidden.issubset(forbidden):
            errors.append("telemetry config forbidden_input_keys omit required privacy terms")
    return errors


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def forbidden_keys(config: dict[str, Any]) -> set[str]:
    values = config.get("forbidden_input_keys")
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise ValueError("telemetry forbidden_input_keys must be a string list")
    return {item.lower() for item in values}


def scan_forbidden_keys(value: Any, forbidden: set[str], path: str = "input") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(term in normalized for term in forbidden):
                errors.append(f"{path}.{key}: forbidden content-bearing or secret field")
            errors.extend(scan_forbidden_keys(child, forbidden, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(scan_forbidden_keys(child, forbidden, f"{path}[{index}]"))
    return errors


def validate_origin(value: Any, field: str, *, cost: bool = False) -> list[str]:
    if not isinstance(value, dict):
        return [f"{field}.origin must be an object"]
    errors: list[str] = []
    unexpected = sorted(set(value) - {"kind", "method"})
    if unexpected:
        errors.append(f"{field}.origin has unexpected fields: {', '.join(unexpected)}")
    kind = value.get("kind")
    method = value.get("method")
    if kind not in ORIGINS:
        errors.append(f"{field}.origin.kind is invalid")
    if method not in METHODS:
        errors.append(f"{field}.origin.method is invalid")
    expected_methods = {
        "locally-measured": {"receipt-total"} if cost else {"human-count"},
        "provider-reported": {"provider-usage"},
        "inferred": {"manual-estimate"},
        "unavailable": {"not-collected"},
    }
    if kind in expected_methods and method not in expected_methods[kind]:
        errors.append(f"{field}.origin method does not match {kind}")
    return errors


def validate_optional_measurement(value: Any, field: str, *, cost: bool = False) -> list[str]:
    if not isinstance(value, dict):
        return [f"{field} must be an object"]
    allowed = {"value", "origin", "unit"} if cost else {"value", "origin"}
    errors: list[str] = []
    unexpected = sorted(set(value) - allowed)
    missing = sorted(allowed - set(value))
    if unexpected:
        errors.append(f"{field} has unexpected fields: {', '.join(unexpected)}")
    if missing:
        errors.append(f"{field} is missing fields: {', '.join(missing)}")
    errors.extend(validate_origin(value.get("origin"), field, cost=cost))
    origin = value.get("origin") if isinstance(value.get("origin"), dict) else {}
    amount = value.get("value")
    unavailable = origin.get("kind") == "unavailable"
    if unavailable and amount is not None:
        errors.append(f"{field}.value must be null when unavailable")
    if not unavailable:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            errors.append(f"{field}.value must be numeric when available")
        elif not math.isfinite(amount) or amount < 0:
            errors.append(f"{field}.value must be finite and non-negative")
        elif not cost and not isinstance(amount, int):
            errors.append(f"{field}.value must be an integer count")
    if cost:
        unit = value.get("unit")
        if unit not in COST_UNITS:
            errors.append(f"{field}.unit is invalid")
        if unavailable and unit != "unavailable":
            errors.append(f"{field}.unit must be unavailable when value is unavailable")
        if not unavailable and unit == "unavailable":
            errors.append(f"{field}.unit cannot be unavailable when value is available")
    return errors


def validate_input(data: Any, config: dict[str, Any], record: dict[str, Any]) -> list[str]:
    if not isinstance(data, dict):
        return ["telemetry input must be an object"]
    if not isinstance(record, dict):
        return ["loop record must be an object"]
    errors = scan_forbidden_keys(data, forbidden_keys(config))
    unexpected = sorted(set(data) - INPUT_KEYS)
    if unexpected:
        errors.append(f"telemetry input has unexpected fields: {', '.join(unexpected)}")
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"telemetry input schema_version must be {SCHEMA_VERSION}")
    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        errors.append("telemetry input run_id is invalid")
    elif run_id != record.get("run_id"):
        errors.append("telemetry input run_id does not match the loop record")
    if "observed_at" in data:
        try:
            observed_at = parse_timestamp(data["observed_at"], "observed_at")
            loop_start = parse_timestamp(record.get("started_at"), "loop.started_at")
            loop_finish = (
                parse_timestamp(record.get("finished_at"), "loop.finished_at")
                if record.get("finished_at")
                else None
            )
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if observed_at < loop_start or (loop_finish and observed_at < loop_finish):
                errors.append("observed_at must not precede the observed loop boundary")
    for field in sorted(COUNT_FIELDS.intersection(data)):
        errors.extend(validate_optional_measurement(data[field], field))
    if "accepted_change_cost" in data:
        errors.extend(
            validate_optional_measurement(
                data["accepted_change_cost"], "accepted_change_cost", cost=True
            )
        )
        cost_value = data["accepted_change_cost"]
        origin = cost_value.get("origin") if isinstance(cost_value, dict) else None
        if (
            isinstance(origin, dict)
            and origin.get("kind") != "unavailable"
            and record.get("state") != "reported"
        ):
            errors.append("accepted_change_cost is available only for a reported loop")
    intervals = data.get("active_intervals", [])
    if not isinstance(intervals, list):
        errors.append("active_intervals must be a list")
    else:
        parsed: list[tuple[datetime, datetime]] = []
        for index, interval in enumerate(intervals):
            field = f"active_intervals[{index}]"
            if not isinstance(interval, dict):
                errors.append(f"{field} must be an object")
                continue
            unexpected_interval = sorted(set(interval) - {"started_at", "ended_at"})
            if unexpected_interval:
                errors.append(f"{field} has unexpected fields: {', '.join(unexpected_interval)}")
            try:
                start = parse_timestamp(interval.get("started_at"), f"{field}.started_at")
                end = parse_timestamp(interval.get("ended_at"), f"{field}.ended_at")
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if end < start:
                errors.append(f"{field} ends before it starts")
            else:
                parsed.append((start, end))
        parsed.sort()
        for previous, current in zip(parsed, parsed[1:]):
            if current[0] < previous[1]:
                errors.append("active_intervals must not overlap")
                break
        try:
            loop_start = parse_timestamp(record.get("started_at"), "loop.started_at")
            loop_end = (
                parse_timestamp(record.get("finished_at"), "loop.finished_at")
                if record.get("finished_at")
                else None
            )
        except ValueError as exc:
            errors.append(str(exc))
        else:
            for start, end in parsed:
                if start < loop_start or (loop_end is not None and end > loop_end):
                    errors.append("active_intervals must stay inside the loop wall-clock boundary")
                    break
    return errors


def unavailable_measurement(name: str, unit: str) -> dict[str, Any]:
    return {
        "name": name,
        "value": None,
        "unit": unit,
        "origin": {"kind": "unavailable", "method": "not-collected"},
        "completeness": "unavailable",
    }


def provided_measurement(name: str, unit: str, value: dict[str, Any]) -> dict[str, Any]:
    if value["origin"]["kind"] == "unavailable":
        unavailable_unit = "unavailable" if name == "accepted_change_cost" else unit
        return unavailable_measurement(name, unavailable_unit)
    return {
        "name": name,
        "value": value["value"],
        "unit": value.get("unit", unit),
        "origin": value["origin"],
        "completeness": "available",
    }


def retry_count(record: dict[str, Any]) -> int:
    attempts: dict[int, int] = defaultdict(lambda: 1)
    for item in record.get("attempt_history", []):
        revision = item.get("revision")
        attempt = item.get("attempt_id")
        if isinstance(revision, int) and isinstance(attempt, int):
            attempts[revision] = max(attempts[revision], attempt)
    revision = record.get("revision")
    attempt = record.get("attempt_id")
    if isinstance(revision, int) and isinstance(attempt, int):
        attempts[revision] = max(attempts[revision], attempt)
    return sum(maximum - 1 for maximum in attempts.values())


def build_summary(record: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    corrections = (
        provided_measurement("human_corrections", "{correction}", data["human_corrections"])
        if "human_corrections" in data
        else unavailable_measurement("human_corrections", "{correction}")
    )
    defects = (
        provided_measurement("escaped_defects", "{defect}", data["escaped_defects"])
        if "escaped_defects" in data
        else unavailable_measurement("escaped_defects", "{defect}")
    )
    retries = {
        "name": "retries",
        "value": retry_count(record),
        "unit": "{attempt}",
        "origin": {"kind": "locally-measured", "method": "loop-record"},
        "completeness": "available",
    }
    active = active_criterion_ids(record)
    passed = current_passed_criteria(record).intersection(active)
    acceptance = unavailable_measurement("acceptance_pass_rate", "1")
    if active and record.get("state") in {"reported", "blocked", "abandoned"}:
        acceptance = {
            "name": "acceptance_pass_rate",
            "value": len(passed) / len(active),
            "unit": "1",
            "origin": {"kind": "locally-measured", "method": "loop-record"},
            "completeness": "available",
            "numerator": len(passed),
            "denominator": len(active),
        }
    intervals = data.get("active_intervals", [])
    cycle = unavailable_measurement("cycle_time", "s")
    if intervals:
        duration = sum(
            (
                parse_timestamp(item["ended_at"], "active interval end")
                - parse_timestamp(item["started_at"], "active interval start")
            ).total_seconds()
            for item in intervals
        )
        cycle = {
            "name": "cycle_time",
            "value": duration,
            "unit": "s",
            "origin": {"kind": "locally-measured", "method": "active-intervals"},
            "completeness": "available",
        }
    elapsed = unavailable_measurement("elapsed_time", "s")
    if record.get("finished_at"):
        duration = (
            parse_timestamp(record["finished_at"], "loop.finished_at")
            - parse_timestamp(record["started_at"], "loop.started_at")
        ).total_seconds()
        elapsed = {
            "name": "elapsed_time",
            "value": duration,
            "unit": "s",
            "origin": {"kind": "locally-measured", "method": "loop-record"},
            "completeness": "available",
        }
    cost = (
        provided_measurement("accepted_change_cost", "unavailable", data["accepted_change_cost"])
        if "accepted_change_cost" in data
        else unavailable_measurement("accepted_change_cost", "unavailable")
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "loop-telemetry-summary",
        "run_id": record["run_id"],
        "revision": record["revision"],
        "attempt_id": record["attempt_id"],
        "state": record["state"],
        "observation_time": data.get("observed_at") or record.get("finished_at") or utc_now(),
        "privacy": {
            "content_captured": False,
            "raw_input_retained": False,
            "default_storage": "stdout",
            "written_summary_retention": "caller-managed",
            "organization_exported": False,
        },
        "measurements": [
            corrections,
            retries,
            defects,
            acceptance,
            cycle,
            elapsed,
            cost,
        ],
    }


def validate_summary(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return ["loop telemetry summary must be an object"]
    errors: list[str] = []
    required = {
        "schema_version",
        "kind",
        "run_id",
        "revision",
        "attempt_id",
        "state",
        "observation_time",
        "privacy",
        "measurements",
    }
    unexpected = sorted(set(data) - required)
    missing = sorted(required - set(data))
    if unexpected:
        errors.append(f"summary has unexpected fields: {', '.join(unexpected)}")
    if missing:
        errors.append(f"summary is missing fields: {', '.join(missing)}")
    if data.get("schema_version") != SCHEMA_VERSION or data.get("kind") != "loop-telemetry-summary":
        errors.append("summary identity is invalid")
    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        errors.append("summary run_id is invalid")
    for field in ("revision", "attempt_id"):
        value = data.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            errors.append(f"summary {field} must be a positive integer")
    state = data.get("state")
    if not isinstance(state, str) or not state.strip():
        errors.append("summary state must be a non-empty string")
    try:
        parse_timestamp(data.get("observation_time"), "summary observation_time")
    except ValueError as exc:
        errors.append(str(exc))
    privacy = data.get("privacy")
    expected_privacy = {
        "content_captured": False,
        "raw_input_retained": False,
        "default_storage": "stdout",
        "written_summary_retention": "caller-managed",
        "organization_exported": False,
    }
    if privacy != expected_privacy:
        errors.append("summary privacy boundary is invalid")
    measurements = data.get("measurements")
    if not isinstance(measurements, list):
        errors.append("summary measurements must be a list")
        return errors
    names = [item.get("name") for item in measurements if isinstance(item, dict)]
    if names != list(METRICS):
        errors.append("summary measurements must contain the seven metrics in canonical order")
    expected_units = {
        "human_corrections": {"{correction}"},
        "retries": {"{attempt}"},
        "escaped_defects": {"{defect}"},
        "acceptance_pass_rate": {"1"},
        "cycle_time": {"s"},
        "elapsed_time": {"s"},
        "accepted_change_cost": COST_UNITS,
    }
    expected_methods = {
        "human_corrections": {
            "human-count",
            "provider-usage",
            "manual-estimate",
            "not-collected",
        },
        "retries": {"loop-record", "not-collected"},
        "escaped_defects": {
            "human-count",
            "provider-usage",
            "manual-estimate",
            "not-collected",
        },
        "acceptance_pass_rate": {"loop-record", "not-collected"},
        "cycle_time": {"active-intervals", "not-collected"},
        "elapsed_time": {"loop-record", "not-collected"},
        "accepted_change_cost": {
            "receipt-total",
            "provider-usage",
            "manual-estimate",
            "not-collected",
        },
    }
    for index, item in enumerate(measurements):
        field = f"measurements[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{field} must be an object")
            continue
        allowed = {"name", "value", "unit", "origin", "completeness"}
        if item.get("name") == "acceptance_pass_rate":
            allowed.update({"numerator", "denominator"})
        extra = sorted(set(item) - allowed)
        if extra:
            errors.append(f"{field} has unexpected fields: {', '.join(extra)}")
        origin = item.get("origin")
        if not isinstance(origin, dict) or set(origin) != {"kind", "method"}:
            errors.append(f"{field}.origin is invalid")
            continue
        if origin.get("kind") not in ORIGINS:
            errors.append(f"{field}.origin.kind is invalid")
        if origin.get("method") not in SUMMARY_METHODS:
            errors.append(f"{field}.origin.method is invalid")
        expected_kind = {
            "human-count": "locally-measured",
            "receipt-total": "locally-measured",
            "provider-usage": "provider-reported",
            "manual-estimate": "inferred",
            "not-collected": "unavailable",
            "loop-record": "locally-measured",
            "active-intervals": "locally-measured",
        }.get(origin.get("method"))
        if expected_kind is not None and origin.get("kind") != expected_kind:
            errors.append(f"{field}.origin method and kind disagree")
        name = item.get("name")
        if name in expected_units and item.get("unit") not in expected_units[name]:
            errors.append(f"{field}.unit is invalid for {name}")
        if name in expected_methods and origin.get("method") not in expected_methods[name]:
            errors.append(f"{field}.origin.method is invalid for {name}")
        value = item.get("value")
        completeness = item.get("completeness")
        if completeness == "unavailable":
            if value is not None or origin.get("kind") != "unavailable":
                errors.append(f"{field} unavailable value and origin disagree")
            if name == "acceptance_pass_rate" and ("numerator" in item or "denominator" in item):
                errors.append(f"{field} unavailable ratio must omit numerator and denominator")
            if name == "accepted_change_cost" and item.get("unit") != "unavailable":
                errors.append(f"{field} unavailable cost must use the unavailable unit")
        elif completeness == "available":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"{field} available value must be numeric")
            elif not math.isfinite(value) or value < 0:
                errors.append(f"{field} available value must be finite and non-negative")
            if origin.get("kind") == "unavailable":
                errors.append(f"{field} available value cannot have unavailable origin")
            if name == "accepted_change_cost" and item.get("unit") == "unavailable":
                errors.append(f"{field} available cost cannot use the unavailable unit")
            if name in {"human_corrections", "retries", "escaped_defects"} and not isinstance(
                value, int
            ):
                errors.append(f"{field} count must be an integer")
            if name == "acceptance_pass_rate":
                numerator = item.get("numerator")
                denominator = item.get("denominator")
                if (
                    isinstance(numerator, bool)
                    or not isinstance(numerator, int)
                    or isinstance(denominator, bool)
                    or not isinstance(denominator, int)
                    or denominator < 1
                    or numerator < 0
                    or numerator > denominator
                    or value != numerator / denominator
                ):
                    errors.append(f"{field} acceptance ratio is inconsistent")
        else:
            errors.append(f"{field}.completeness is invalid")
    return errors


def build_aggregate(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: list[dict[str, Any]] = []
    for name in METRICS:
        values: dict[str, list[float]] = defaultdict(list)
        origins: dict[str, int] = defaultdict(int)
        unavailable = 0
        for summary in summaries:
            item = next(
                measurement
                for measurement in summary["measurements"]
                if measurement["name"] == name
            )
            origins[item["origin"]["kind"]] += 1
            if item["completeness"] == "unavailable":
                unavailable += 1
            else:
                values[item["unit"]].append(float(item["value"]))
        units = [
            {
                "unit": unit,
                "count": len(points),
                "sum": sum(points),
                "minimum": min(points),
                "maximum": max(points),
            }
            for unit, points in sorted(values.items())
        ]
        metrics.append(
            {
                "name": name,
                "available_count": sum(len(points) for points in values.values()),
                "unavailable_count": unavailable,
                "origins": dict(sorted(origins.items())),
                "units": units,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "loop-telemetry-aggregate",
        "summary_count": len(summaries),
        "privacy": {
            "content_captured": False,
            "run_identifiers_retained": False,
            "source_inputs_retained": False,
        },
        "metrics": metrics,
    }


def output_path(root: Path, requested: Path) -> Path:
    root = root.absolute()
    allowed = (root / ".harness" / "telemetry").absolute()
    candidate = requested if requested.is_absolute() else root / requested
    candidate = candidate.absolute()
    try:
        candidate.relative_to(allowed)
    except ValueError as exc:
        raise ValueError("telemetry output must stay under .harness/telemetry") from exc
    current = root
    for part in candidate.relative_to(root).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"telemetry output ancestor must not be a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"telemetry output ancestor must be a directory: {current}")
    if candidate.is_symlink():
        raise ValueError("telemetry output must not be a symlink")
    return candidate


def emit(root: Path, payload: dict[str, Any], requested: Path | None) -> None:
    if requested is None:
        print(json.dumps(payload, indent=2))
        return
    destination = output_path(root, requested)
    write_json(destination, payload)
    print(destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    subparsers = parser.add_subparsers(dest="action", required=True)
    summarize = subparsers.add_parser("summarize")
    summarize.add_argument("--run", required=True)
    summarize.add_argument("--input", type=Path)
    summarize.add_argument("--output", type=Path)
    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("summary", nargs="+", type=Path)
    aggregate.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = args.root.absolute() if args.root else repository_root(Path(__file__).parent)
    try:
        if args.action == "summarize":
            _, record = load_run(root, args.run)
            data = (
                load_json(args.input)
                if args.input
                else {
                    "schema_version": SCHEMA_VERSION,
                    "run_id": args.run,
                }
            )
            config = load_json(root / "harness/telemetry.json")
            errors = validate_config(config)
            if not errors:
                errors.extend(validate_input(data, config, record))
            if errors:
                raise ValueError("; ".join(errors))
            summary_payload = build_summary(record, data)
            summary_errors = validate_summary(summary_payload)
            if summary_errors:
                raise ValueError("generated summary is invalid: " + "; ".join(summary_errors))
            emit(root, summary_payload, args.output)
        else:
            summaries = [load_json(path) for path in args.summary]
            errors = [
                f"{path}: {error}"
                for path, summary in zip(args.summary, summaries)
                for error in validate_summary(summary)
            ]
            if errors:
                raise ValueError("; ".join(errors))
            emit(root, build_aggregate(summaries), args.output)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        print(f"loop telemetry: failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
