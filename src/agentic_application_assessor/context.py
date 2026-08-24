"""Strict, bounded application-context loading."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from datetime import date
from pathlib import Path
from typing import Any

from .errors import AssessmentError


MAX_CONTEXT_BYTES = 256 * 1024
ROOT_KEYS = {
    "schema_version",
    "review",
    "application",
    "components",
    "workflows",
    "data_assets",
    "quality_scenarios",
}
RECORD_ID = re.compile(r"^[a-z][a-z0-9-]*$")


def _object(value: Any, label: str, allowed: set[str], required: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssessmentError(f"{label} must be an object")
    extra = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if extra:
        raise AssessmentError(f"{label} has unsupported properties: {', '.join(extra)}")
    if missing:
        raise AssessmentError(f"{label} is missing required properties: {', '.join(missing)}")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssessmentError(f"{label} must be a non-empty string")
    if len(value) > 4096:
        raise AssessmentError(f"{label} is too long")
    return value.strip()


def _text_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise AssessmentError(f"{label} must be a non-empty array")
    result = [_text(item, f"{label} item") for item in value]
    if len(result) != len(set(result)):
        raise AssessmentError(f"{label} must contain unique values")
    return result


def _records(value: Any, label: str, allowed: set[str], required: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 256:
        raise AssessmentError(f"{label} must be an array with at most 256 items")
    records = [
        _object(item, f"{label}[{index}]", allowed, required) for index, item in enumerate(value)
    ]
    ids = [_text(item["id"], f"{label}.id") for item in records]
    if any(item["id"] != normalized for item, normalized in zip(records, ids, strict=True)):
        raise AssessmentError(f"{label} identifiers must not contain surrounding whitespace")
    invalid = [item for item in ids if RECORD_ID.fullmatch(item) is None]
    if invalid:
        raise AssessmentError(f"{label} identifiers must use lowercase kebab-case")
    if len(ids) != len(set(ids)):
        raise AssessmentError(f"{label} identifiers must be unique")
    return records


def validate_context(payload: Any) -> dict[str, Any]:
    root = _object(payload, "context", ROOT_KEYS, {"schema_version", "review", "application"})
    if root["schema_version"] != "1.0":
        raise AssessmentError("context.schema_version must be 1.0")
    review = _object(
        root["review"],
        "review",
        {"status", "confirmed_on", "source"},
        {"status", "confirmed_on", "source"},
    )
    if review["status"] != "accepted":
        raise AssessmentError("review.status must be accepted")
    confirmed_on = _text(review["confirmed_on"], "review.confirmed_on")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", confirmed_on) is None:
        raise AssessmentError("review.confirmed_on must be an RFC 3339 full-date")
    try:
        date.fromisoformat(confirmed_on)
    except ValueError as exc:
        raise AssessmentError("review.confirmed_on must be an RFC 3339 full-date") from exc
    _text(review["source"], "review.source")
    application = _object(
        root["application"],
        "application",
        {"name", "purpose", "stakeholders"},
        {"name", "purpose", "stakeholders"},
    )
    _text(application["name"], "application.name")
    _text(application["purpose"], "application.purpose")
    _text_list(application["stakeholders"], "application.stakeholders")
    for record in _records(
        root.get("components", []),
        "components",
        {"id", "name", "responsibility", "paths"},
        {"id", "name", "responsibility", "paths"},
    ):
        _text(record["name"], "components.name")
        _text(record["responsibility"], "components.responsibility")
        _text_list(record["paths"], "components.paths")
    for record in _records(
        root.get("workflows", []),
        "workflows",
        {"id", "name", "description"},
        {"id", "name", "description"},
    ):
        _text(record["name"], "workflows.name")
        _text(record["description"], "workflows.description")
    for record in _records(
        root.get("data_assets", []),
        "data_assets",
        {"id", "name", "classification", "description"},
        {"id", "name", "classification", "description"},
    ):
        _text(record["name"], "data_assets.name")
        _text(record["classification"], "data_assets.classification")
        _text(record["description"], "data_assets.description")
    for record in _records(
        root.get("quality_scenarios", []),
        "quality_scenarios",
        {"id", "attribute", "stimulus", "response"},
        {"id", "attribute", "stimulus", "response"},
    ):
        _text(record["attribute"], "quality_scenarios.attribute")
        _text(record["stimulus"], "quality_scenarios.stimulus")
        _text(record["response"], "quality_scenarios.response")
    return root


def load_context(path: Path) -> tuple[dict[str, Any], str]:
    lexical = path.absolute()
    for candidate in (lexical, *lexical.parents):
        try:
            if stat.S_ISLNK(candidate.lstat().st_mode):
                raise AssessmentError(f"context path traverses a symlink: {candidate}")
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise AssessmentError(f"cannot inspect context path: {exc}") from exc
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise AssessmentError(f"cannot inspect context file: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise AssessmentError("context must be a regular file, not a symlink")
    if metadata.st_size > MAX_CONTEXT_BYTES:
        raise AssessmentError("context file exceeds 256 KiB")
    try:
        raw = path.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssessmentError(f"cannot read context JSON: {exc}") from exc
    return validate_context(payload), hashlib.sha256(raw).hexdigest()
