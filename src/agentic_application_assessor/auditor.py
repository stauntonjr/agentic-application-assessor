"""Fail-closed Agentic Repo Auditor 0.1.0/schema-1.2 artifact import."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import stat
from typing import Any

from .errors import AssessmentError
from .git import auditor_target_identity
from .model import AuditorInput, Evidence, Target


MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_FINDINGS = 256
MAX_FINDING_EVIDENCE = 256
MAX_IMPORTED_EVIDENCE = 1_024
MAX_STRING_CHARS = 65_536
AUDITOR_SCHEMA_VERSION = "1.2"
AUDITOR_TOOL_NAME = "agentic-repo-auditor"
AUDITOR_TOOL_VERSION = "0.1.0"
FINDING_ID = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
STATE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
REVISION = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
STATUSES = ("pass", "warn", "fail", "not-applicable", "unknown")
SEVERITIES = ("info", "low", "medium", "high")
CATEGORIES = ("governance", "git", "ci", "security", "testing", "agent-readiness")


@dataclass(frozen=True)
class ImportedAuditorArtifact:
    """Validated artifact metadata and evidence records."""

    descriptor: AuditorInput
    evidence: tuple[Evidence, ...]
    finding_count: int
    nested_evidence_count: int


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


def _object(value: Any, label: str, *, allowed: set[str], required: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssessmentError(f"{label} must be an object")
    extra = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if extra:
        raise AssessmentError(f"{label} has unsupported properties: {', '.join(extra)}")
    if missing:
        raise AssessmentError(f"{label} is missing required properties: {', '.join(missing)}")
    return value


def _string(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise AssessmentError(f"{label} must be {qualifier}")
    if len(value) > MAX_STRING_CHARS:
        raise AssessmentError(f"{label} exceeds the adapter string bound")
    try:
        value.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise AssessmentError(f"{label} is not valid Unicode") from exc
    return value


def _count(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise AssessmentError(f"{label} must be a non-negative integer")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise AssessmentError(f"{label} must be an array")
    result = [_string(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise AssessmentError(f"{label} must contain unique values")
    return result


def _validate_declaration(value: Any, label: str, *, primary_check: bool) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise AssessmentError(f"{label} must be null or an object")
    keys = set(value)
    if keys == {"not_applicable_reason"}:
        _string(value["not_applicable_reason"], f"{label}.not_applicable_reason")
        return
    expected = {"command", "source"} if primary_check else {"path"}
    if keys != expected:
        raise AssessmentError(f"{label} has an invalid declaration shape")
    for key in sorted(expected):
        _string(value[key], f"{label}.{key}")


def _validate_payload(payload: Any) -> dict[str, Any]:
    root_keys = {"schema_version", "tool", "target", "configuration", "summary", "findings"}
    root = _object(payload, "Auditor report", allowed=root_keys, required=root_keys)
    if root["schema_version"] != AUDITOR_SCHEMA_VERSION:
        raise AssessmentError("Auditor report schema_version must be 1.2")

    tool = _object(
        root["tool"],
        "Auditor report tool",
        allowed={"name", "version"},
        required={"name", "version"},
    )
    if tool["name"] != AUDITOR_TOOL_NAME or tool["version"] != AUDITOR_TOOL_VERSION:
        raise AssessmentError("Auditor report must identify agentic-repo-auditor 0.1.0")

    target_keys = {"name", "revision", "branch", "dirty", "state_id"}
    target = _object(
        root["target"], "Auditor report target", allowed=target_keys, required=target_keys
    )
    _string(target["name"], "Auditor report target.name")
    revision = _string(target["revision"], "Auditor report target.revision")
    if REVISION.fullmatch(revision) is None:
        raise AssessmentError(
            "Auditor report target.revision must be a 40- or 64-character lowercase Git SHA"
        )
    _string(target["branch"], "Auditor report target.branch")
    if type(target["dirty"]) is not bool:
        raise AssessmentError("Auditor report target.dirty must be boolean")
    state_id = _string(target["state_id"], "Auditor report target.state_id")
    if STATE_ID.fullmatch(state_id) is None:
        raise AssessmentError("Auditor report target.state_id must be sha256:<64 lowercase hex>")

    configuration = _object(
        root["configuration"],
        "Auditor report configuration",
        allowed={"disabled_checks", "evidence"},
        required={"disabled_checks", "evidence"},
    )
    _string_list(configuration["disabled_checks"], "Auditor report configuration.disabled_checks")
    declarations = _object(
        configuration["evidence"],
        "Auditor report configuration.evidence",
        allowed={"project_contract", "primary_check"},
        required={"project_contract", "primary_check"},
    )
    _validate_declaration(
        declarations["project_contract"],
        "Auditor report configuration.evidence.project_contract",
        primary_check=False,
    )
    _validate_declaration(
        declarations["primary_check"],
        "Auditor report configuration.evidence.primary_check",
        primary_check=True,
    )

    summary = _object(
        root["summary"],
        "Auditor report summary",
        allowed={"total", "by_status", "by_severity"},
        required={"total", "by_status", "by_severity"},
    )
    _count(summary["total"], "Auditor report summary.total")
    status_counts = _object(
        summary["by_status"],
        "Auditor report summary.by_status",
        allowed=set(STATUSES),
        required=set(STATUSES),
    )
    severity_counts = _object(
        summary["by_severity"],
        "Auditor report summary.by_severity",
        allowed=set(SEVERITIES),
        required=set(SEVERITIES),
    )
    for key in STATUSES:
        _count(status_counts[key], f"Auditor report summary.by_status.{key}")
    for key in SEVERITIES:
        _count(severity_counts[key], f"Auditor report summary.by_severity.{key}")

    findings = root["findings"]
    if not isinstance(findings, list):
        raise AssessmentError("Auditor report findings must be an array")
    if len(findings) > MAX_FINDINGS:
        raise AssessmentError("Auditor report exceeds the 256-finding adapter bound")
    finding_ids: list[str] = []
    nested_count = 0
    for finding_index, item in enumerate(findings):
        label = f"Auditor report findings[{finding_index}]"
        keys = {
            "id",
            "category",
            "status",
            "severity",
            "title",
            "description",
            "evidence",
            "remediation",
        }
        finding = _object(item, label, allowed=keys, required=keys)
        finding_id = _string(finding["id"], f"{label}.id")
        if FINDING_ID.fullmatch(finding_id) is None:
            raise AssessmentError(f"{label}.id is not a canonical finding identifier")
        finding_ids.append(finding_id)
        if finding["category"] not in CATEGORIES:
            raise AssessmentError(f"{label}.category is unsupported")
        if finding["status"] not in STATUSES:
            raise AssessmentError(f"{label}.status is unsupported")
        if finding["severity"] not in SEVERITIES:
            raise AssessmentError(f"{label}.severity is unsupported")
        for key in ("title", "description", "remediation"):
            _string(finding[key], f"{label}.{key}")
        records = finding["evidence"]
        if not isinstance(records, list) or not records:
            raise AssessmentError(f"{label}.evidence must be a non-empty array")
        if len(records) > MAX_FINDING_EVIDENCE:
            raise AssessmentError(f"{label}.evidence exceeds the 256-item adapter bound")
        nested_count += len(records)
        if nested_count > MAX_IMPORTED_EVIDENCE:
            raise AssessmentError("Auditor report exceeds the 1,024-item evidence adapter bound")
        for evidence_index, record in enumerate(records):
            evidence_label = f"{label}.evidence[{evidence_index}]"
            evidence = _object(
                record,
                evidence_label,
                allowed={"kind", "path", "value"},
                required={"kind", "path", "value"},
            )
            _string(evidence["kind"], f"{evidence_label}.kind")
            _string(evidence["path"], f"{evidence_label}.path", allow_empty=True)
            _string(evidence["value"], f"{evidence_label}.value")
    duplicates = sorted(item for item, count in Counter(finding_ids).items() if count > 1)
    if duplicates:
        raise AssessmentError(f"Auditor report has duplicate finding IDs: {', '.join(duplicates)}")

    expected_statuses = Counter(item["status"] for item in findings)
    expected_severities = Counter(item["severity"] for item in findings)
    if summary["total"] != len(findings):
        raise AssessmentError("Auditor report summary.total does not match findings")
    if any(status_counts[key] != expected_statuses[key] for key in STATUSES):
        raise AssessmentError("Auditor report summary.by_status does not match findings")
    if any(severity_counts[key] != expected_severities[key] for key in SEVERITIES):
        raise AssessmentError("Auditor report summary.by_severity does not match findings")
    return root


def _artifact_file(path: Path) -> tuple[bytes, str]:
    lexical = path.absolute()
    for candidate in (lexical, *lexical.parents):
        try:
            if stat.S_ISLNK(candidate.lstat().st_mode):
                raise AssessmentError(f"Auditor report path traverses a symlink: {candidate}")
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise AssessmentError(f"cannot inspect Auditor report path: {exc}") from exc
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise AssessmentError(f"cannot inspect Auditor report file: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise AssessmentError("Auditor report must be a regular file, not a symlink")
    if metadata.st_size > MAX_ARTIFACT_BYTES:
        raise AssessmentError("Auditor report exceeds the 2 MiB adapter bound")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AssessmentError(f"cannot read Auditor report file: {exc}") from exc
    return raw, hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def load_auditor_artifact(
    path: Path, root: Path, assessor_target: Target
) -> ImportedAuditorArtifact:
    """Load, validate, bind, and normalize one canonical Auditor report."""

    raw, digest = _artifact_file(path)
    try:
        payload = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (_DuplicateKey, UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise AssessmentError(f"cannot read Auditor report JSON: {exc}") from exc
    report = _validate_payload(payload)
    actual_target = auditor_target_identity(root)
    imported_target = report["target"]
    if imported_target != actual_target:
        mismatches = sorted(
            key for key in actual_target if imported_target.get(key) != actual_target[key]
        )
        raise AssessmentError(
            "Auditor report target does not match the assessed repository: " + ", ".join(mismatches)
        )
    assessor_overlap = {
        "name": assessor_target.name,
        "revision": assessor_target.revision,
        "branch": "DETACHED" if assessor_target.branch == "(detached)" else assessor_target.branch,
        "dirty": assessor_target.dirty,
    }
    collector_mismatches = sorted(
        key for key, value in assessor_overlap.items() if actual_target[key] != value
    )
    if collector_mismatches:
        raise AssessmentError(
            "Auditor and Assessor target identity collectors disagree: "
            + ", ".join(collector_mismatches)
        )

    descriptor = AuditorInput(
        path.name,
        digest,
        AUDITOR_SCHEMA_VERSION,
        AUDITOR_TOOL_NAME,
        AUDITOR_TOOL_VERSION,
        Target(
            imported_target["name"],
            imported_target["revision"],
            imported_target["branch"],
            imported_target["dirty"],
            imported_target["state_id"],
        ),
    )
    source_root = path.name
    records: list[Evidence] = [
        Evidence(
            "auditor.artifact",
            "imported-tool",
            "analysis-artifact",
            f"{source_root}#",
            f"{AUDITOR_TOOL_NAME} {AUDITOR_TOOL_VERSION} report schema {AUDITOR_SCHEMA_VERSION}",
            digest,
        ),
        Evidence(
            "auditor.configuration",
            "imported-tool",
            "repository-audit-configuration",
            f"{source_root}#/configuration",
            _canonical(report["configuration"]),
            digest,
        ),
        Evidence(
            "auditor.summary",
            "imported-tool",
            "repository-audit-summary",
            f"{source_root}#/summary",
            _canonical(report["summary"]),
            digest,
        ),
    ]
    for finding_index, finding in enumerate(report["findings"]):
        finding_id = finding["id"]
        finding_record = {key: value for key, value in finding.items() if key != "evidence"}
        records.append(
            Evidence(
                f"auditor.finding.{finding_id}",
                "imported-tool",
                "repository-audit-finding",
                f"{source_root}#/findings/{finding_index}",
                _canonical(finding_record),
                digest,
            )
        )
        for evidence_index, evidence in enumerate(finding["evidence"]):
            records.append(
                Evidence(
                    f"auditor.finding.{finding_id}.evidence.{evidence_index:04d}",
                    "imported-tool",
                    "repository-audit-finding-evidence",
                    f"{source_root}#/findings/{finding_index}/evidence/{evidence_index}",
                    _canonical(evidence),
                    digest,
                )
            )
    return ImportedAuditorArtifact(
        descriptor,
        tuple(records),
        len(report["findings"]),
        sum(len(item["evidence"]) for item in report["findings"]),
    )
