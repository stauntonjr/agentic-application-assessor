from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import pytest  # pyright: ignore[reportMissingImports]

from agentic_application_assessor.context import load_context, validate_context
from agentic_application_assessor.assess import assess
from agentic_application_assessor.errors import AssessmentError
from agentic_application_assessor.questionnaire import (
    generate_questionnaire,
    reconcile_questionnaire,
    render_questionnaire_json,
    validate_answers,
    validate_questionnaire,
)


def run(*args: str, cwd: Path) -> str:
    return subprocess.run(
        args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.strip()


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "application"
    root.mkdir()
    run("git", "init", "-b", "main", cwd=root)
    run("git", "config", "user.name", "Test", cwd=root)
    run("git", "config", "user.email", "test@example.invalid", cwd=root)
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'fixture-app'\nversion = '0.1.0'\n", encoding="utf-8"
    )
    (root / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-m", "fixture", cwd=root)
    return root


def accepted_context(tmp_path: Path) -> Path:
    path = tmp_path / "context.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "review": {
                    "status": "accepted",
                    "confirmed_on": "2026-08-24",
                    "source": "owner review",
                },
                "application": {
                    "name": "Fixture",
                    "purpose": "Test the workflow.",
                    "stakeholders": ["maintainer"],
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def write_questionnaire(path: Path, questionnaire: dict[str, Any]) -> str:
    rendered = render_questionnaire_json(questionnaire)
    path.write_text(rendered, encoding="utf-8")
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def answer_payload(digest: str, identifiers: set[str]) -> dict[str, Any]:
    values: dict[str, Any] = {
        "application.name": {"status": "answered", "value": "Fixture Application"},
        "application.purpose": {"status": "answered", "value": "Support a safe review."},
        "application.stakeholders": {"status": "answered", "value": ["owner", "maintainer"]},
        "requirements.priorities": {"status": "answered", "value": ["correctness"]},
        "requirements.constraints": {"status": "answered", "value": ["local-only"]},
        "requirements.risk-tolerance": {
            "status": "answered",
            "value": "Human approval for external effects.",
        },
        "requirements.deployment-context": {"status": "unknown"},
        "requirements.evidence-expectations": {
            "status": "answered",
            "value": ["reproducible", "source-linked"],
        },
    }
    return {
        "schema_version": "1.0",
        "questionnaire_sha256": digest,
        "submission": {"source": "owner questionnaire", "recorded_on": "2026-08-25"},
        "answers": {key: value for key, value in values.items() if key in identifiers},
        "contradictions": ["README describes a hosted mode while policy says local-only."],
        "unknowns": ["Production operator is not yet identified."],
    }


def test_questionnaire_is_deterministic_gap_only_and_contextualized(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = run("git", "status", "--porcelain=v1", cwd=root)
    first = generate_questionnaire(root)
    second = generate_questionnaire(root)
    assert render_questionnaire_json(first) == render_questionnaire_json(second)
    ids = [item["id"] for item in first["questions"]]
    assert "application.name" in ids
    assert first["observed_defaults"] == [
        {
            "question_id": "application.name",
            "origin": "observed",
            "source": "pyproject.toml#/project/name",
            "value": "fixture-app",
        }
    ]
    deployment = next(
        item for item in first["questions"] if item["id"] == "requirements.deployment-context"
    )
    assert "compose.yaml" in deployment["repository_context"]
    assert len(ids) == len(set(ids)) == 8

    with_context = generate_questionnaire(root, accepted_context(tmp_path))
    assert all(not item["id"].startswith("application.") for item in with_context["questions"])
    assert len(with_context["questions"]) == 5
    assert run("git", "status", "--porcelain=v1", cwd=root) == before


def test_reconcile_drafts_then_requires_explicit_acceptance(tmp_path: Path) -> None:
    root = repository(tmp_path)
    questionnaire = generate_questionnaire(root)
    questionnaire_path = tmp_path / "questionnaire.json"
    digest = write_questionnaire(questionnaire_path, questionnaire)
    ids = {item["id"] for item in questionnaire["questions"]}
    answers = answer_payload(digest, ids)
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    before = run("git", "status", "--porcelain=v1", cwd=root)

    draft = reconcile_questionnaire(root, questionnaire_path, answers_path)
    assert draft["review"]["status"] == "draft"
    assert draft["application_provenance"]["name"]["origin"] == "human-declared"
    assert draft["application_provenance"]["name"]["status"] == "provisional"
    assert draft["requirements"]["priorities"]["status"] == "provisional"
    assert any(
        item["id"] == "unknown.requirements.deployment-context" for item in draft["unknowns"]
    )
    with pytest.raises(AssessmentError, match="review.status must be accepted"):
        validate_context(draft)

    accepted = reconcile_questionnaire(
        root,
        questionnaire_path,
        answers_path,
        accept_by="Jack Rory Staunton",
        accepted_on="2026-08-25",
    )
    assert accepted["review"]["status"] == "accepted"
    assert accepted["application_provenance"]["name"]["status"] == "confirmed"
    assert accepted["requirements"]["priorities"]["status"] == "confirmed"
    accepted_path = tmp_path / "accepted.json"
    accepted_path.write_text(render_questionnaire_json(accepted), encoding="utf-8")
    assert load_context(accepted_path)[0] == accepted
    assert assess(root, accepted_path).as_dict()["inputs"]["context"]["schema_version"] == "1.1"
    assert run("git", "status", "--porcelain=v1", cwd=root) == before


def test_reconcile_rejects_hand_edited_gap_set(tmp_path: Path) -> None:
    root = repository(tmp_path)
    questionnaire = generate_questionnaire(root)
    questionnaire["questions"] = questionnaire["questions"][:-1]
    questionnaire_path = tmp_path / "questionnaire.json"
    digest = write_questionnaire(questionnaire_path, questionnaire)
    answers = answer_payload(digest, {item["id"] for item in questionnaire["questions"]})
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    with pytest.raises(AssessmentError, match="not the canonical gap set"):
        reconcile_questionnaire(root, questionnaire_path, answers_path)


def test_accepted_context_is_preserved_and_cannot_be_silently_overwritten(tmp_path: Path) -> None:
    root = repository(tmp_path)
    context_path = accepted_context(tmp_path)
    questionnaire = generate_questionnaire(root, context_path)
    questionnaire_path = tmp_path / "questionnaire.json"
    digest = write_questionnaire(questionnaire_path, questionnaire)
    ids = {item["id"] for item in questionnaire["questions"]}
    answers = answer_payload(digest, ids)
    answers["answers"]["application.purpose"] = {
        "status": "answered",
        "value": "Overwrite accepted intent.",
    }
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    with pytest.raises(AssessmentError, match="questions that were not asked: application.purpose"):
        reconcile_questionnaire(root, questionnaire_path, answers_path, context_path)

    del answers["answers"]["application.purpose"]
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    accepted = reconcile_questionnaire(
        root,
        questionnaire_path,
        answers_path,
        context_path,
        accept_by="Jack Rory Staunton",
        accepted_on="2026-08-25",
    )
    assert accepted["application"]["purpose"] == "Test the workflow."
    assert accepted["application_provenance"]["purpose"]["source"] == "owner review"


def test_inputs_reject_duplicates_malformed_oversize_deep_and_symlink(tmp_path: Path) -> None:
    root = repository(tmp_path)
    questionnaire = generate_questionnaire(root)
    questionnaire_path = tmp_path / "questionnaire.json"
    digest = write_questionnaire(questionnaire_path, questionnaire)
    answers_path = tmp_path / "answers.json"
    answers_path.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")
    with pytest.raises(AssessmentError, match="duplicate object key: schema_version"):
        reconcile_questionnaire(root, questionnaire_path, answers_path)

    answers_path.write_text("[" * 10_000 + "]" * 10_000, encoding="utf-8")
    with pytest.raises(AssessmentError, match="cannot read answers JSON"):
        reconcile_questionnaire(root, questionnaire_path, answers_path)

    answers_path.write_bytes(b" " * (256 * 1024 + 1))
    with pytest.raises(AssessmentError, match="exceeds the 256 KiB input bound"):
        reconcile_questionnaire(root, questionnaire_path, answers_path)

    valid = answer_payload(digest, {item["id"] for item in questionnaire["questions"]})
    actual = tmp_path / "actual-answers.json"
    actual.write_text(json.dumps(valid), encoding="utf-8")
    answers_path.unlink()
    answers_path.symlink_to(actual)
    with pytest.raises(AssessmentError, match="path traverses a symlink"):
        reconcile_questionnaire(root, questionnaire_path, answers_path)

    real_directory = tmp_path / "real-inputs"
    real_directory.mkdir()
    ancestor_answers = real_directory / "answers.json"
    ancestor_answers.write_text(json.dumps(valid), encoding="utf-8")
    linked_directory = tmp_path / "linked-inputs"
    linked_directory.symlink_to(real_directory, target_is_directory=True)
    with pytest.raises(AssessmentError, match="path traverses a symlink"):
        reconcile_questionnaire(root, questionnaire_path, linked_directory / "answers.json")


def test_reconcile_rejects_stale_questionnaire_and_is_deterministic(tmp_path: Path) -> None:
    root = repository(tmp_path)
    questionnaire = generate_questionnaire(root)
    questionnaire_path = tmp_path / "questionnaire.json"
    digest = write_questionnaire(questionnaire_path, questionnaire)
    answers = answer_payload(digest, {item["id"] for item in questionnaire["questions"]})
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    first = reconcile_questionnaire(root, questionnaire_path, answers_path)
    second = reconcile_questionnaire(root, questionnaire_path, answers_path)
    assert render_questionnaire_json(first) == render_questionnaire_json(second)

    (root / "README.md").write_text("changed after questions\n", encoding="utf-8")
    with pytest.raises(AssessmentError, match="questionnaire target is stale"):
        reconcile_questionnaire(root, questionnaire_path, answers_path)


def test_generation_and_reconciliation_recheck_target_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    module = __import__("agentic_application_assessor.questionnaire", fromlist=["target_identity"])
    original = module.target_identity
    calls = 0

    def mutate_on_second(path: Path) -> Any:
        nonlocal calls
        calls += 1
        if calls == 2:
            (root / "pyproject.toml").write_text("changed during generation\n", encoding="utf-8")
        return original(path)

    monkeypatch.setattr(module, "target_identity", mutate_on_second)
    with pytest.raises(AssessmentError, match="changed during questionnaire generation"):
        generate_questionnaire(root)

    monkeypatch.setattr(module, "target_identity", original)
    run("git", "restore", "pyproject.toml", cwd=root)
    questionnaire = generate_questionnaire(root)
    questionnaire_path = tmp_path / "questionnaire.json"
    digest = write_questionnaire(questionnaire_path, questionnaire)
    answers = answer_payload(digest, {item["id"] for item in questionnaire["questions"]})
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    calls = 0

    def mutate_on_final(path: Path) -> Any:
        nonlocal calls
        calls += 1
        if calls == 4:
            (root / "late.txt").write_text("changed during reconciliation\n", encoding="utf-8")
        return original(path)

    monkeypatch.setattr(module, "target_identity", mutate_on_final)
    with pytest.raises(AssessmentError, match="changed during questionnaire reconciliation"):
        reconcile_questionnaire(root, questionnaire_path, answers_path)


def test_existing_schema_1_1_provenance_and_unrelated_unknowns_are_preserved(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    first_questionnaire = generate_questionnaire(root)
    first_path = tmp_path / "first-questionnaire.json"
    first_digest = write_questionnaire(first_path, first_questionnaire)
    first_answers = answer_payload(
        first_digest, {item["id"] for item in first_questionnaire["questions"]}
    )
    first_answers_path = tmp_path / "first-answers.json"
    first_answers_path.write_text(json.dumps(first_answers), encoding="utf-8")
    accepted = reconcile_questionnaire(
        root,
        first_path,
        first_answers_path,
        accept_by="Jack Rory Staunton",
        accepted_on="2026-08-25",
    )
    accepted["unknowns"].append(
        {
            "id": "unknown.operator",
            "statement": "The production operator remains unknown.",
            "status": "open",
            "source": "owner follow-up",
            "recorded_on": "2026-08-25",
        }
    )
    accepted_path = tmp_path / "accepted-1.1.json"
    accepted_path.write_text(render_questionnaire_json(accepted), encoding="utf-8")
    original_provenance = deepcopy(accepted["application_provenance"])
    original_priorities = deepcopy(accepted["requirements"]["priorities"])

    followup = generate_questionnaire(root, accepted_path)
    assert [item["id"] for item in followup["questions"]] == ["requirements.deployment-context"]
    followup_path = tmp_path / "followup-questionnaire.json"
    followup_digest = write_questionnaire(followup_path, followup)
    followup_answers = {
        "schema_version": "1.0",
        "questionnaire_sha256": followup_digest,
        "submission": {"source": "owner follow-up", "recorded_on": "2026-08-26"},
        "answers": {
            "requirements.deployment-context": {
                "status": "answered",
                "value": "Local CLI only.",
            }
        },
        "contradictions": [],
        "unknowns": [],
    }
    followup_answers_path = tmp_path / "followup-answers.json"
    followup_answers_path.write_text(json.dumps(followup_answers), encoding="utf-8")
    draft = reconcile_questionnaire(root, followup_path, followup_answers_path, accepted_path)
    assert draft["application_provenance"] == original_provenance
    assert draft["requirements"]["priorities"] == original_priorities
    assert not any(
        item["id"] == "unknown.requirements.deployment-context" for item in draft["unknowns"]
    )
    assert any(item["id"] == "unknown.operator" for item in draft["unknowns"])


def test_custom_validators_and_draft_2020_12_schemas_agree(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    root = repository(tmp_path)
    questionnaire = generate_questionnaire(root)
    questionnaire_schema = json.loads(
        Path("schemas/application-questionnaire.schema.json").read_text(encoding="utf-8")
    )
    answers_schema = json.loads(
        Path("schemas/application-questionnaire-answers.schema.json").read_text(encoding="utf-8")
    )
    context_schema = json.loads(
        Path("schemas/application-context.schema.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator
    validator.check_schema(questionnaire_schema)
    validator(questionnaire_schema, format_checker=jsonschema.FormatChecker()).validate(
        questionnaire
    )
    assert validate_questionnaire(deepcopy(questionnaire)) == questionnaire

    questionnaire_path = tmp_path / "questionnaire.json"
    digest = write_questionnaire(questionnaire_path, questionnaire)
    answers = answer_payload(digest, {item["id"] for item in questionnaire["questions"]})
    validator(answers_schema, format_checker=jsonschema.FormatChecker()).validate(answers)
    assert validate_answers(deepcopy(answers)) == answers
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    draft = reconcile_questionnaire(root, questionnaire_path, answers_path)
    validator(context_schema, format_checker=jsonschema.FormatChecker()).validate(draft)
    assert validate_context(deepcopy(draft), require_accepted=False) == draft

    malformed = deepcopy(answers)
    malformed["answers"]["requirements.priorities"]["value"] = []
    with pytest.raises(AssessmentError):
        validate_answers(malformed)
    assert list(validator(answers_schema).iter_errors(malformed))

    mutations: list[tuple[str, Any, Any]] = [
        (
            "questionnaire revision",
            lambda value: value["target"].update(revision="bad"),
            validate_questionnaire,
        ),
        (
            "questionnaire state digest",
            lambda value: value["target"].update(state_id="sha256:bad"),
            validate_questionnaire,
        ),
        (
            "questionnaire evidence digest",
            lambda value: value["repository_evidence"][0].update(sha256="bad"),
            validate_questionnaire,
        ),
    ]
    for label, mutate, custom in mutations:
        candidate = deepcopy(questionnaire)
        mutate(candidate)
        custom_valid = True
        try:
            custom(candidate)
        except AssessmentError:
            custom_valid = False
        schema_valid = validator(questionnaire_schema).is_valid(candidate)
        assert custom_valid == schema_valid, label

    invalid_application_status = deepcopy(answers)
    invalid_application_status["answers"]["application.name"] = {
        "status": "not-applicable",
        "value": "No name",
    }
    with pytest.raises(AssessmentError):
        validate_answers(invalid_application_status)
    assert not validator(answers_schema).is_valid(invalid_application_status)

    accepted = reconcile_questionnaire(
        root,
        questionnaire_path,
        answers_path,
        accept_by="Jack Rory Staunton",
        accepted_on="2026-08-25",
    )
    invalid_context = deepcopy(accepted)
    invalid_context["requirements"]["priorities"]["status"] = "provisional"
    with pytest.raises(AssessmentError):
        validate_context(invalid_context)
    assert not validator(context_schema).is_valid(invalid_context)
    invalid_context = deepcopy(accepted)
    del invalid_context["application_provenance"]
    with pytest.raises(AssessmentError):
        validate_context(invalid_context)
    assert not validator(context_schema).is_valid(invalid_context)


def test_schema_1_0_legacy_array_contract_is_exact_and_1_1_remains_bounded(
    tmp_path: Path,
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(Path("schemas/application-context.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    legacy = json.loads(accepted_context(tmp_path).read_text(encoding="utf-8"))
    compatibility_fixtures: list[tuple[str, dict[str, Any], bool]] = []

    many_stakeholders = deepcopy(legacy)
    many_stakeholders["application"]["stakeholders"] = [
        f"stakeholder-{index}" for index in range(65)
    ]
    compatibility_fixtures.append(("65 unique stakeholders", many_stakeholders, True))

    long_component_fields = deepcopy(legacy)
    long_component_fields["components"] = [
        {
            "id": "legacy-component",
            "name": "n" * 4097,
            "responsibility": "r" * 4097,
            "paths": ["p" * 4097],
        }
    ]
    compatibility_fixtures.append(
        ("legacy unbounded component strings", long_component_fields, True)
    )

    oversized_stakeholder = deepcopy(legacy)
    oversized_stakeholder["application"]["stakeholders"] = ["s" * 4097]
    compatibility_fixtures.append(
        ("legacy bounded stakeholder string", oversized_stakeholder, False)
    )

    duplicate_paths = deepcopy(legacy)
    duplicate_paths["components"] = [
        {
            "id": "legacy-component",
            "name": "Legacy",
            "responsibility": "Compatibility",
            "paths": ["src", "src"],
        }
    ]
    compatibility_fixtures.append(("legacy unique component paths", duplicate_paths, False))

    for label, fixture, expected in compatibility_fixtures:
        assert validator.is_valid(fixture) is expected, label

    strict_root = tmp_path / "strict"
    strict_root.mkdir()
    root = repository(strict_root)
    questionnaire = generate_questionnaire(root)
    questionnaire_path = tmp_path / "strict-questionnaire.json"
    digest = write_questionnaire(questionnaire_path, questionnaire)
    answers = answer_payload(digest, {item["id"] for item in questionnaire["questions"]})
    answers_path = tmp_path / "strict-answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    accepted = reconcile_questionnaire(
        root,
        questionnaire_path,
        answers_path,
        accept_by="Jack Rory Staunton",
        accepted_on="2026-08-25",
    )
    accepted["application"]["stakeholders"] = [f"stakeholder-{index}" for index in range(65)]
    assert not validator.is_valid(accepted)
    with pytest.raises(AssessmentError):
        validate_context(accepted)


def test_question_id_uniqueness_has_bidirectional_custom_schema_parity(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    root = repository(tmp_path)
    questionnaire = generate_questionnaire(root, accepted_context(tmp_path))
    schema = json.loads(
        Path("schemas/application-questionnaire.schema.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(schema)

    def custom_valid(candidate: dict[str, Any]) -> bool:
        try:
            validate_questionnaire(candidate)
        except AssessmentError:
            return False
        return True

    assert custom_valid(deepcopy(questionnaire))
    assert validator.is_valid(questionnaire)
    for variant in ("identical", "different-content"):
        duplicate = deepcopy(questionnaire)
        repeated = deepcopy(duplicate["questions"][0])
        if variant == "different-content":
            repeated["prompt"] = "Different prompt with the same stable identifier."
        duplicate["questions"].append(repeated)
        assert not custom_valid(deepcopy(duplicate)), variant
        assert not validator.is_valid(duplicate), variant


@pytest.mark.parametrize("collection", ["contradictions", "unknowns"])
def test_context_issue_record_exact_duplicates_have_bidirectional_parity(
    tmp_path: Path, collection: str
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    root = repository(tmp_path)
    questionnaire = generate_questionnaire(root)
    questionnaire_path = tmp_path / "questionnaire.json"
    digest = write_questionnaire(questionnaire_path, questionnaire)
    answers = answer_payload(digest, {item["id"] for item in questionnaire["questions"]})
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    accepted = reconcile_questionnaire(
        root,
        questionnaire_path,
        answers_path,
        accept_by="Jack Rory Staunton",
        accepted_on="2026-08-25",
    )
    schema = json.loads(Path("schemas/application-context.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())

    def custom_valid(candidate: dict[str, Any]) -> bool:
        try:
            validate_context(candidate)
        except AssessmentError:
            return False
        return True

    assert accepted[collection]
    assert custom_valid(deepcopy(accepted))
    assert validator.is_valid(accepted)

    exact_duplicate = deepcopy(accepted)
    exact_duplicate[collection].append(deepcopy(exact_duplicate[collection][0]))
    assert not custom_valid(deepcopy(exact_duplicate))
    assert not validator.is_valid(exact_duplicate)

    same_id_distinct_record = deepcopy(accepted)
    distinct = deepcopy(same_id_distinct_record[collection][0])
    distinct["statement"] = f"A distinct {collection} record with the same stable identifier."
    same_id_distinct_record[collection].append(distinct)
    assert custom_valid(deepcopy(same_id_distinct_record))
    assert validator.is_valid(same_id_distinct_record)
