"""Deterministic, gap-only application-context questionnaire workflow."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import stat
import tomllib
from typing import Any

from .context import load_context, validate_context
from .errors import AssessmentError
from .git import target_identity


SCHEMA_VERSION = "1.0"
CONTEXT_SCHEMA_VERSION = "1.1"
MAX_INPUT_BYTES = 256 * 1024
MAX_TEXT_CHARS = 4096
MAX_LIST_ITEMS = 64
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


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8") + b"\n"


def render_questionnaire_json(value: dict[str, Any]) -> str:
    """Render a questionnaire or reconciled context deterministically."""

    return _canonical_bytes(value).decode("utf-8")


def _safe_json_file(path: Path, label: str) -> tuple[dict[str, Any], str]:
    lexical = path.absolute()
    for candidate in (lexical, *lexical.parents):
        try:
            if stat.S_ISLNK(candidate.lstat().st_mode):
                raise AssessmentError(f"{label} path traverses a symlink: {candidate}")
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise AssessmentError(f"cannot inspect {label} path: {exc}") from exc
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise AssessmentError(f"cannot inspect {label} file: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise AssessmentError(f"{label} must be a regular file, not a symlink")
    if metadata.st_size > MAX_INPUT_BYTES:
        raise AssessmentError(f"{label} exceeds the 256 KiB input bound")
    try:
        raw = path.read_bytes()
        payload = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (
        _DuplicateKey,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ) as exc:
        raise AssessmentError(f"cannot read {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssessmentError(f"{label} must be a JSON object")
    return payload, hashlib.sha256(raw).hexdigest()


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


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssessmentError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise AssessmentError(f"{label} must not contain surrounding whitespace")
    if len(value) > MAX_TEXT_CHARS:
        raise AssessmentError(f"{label} exceeds the 4,096-character bound")
    return value


def _date(value: Any, label: str) -> str:
    result = _text(value, label)
    try:
        date.fromisoformat(result)
    except ValueError as exc:
        raise AssessmentError(f"{label} must be an RFC 3339 full-date") from exc
    return result


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > MAX_LIST_ITEMS:
        raise AssessmentError(f"{label} must contain between 1 and 64 strings")
    result = [_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise AssessmentError(f"{label} must contain unique values")
    return result


QUESTION_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "application.name",
        "category": "intent",
        "prompt": "What owner-accepted name identifies this application?",
        "response_type": "string",
        "rationale": "A stable application identity is required for accepted context.",
    },
    {
        "id": "application.purpose",
        "category": "intent",
        "prompt": "What does this application do, for whom, and toward what outcome?",
        "response_type": "string",
        "rationale": "Repository structure cannot establish product intent.",
    },
    {
        "id": "application.stakeholders",
        "category": "intent",
        "prompt": "Which users, maintainers, or decision owners are stakeholders?",
        "response_type": "string-array",
        "rationale": "Stakeholders determine whose requirements and risks matter.",
    },
    {
        "id": "requirements.priorities",
        "category": "priorities",
        "prompt": "Which outcomes or capabilities are highest priority?",
        "response_type": "string-array",
        "rationale": "Priorities make later findings decision-relative.",
    },
    {
        "id": "requirements.constraints",
        "category": "constraints",
        "prompt": "Which technical, budget, schedule, licensing, or data constraints are binding?",
        "response_type": "string-array",
        "rationale": "Constraints bound feasible recommendations.",
    },
    {
        "id": "requirements.risk-tolerance",
        "category": "risk-tolerance",
        "prompt": "What risk tolerance and human-approval boundary should guide the assessment?",
        "response_type": "string",
        "rationale": "Risk disposition cannot be inferred from code.",
    },
    {
        "id": "requirements.deployment-context",
        "category": "deployment-context",
        "prompt": "Where and how is the application deployed, operated, recovered, or retired?",
        "response_type": "string",
        "rationale": "Repository deployment files are signals, not proof of live operation.",
    },
    {
        "id": "requirements.evidence-expectations",
        "category": "evidence-expectations",
        "prompt": "Which evidence, provenance, reproducibility, or confidence standard is required?",
        "response_type": "string-array",
        "rationale": "Evidence expectations define the bar for useful findings.",
    },
)
QUESTION_BY_ID = {item["id"]: item for item in QUESTION_DEFINITIONS}
REQUIREMENT_IDS = tuple(
    item["id"].partition(".")[2]
    for item in QUESTION_DEFINITIONS
    if item["id"].startswith("requirements.")
)


def _target_dict(target: Any) -> dict[str, Any]:
    return target.as_dict()


def _repository_evidence(
    root: Path, paths: tuple[str, ...], target: Any
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evidence = [
        {
            "id": "repository.target-identity",
            "kind": "git-target-identity",
            "source": f"target:{target.state_id}",
            "value": target.name,
            "sha256": target.state_id.removeprefix("sha256:"),
        }
    ]
    defaults: dict[str, Any] = {}
    manifest = root / "pyproject.toml"
    if "pyproject.toml" in paths:
        try:
            metadata = manifest.lstat()
            if (
                stat.S_ISREG(metadata.st_mode)
                and not stat.S_ISLNK(metadata.st_mode)
                and metadata.st_size <= MAX_INPUT_BYTES
            ):
                raw = manifest.read_bytes()
                parsed = tomllib.loads(raw.decode("utf-8"))
                project = parsed.get("project", {}) if isinstance(parsed, dict) else {}
                name = project.get("name") if isinstance(project, dict) else None
                if (
                    isinstance(name, str)
                    and name
                    and name == name.strip()
                    and len(name) <= MAX_TEXT_CHARS
                ):
                    evidence.append(
                        {
                            "id": "repository.pyproject-name",
                            "kind": "package-metadata",
                            "source": "pyproject.toml#/project/name",
                            "value": name,
                            "sha256": hashlib.sha256(raw).hexdigest(),
                        }
                    )
                    defaults["application.name"] = {
                        "value": name,
                        "origin": "observed",
                        "source": "pyproject.toml#/project/name",
                    }
        except (OSError, UnicodeError, tomllib.TOMLDecodeError):
            # A malformed manifest is not interpreted and never blocks asking the owner.
            pass
    deployment = sorted(
        item
        for item in paths
        if Path(item).name in {"Dockerfile", "compose.yaml", "compose.yml", "Procfile"}
        or any(part in {"deploy", "deployment", "k8s", "terraform"} for part in Path(item).parts)
    )
    if deployment:
        retained: list[str] = []
        for item in deployment[:MAX_LIST_ITEMS]:
            if len("; ".join((*retained, item))) > MAX_TEXT_CHARS:
                break
            retained.append(item)
        if retained:
            joined = "; ".join(retained)
            evidence.append(
                {
                    "id": "repository.deployment-signals",
                    "kind": "deployment-file-inventory",
                    "source": f"target:{target.state_id}#paths",
                    "value": joined,
                    "sha256": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
                }
            )
    return evidence, defaults


def _declared_paths(context: dict[str, Any] | None) -> set[str]:
    if context is None:
        return set()
    result = {
        f"application.{key}"
        for key in ("name", "purpose", "stakeholders")
        if key in context["application"]
    }
    for key, declaration in context.get("requirements", {}).items():
        if declaration.get("status") in {"confirmed", "not-applicable"}:
            result.add(f"requirements.{key.replace('_', '-')}")
    return result


def generate_questionnaire(target_path: Path, context_path: Path | None = None) -> dict[str, Any]:
    """Generate questions only for gaps not covered by accepted context or safe observations."""

    root, target, paths = target_identity(target_path)
    context: dict[str, Any] | None = None
    context_input: dict[str, Any] | None = None
    if context_path is not None:
        context, digest = load_context(context_path)
        context_input = {
            "path": context_path.name,
            "sha256": digest,
            "schema_version": context["schema_version"],
        }
    evidence, defaults = _repository_evidence(root, paths, target)
    declared = _declared_paths(context)
    questions: list[dict[str, Any]] = []
    for definition in QUESTION_DEFINITIONS:
        identifier = definition["id"]
        if identifier in declared:
            continue
        question = dict(definition)
        if identifier == "requirements.deployment-context":
            signals = [
                item["value"] for item in evidence if item["id"] == "repository.deployment-signals"
            ]
            if signals:
                question["repository_context"] = f"Observed deployment-file signals: {signals[0]}"
        questions.append(question)
    result = {
        "schema_version": SCHEMA_VERSION,
        "target": _target_dict(target),
        "accepted_context": context_input,
        "repository_evidence": evidence,
        "observed_defaults": [
            {"question_id": key, **value} for key, value in sorted(defaults.items())
        ],
        "questions": questions,
    }
    final_root, final_target, final_paths = target_identity(target_path)
    if final_root != root or final_target != target or final_paths != paths:
        raise AssessmentError("target changed during questionnaire generation")
    return result


def validate_questionnaire(payload: Any) -> dict[str, Any]:
    keys = {
        "schema_version",
        "target",
        "accepted_context",
        "repository_evidence",
        "observed_defaults",
        "questions",
    }
    root = _object(payload, "questionnaire", allowed=keys, required=keys)
    if root["schema_version"] != SCHEMA_VERSION:
        raise AssessmentError("questionnaire.schema_version must be 1.0")
    target = _object(
        root["target"],
        "questionnaire.target",
        allowed={"name", "revision", "branch", "dirty", "state_id"},
        required={"name", "revision", "branch", "dirty", "state_id"},
    )
    for key in ("name", "revision", "branch", "state_id"):
        _text(target[key], f"questionnaire.target.{key}")
    if REVISION.fullmatch(target["revision"]) is None:
        raise AssessmentError("questionnaire.target.revision is not a canonical Git object ID")
    if STATE_ID.fullmatch(target["state_id"]) is None:
        raise AssessmentError("questionnaire.target.state_id must be sha256:<64 lowercase hex>")
    if type(target["dirty"]) is not bool:
        raise AssessmentError("questionnaire.target.dirty must be boolean")
    if root["accepted_context"] is not None:
        descriptor = _object(
            root["accepted_context"],
            "questionnaire.accepted_context",
            allowed={"path", "sha256", "schema_version"},
            required={"path", "sha256", "schema_version"},
        )
        for key in descriptor:
            _text(descriptor[key], f"questionnaire.accepted_context.{key}")
        if SHA256.fullmatch(descriptor["sha256"]) is None:
            raise AssessmentError("questionnaire.accepted_context.sha256 is invalid")
        if descriptor["schema_version"] not in {"1.0", "1.1"}:
            raise AssessmentError("questionnaire.accepted_context.schema_version is unsupported")
    evidence = root["repository_evidence"]
    if not isinstance(evidence, list) or not evidence or len(evidence) > MAX_LIST_ITEMS:
        raise AssessmentError("questionnaire.repository_evidence must contain 1 to 64 records")
    for index, item in enumerate(evidence):
        record = _object(
            item,
            f"questionnaire.repository_evidence[{index}]",
            allowed={"id", "kind", "source", "value", "sha256"},
            required={"id", "kind", "source", "value", "sha256"},
        )
        for key in record:
            _text(record[key], f"questionnaire.repository_evidence[{index}].{key}")
        if SHA256.fullmatch(record["sha256"]) is None:
            raise AssessmentError(f"questionnaire.repository_evidence[{index}].sha256 is invalid")
    defaults = root["observed_defaults"]
    if not isinstance(defaults, list) or len(defaults) > len(QUESTION_DEFINITIONS):
        raise AssessmentError("questionnaire.observed_defaults exceeds its bound")
    for index, item in enumerate(defaults):
        default = _object(
            item,
            f"questionnaire.observed_defaults[{index}]",
            allowed={"question_id", "value", "origin", "source"},
            required={"question_id", "value", "origin", "source"},
        )
        if default["question_id"] != "application.name" or default["origin"] != "observed":
            raise AssessmentError(f"questionnaire.observed_defaults[{index}] is unsupported")
        _text(default["value"], f"questionnaire.observed_defaults[{index}].value")
        _text(default["source"], f"questionnaire.observed_defaults[{index}].source")
    questions = root["questions"]
    if not isinstance(questions, list) or len(questions) > len(QUESTION_DEFINITIONS):
        raise AssessmentError("questionnaire.questions exceeds its bound")
    identifiers: list[str] = []
    for index, item in enumerate(questions):
        question = _object(
            item,
            f"questionnaire.questions[{index}]",
            allowed={
                "id",
                "category",
                "prompt",
                "response_type",
                "rationale",
                "repository_context",
            },
            required={"id", "category", "prompt", "response_type", "rationale"},
        )
        identifier = question["id"]
        if identifier not in QUESTION_BY_ID:
            raise AssessmentError(f"questionnaire.questions[{index}].id is unsupported")
        identifiers.append(identifier)
        if question["category"] not in {
            "intent",
            "priorities",
            "constraints",
            "risk-tolerance",
            "deployment-context",
            "evidence-expectations",
        }:
            raise AssessmentError(f"questionnaire.questions[{index}].category is unsupported")
        if question["response_type"] not in {"string", "string-array"}:
            raise AssessmentError(f"questionnaire.questions[{index}].response_type is unsupported")
        for key in ("prompt", "rationale"):
            _text(question[key], f"questionnaire.questions[{index}].{key}")
        if "repository_context" in question:
            _text(
                question["repository_context"],
                f"questionnaire.questions[{index}].repository_context",
            )
    if len(identifiers) != len(set(identifiers)):
        raise AssessmentError("questionnaire question IDs must be unique")
    return root


def validate_answers(payload: Any) -> dict[str, Any]:
    root = _object(
        payload,
        "answers",
        allowed={
            "schema_version",
            "questionnaire_sha256",
            "submission",
            "answers",
            "contradictions",
            "unknowns",
        },
        required={
            "schema_version",
            "questionnaire_sha256",
            "submission",
            "answers",
            "contradictions",
            "unknowns",
        },
    )
    if root["schema_version"] != SCHEMA_VERSION:
        raise AssessmentError("answers.schema_version must be 1.0")
    digest = _text(root["questionnaire_sha256"], "answers.questionnaire_sha256")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise AssessmentError(
            "answers.questionnaire_sha256 must be 64 lowercase hexadecimal characters"
        )
    submission = _object(
        root["submission"],
        "answers.submission",
        allowed={"source", "recorded_on"},
        required={"source", "recorded_on"},
    )
    _text(submission["source"], "answers.submission.source")
    _date(submission["recorded_on"], "answers.submission.recorded_on")
    records = root["answers"]
    if not isinstance(records, dict) or len(records) > len(QUESTION_DEFINITIONS):
        raise AssessmentError("answers.answers must be an object with at most 8 entries")
    for identifier, value in records.items():
        if identifier not in QUESTION_BY_ID:
            raise AssessmentError(f"answers.answers has unsupported question ID: {identifier}")
        answer = _object(
            value,
            f"answers.answers.{identifier}",
            allowed={"status", "value"},
            required={"status"},
        )
        if answer["status"] not in {"answered", "unknown", "not-applicable"}:
            raise AssessmentError(f"answers.answers.{identifier}.status is unsupported")
        if identifier.startswith("application.") and answer["status"] == "not-applicable":
            raise AssessmentError(
                f"answers.answers.{identifier}.status must be answered or unknown"
            )
        if answer["status"] in {"answered", "not-applicable"} and "value" not in answer:
            raise AssessmentError(f"answers.answers.{identifier}.value is required")
        if answer["status"] == "unknown" and "value" in answer:
            raise AssessmentError(
                f"answers.answers.{identifier}.value is not allowed for unknown status"
            )
        if "value" in answer:
            response_type = QUESTION_BY_ID[identifier]["response_type"]
            if response_type == "string":
                _text(answer["value"], f"answers.answers.{identifier}.value")
            else:
                _string_list(answer["value"], f"answers.answers.{identifier}.value")
    _string_list(root["contradictions"], "answers.contradictions") if root[
        "contradictions"
    ] else None
    _string_list(root["unknowns"], "answers.unknowns") if root["unknowns"] else None
    if not isinstance(root["contradictions"], list) or not isinstance(root["unknowns"], list):
        raise AssessmentError("answers contradictions and unknowns must be arrays")
    return root


def _load_questionnaire(path: Path) -> tuple[dict[str, Any], str]:
    payload, digest = _safe_json_file(path, "questionnaire")
    return validate_questionnaire(payload), digest


def _load_answers(path: Path) -> tuple[dict[str, Any], str]:
    payload, digest = _safe_json_file(path, "answers")
    return validate_answers(payload), digest


def _base_context(context: dict[str, Any] | None) -> dict[str, Any]:
    if context is None:
        return {
            "schema_version": CONTEXT_SCHEMA_VERSION,
            "application": {},
            "requirements": {},
            "contradictions": [],
            "unknowns": [],
        }
    result = deepcopy(context)
    result["schema_version"] = CONTEXT_SCHEMA_VERSION
    result.setdefault("requirements", {})
    result.setdefault("contradictions", [])
    result.setdefault("unknowns", [])
    return result


def _issue_record(kind: str, statement: str, source: str, recorded_on: str) -> dict[str, str]:
    digest = hashlib.sha256(statement.encode("utf-8")).hexdigest()[:16]
    return {
        "id": f"{kind}.{digest}",
        "statement": statement,
        "status": "unresolved" if kind == "contradiction" else "open",
        "source": source,
        "recorded_on": recorded_on,
    }


def _unique_issue_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        existing = by_id.get(record["id"])
        if existing is not None and existing != record:
            raise AssessmentError(f"conflicting issue record identity: {record['id']}")
        by_id[record["id"]] = record
    return [by_id[key] for key in sorted(by_id)]


def reconcile_questionnaire(
    target_path: Path,
    questionnaire_path: Path,
    answers_path: Path,
    context_path: Path | None = None,
    *,
    accept_by: str | None = None,
    accepted_on: str | None = None,
) -> dict[str, Any]:
    """Reconcile bounded answers into a draft or explicitly accepted context."""

    questionnaire, questionnaire_digest = _load_questionnaire(questionnaire_path)
    answers, answers_digest = _load_answers(answers_path)
    root, target, paths = target_identity(target_path)
    if questionnaire["target"] != _target_dict(target):
        raise AssessmentError("questionnaire target is stale or does not match the exact target")
    if answers["questionnaire_sha256"] != questionnaire_digest:
        raise AssessmentError("answers do not match the exact questionnaire bytes")
    descriptor = questionnaire["accepted_context"]
    context: dict[str, Any] | None = None
    if descriptor is not None:
        if context_path is None:
            raise AssessmentError("the questionnaire requires its bound accepted context")
        context, digest = load_context(context_path)
        if (
            digest != descriptor["sha256"]
            or context["schema_version"] != descriptor["schema_version"]
        ):
            raise AssessmentError("accepted context is stale or does not match the questionnaire")
    elif context_path is not None:
        raise AssessmentError("an unbound context cannot be introduced during reconciliation")
    expected_questionnaire = generate_questionnaire(target_path, context_path)
    if questionnaire != expected_questionnaire:
        raise AssessmentError(
            "questionnaire is not the canonical gap set for the exact target and context"
        )
    if (accept_by is None) != (accepted_on is None):
        raise AssessmentError("--accept-by and --accepted-on must be provided together")
    if accept_by is not None:
        _text(accept_by, "accept_by")
        _date(accepted_on, "accepted_on")

    question_ids = {item["id"] for item in questionnaire["questions"]}
    unexpected = sorted(set(answers["answers"]) - question_ids)
    if unexpected:
        raise AssessmentError(
            "answers include questions that were not asked: " + ", ".join(unexpected)
        )

    result = _base_context(context)
    recorded_on = answers["submission"]["recorded_on"]
    source = answers["submission"]["source"]
    observed_sources: dict[str, str] = {}
    for default in questionnaire["observed_defaults"]:
        identifier = default["question_id"]
        observed_sources[identifier] = default["source"]
        if identifier == "application.name" and "name" not in result["application"]:
            result["application"]["name"] = default["value"]

    unanswered: list[str] = []
    for question in questionnaire["questions"]:
        identifier = question["id"]
        answer = answers["answers"].get(identifier)
        if answer is None or answer["status"] == "unknown":
            unanswered.append(identifier)
            continue
        value = answer["value"]
        namespace, _, field = identifier.partition(".")
        if namespace == "application":
            result["application"][field] = value
        else:
            result["requirements"][field.replace("-", "_")] = {
                "value": value,
                "status": "not-applicable"
                if answer["status"] == "not-applicable"
                else "provisional",
                "source": source,
                "recorded_on": recorded_on,
            }

    contradictions = list(result.get("contradictions", []))
    contradictions.extend(
        _issue_record("contradiction", statement, source, recorded_on)
        for statement in answers["contradictions"]
    )
    result["contradictions"] = _unique_issue_records(contradictions)
    resolved_ids = {f"unknown.{identifier}" for identifier in answers["answers"]}
    unknowns = [item for item in result.get("unknowns", []) if item["id"] not in resolved_ids]
    unknowns.extend(
        _issue_record("unknown", statement, source, recorded_on)
        for statement in answers["unknowns"]
    )
    unknowns.extend(
        {
            "id": f"unknown.{identifier}",
            "statement": f"No owner answer is available for {identifier}.",
            "status": "open",
            "source": source,
            "recorded_on": recorded_on,
        }
        for identifier in unanswered
    )
    result["unknowns"] = _unique_issue_records(unknowns)
    result.setdefault("application_provenance", {})
    for field in ("name", "purpose", "stakeholders"):
        identifier = f"application.{field}"
        if field not in result["application"]:
            continue
        existing_source = (
            context["review"]["source"]
            if context is not None and field in context["application"]
            else None
        )
        if field in result["application_provenance"]:
            continue
        result["application_provenance"][field] = {
            "origin": "human-declared"
            if existing_source or identifier in answers["answers"]
            else "observed",
            "status": "provisional",
            "source": existing_source or observed_sources.get(identifier, source),
            "recorded_on": (
                context["review"]["confirmed_on"]
                if context is not None and field in context["application"]
                else recorded_on
            ),
        }
    result["questionnaire_input"] = {
        "path": questionnaire_path.name,
        "sha256": questionnaire_digest,
        "schema_version": questionnaire["schema_version"],
        "target": questionnaire["target"],
        "repository_evidence": questionnaire["repository_evidence"],
    }
    result["answers_input"] = {
        "path": answers_path.name,
        "sha256": answers_digest,
        "schema_version": answers["schema_version"],
        "source": source,
        "recorded_on": recorded_on,
    }

    if accept_by is None:
        result["review"] = {
            "status": "draft",
            "drafted_on": recorded_on,
            "source": f"questionnaire answers from {source}",
        }
    else:
        missing_application = sorted(
            {"name", "purpose", "stakeholders"} - set(result["application"])
        )
        if missing_application:
            raise AssessmentError(
                "accepted context requires application fields: " + ", ".join(missing_application)
            )
        for metadata in result["application_provenance"].values():
            metadata["status"] = "confirmed"
        for declaration in result["requirements"].values():
            if declaration["status"] == "provisional":
                declaration["status"] = "confirmed"
        result["review"] = {
            "status": "accepted",
            "confirmed_on": accepted_on,
            "source": f"questionnaire answers from {source}",
            "accepted_by": accept_by,
        }
    validated = validate_context(result, require_accepted=accept_by is not None)
    final_root, final_target, final_paths = target_identity(target_path)
    if final_root != root or final_target != target or final_paths != paths:
        raise AssessmentError("target changed during questionnaire reconciliation")
    return validated
