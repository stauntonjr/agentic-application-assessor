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
    "requirements",
    "application_provenance",
    "contradictions",
    "unknowns",
    "questionnaire_input",
    "answers_input",
}
LEGACY_ROOT_KEYS = ROOT_KEYS - {
    "requirements",
    "application_provenance",
    "contradictions",
    "unknowns",
    "questionnaire_input",
    "answers_input",
}
RECORD_ID = re.compile(r"^[a-z][a-z0-9-]*$")
ISSUE_ID = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z0-9-]+)+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
STATE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")


class _DuplicateKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(f"duplicate object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON number: {value}")


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


def _full_date(value: Any, label: str) -> str:
    result = _text(value, label)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", result) is None:
        raise AssessmentError(f"{label} must be an RFC 3339 full-date")
    try:
        date.fromisoformat(result)
    except ValueError as exc:
        raise AssessmentError(f"{label} must be an RFC 3339 full-date") from exc
    return result


def _optional_text_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or len(value) > 64:
        raise AssessmentError(f"{label} must be an array with at most 64 items")
    result = [_text(item, f"{label} item") for item in value]
    if len(result) != len(set(result)):
        raise AssessmentError(f"{label} must contain unique values")
    return result


def _bounded_text_list(value: Any, label: str) -> list[str]:
    result = _text_list(value, label)
    if len(result) > 64:
        raise AssessmentError(f"{label} must contain at most 64 items")
    return result


def _sha256(value: Any, label: str) -> str:
    result = _text(value, label)
    if SHA256.fullmatch(result) is None:
        raise AssessmentError(f"{label} must be 64 lowercase hexadecimal characters")
    return result


def _target_descriptor(value: Any, label: str) -> None:
    target = _object(
        value,
        label,
        {"name", "revision", "branch", "dirty", "state_id"},
        {"name", "revision", "branch", "dirty", "state_id"},
    )
    _text(target["name"], f"{label}.name")
    revision = _text(target["revision"], f"{label}.revision")
    if REVISION.fullmatch(revision) is None:
        raise AssessmentError(f"{label}.revision is not a canonical Git object ID")
    _text(target["branch"], f"{label}.branch")
    if type(target["dirty"]) is not bool:
        raise AssessmentError(f"{label}.dirty must be boolean")
    state_id = _text(target["state_id"], f"{label}.state_id")
    if STATE_ID.fullmatch(state_id) is None:
        raise AssessmentError(f"{label}.state_id must be sha256:<64 lowercase hex>")


def _repository_evidence(value: Any, label: str) -> None:
    if not isinstance(value, list) or not value or len(value) > 64:
        raise AssessmentError(f"{label} must contain between 1 and 64 records")
    for index, item in enumerate(value):
        record = _object(
            item,
            f"{label}[{index}]",
            {"id", "kind", "source", "value", "sha256"},
            {"id", "kind", "source", "value", "sha256"},
        )
        for key in ("id", "kind", "source", "value"):
            _text(record[key], f"{label}[{index}].{key}")
        _sha256(record["sha256"], f"{label}[{index}].sha256")


def _issue_records(value: Any, label: str, status: str) -> None:
    if not isinstance(value, list) or len(value) > 64:
        raise AssessmentError(f"{label} must be an array with at most 64 records")
    seen: set[str] = set()
    for index, item in enumerate(value):
        record = _object(
            item,
            f"{label}[{index}]",
            {"id", "statement", "status", "source", "recorded_on"},
            {"id", "statement", "status", "source", "recorded_on"},
        )
        identifier = _text(record["id"], f"{label}[{index}].id")
        if ISSUE_ID.fullmatch(identifier) is None:
            raise AssessmentError(f"{label}[{index}].id is not stable dot notation")
        _text(record["statement"], f"{label}[{index}].statement")
        if record["status"] != status:
            raise AssessmentError(f"{label}[{index}].status must be {status}")
        _text(record["source"], f"{label}[{index}].source")
        _full_date(record["recorded_on"], f"{label}[{index}].recorded_on")
        fingerprint = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if fingerprint in seen:
            raise AssessmentError(f"{label} must not contain exact duplicate records")
        seen.add(fingerprint)


def _declaration(value: Any, label: str, *, list_value: bool, accepted: bool) -> None:
    record = _object(
        value,
        label,
        {"value", "status", "source", "recorded_on"},
        {"value", "status", "source", "recorded_on"},
    )
    allowed_statuses = {"confirmed", "TBD", "not-applicable"}
    if not accepted:
        allowed_statuses.add("provisional")
    if record["status"] not in allowed_statuses:
        raise AssessmentError(f"{label}.status is incompatible with the review status")
    if list_value:
        _bounded_text_list(record["value"], f"{label}.value")
    else:
        _text(record["value"], f"{label}.value")
    _text(record["source"], f"{label}.source")
    _full_date(record["recorded_on"], f"{label}.recorded_on")


def validate_context(payload: Any, *, require_accepted: bool = True) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AssessmentError("context must be an object")
    version = payload.get("schema_version")
    if version not in {"1.0", "1.1"}:
        raise AssessmentError("context.schema_version must be 1.0 or 1.1")
    allowed = LEGACY_ROOT_KEYS if version == "1.0" else ROOT_KEYS
    required = {"schema_version", "review", "application"}
    if version == "1.1":
        required.update({"questionnaire_input", "answers_input"})
    root = _object(payload, "context", allowed, required)
    if version == "1.0":
        review_allowed = {"status", "confirmed_on", "source"}
        review_required = review_allowed
    else:
        raw_review = root.get("review")
        status = raw_review.get("status") if isinstance(raw_review, dict) else None
        if status == "draft":
            review_allowed = {"status", "drafted_on", "source"}
            review_required = review_allowed
        elif status == "accepted":
            review_allowed = {"status", "confirmed_on", "source", "accepted_by"}
            review_required = review_allowed
        else:
            raise AssessmentError("review.status must be draft or accepted")
    review = _object(root["review"], "review", review_allowed, review_required)
    if version == "1.0" and review["status"] != "accepted":
        raise AssessmentError("review.status must be accepted")
    if require_accepted and review["status"] != "accepted":
        raise AssessmentError("review.status must be accepted")
    if review["status"] == "accepted":
        _full_date(review["confirmed_on"], "review.confirmed_on")
        if "accepted_by" in review:
            _text(review["accepted_by"], "review.accepted_by")
    else:
        _full_date(review["drafted_on"], "review.drafted_on")
    _text(review["source"], "review.source")
    accepted = review["status"] == "accepted"
    application = _object(
        root["application"],
        "application",
        {"name", "purpose", "stakeholders"},
        {"name", "purpose", "stakeholders"} if accepted else set(),
    )
    if "name" in application:
        _text(application["name"], "application.name")
    if "purpose" in application:
        _text(application["purpose"], "application.purpose")
    if "stakeholders" in application:
        if version == "1.1":
            _bounded_text_list(application["stakeholders"], "application.stakeholders")
        else:
            _text_list(application["stakeholders"], "application.stakeholders")
    for record in _records(
        root.get("components", []),
        "components",
        {"id", "name", "responsibility", "paths"},
        {"id", "name", "responsibility", "paths"},
    ):
        _text(record["name"], "components.name")
        _text(record["responsibility"], "components.responsibility")
        if version == "1.1":
            _bounded_text_list(record["paths"], "components.paths")
        else:
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
    if version == "1.1":
        requirements = _object(
            root.get("requirements", {}),
            "requirements",
            {
                "priorities",
                "constraints",
                "risk_tolerance",
                "deployment_context",
                "evidence_expectations",
            },
            set(),
        )
        for key in ("priorities", "constraints", "evidence_expectations"):
            if key in requirements:
                _declaration(
                    requirements[key], f"requirements.{key}", list_value=True, accepted=accepted
                )
        for key in ("risk_tolerance", "deployment_context"):
            if key in requirements:
                _declaration(
                    requirements[key], f"requirements.{key}", list_value=False, accepted=accepted
                )
        provenance = _object(
            root.get("application_provenance", {}),
            "application_provenance",
            {"name", "purpose", "stakeholders"},
            set(application) if accepted else set(),
        )
        for key, value in provenance.items():
            record = _object(
                value,
                f"application_provenance.{key}",
                {"origin", "status", "source", "recorded_on"},
                {"origin", "status", "source", "recorded_on"},
            )
            if record["origin"] not in {"observed", "human-declared"}:
                raise AssessmentError(f"application_provenance.{key}.origin is unsupported")
            allowed_statuses = {"confirmed"} if accepted else {"confirmed", "provisional"}
            if record["status"] not in allowed_statuses:
                raise AssessmentError(
                    f"application_provenance.{key}.status is incompatible with the review status"
                )
            _text(record["source"], f"application_provenance.{key}.source")
            _full_date(record["recorded_on"], f"application_provenance.{key}.recorded_on")
        _issue_records(root.get("contradictions", []), "contradictions", "unresolved")
        _issue_records(root.get("unknowns", []), "unknowns", "open")
        questionnaire_input = _object(
            root["questionnaire_input"],
            "questionnaire_input",
            {"path", "sha256", "schema_version", "target", "repository_evidence"},
            {"path", "sha256", "schema_version", "target", "repository_evidence"},
        )
        _text(questionnaire_input["path"], "questionnaire_input.path")
        _sha256(questionnaire_input["sha256"], "questionnaire_input.sha256")
        if questionnaire_input["schema_version"] != "1.0":
            raise AssessmentError("questionnaire_input.schema_version must be 1.0")
        _target_descriptor(questionnaire_input["target"], "questionnaire_input.target")
        _repository_evidence(
            questionnaire_input["repository_evidence"],
            "questionnaire_input.repository_evidence",
        )
        answers_input = _object(
            root["answers_input"],
            "answers_input",
            {"path", "sha256", "schema_version", "source", "recorded_on"},
            {"path", "sha256", "schema_version", "source", "recorded_on"},
        )
        _text(answers_input["path"], "answers_input.path")
        _sha256(answers_input["sha256"], "answers_input.sha256")
        if answers_input["schema_version"] != "1.0":
            raise AssessmentError("answers_input.schema_version must be 1.0")
        _text(answers_input["source"], "answers_input.source")
        _full_date(answers_input["recorded_on"], "answers_input.recorded_on")
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
        payload = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise AssessmentError(f"cannot read context JSON: {exc}") from exc
    return validate_context(payload), hashlib.sha256(raw).hexdigest()
