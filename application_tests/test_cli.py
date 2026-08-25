from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest  # pyright: ignore[reportMissingImports]


@pytest.mark.integration
def test_cli_json_and_error_contract(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    (root / "README.md").write_text("# App\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True)
    context = tmp_path / "context.json"
    context.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "review": {"status": "accepted", "confirmed_on": "2026-08-24", "source": "owner"},
                "application": {
                    "name": "App",
                    "purpose": "Test the CLI.",
                    "stakeholders": ["maintainer"],
                },
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_application_assessor",
            "assess",
            str(root),
            "--context",
            str(context),
            "--format",
            "json",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert json.loads(result.stdout)["tool"]["name"] == "agentic-application-assessor"
    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_application_assessor",
            "assess",
            str(root / "missing"),
            "--context",
            str(context),
        ],
        check=False,
        text=True,
        stderr=subprocess.PIPE,
    )
    assert bad.returncode == 2
    assert bad.stderr.startswith("agentic-application-assessor:")


def test_cli_deeply_nested_context_fails_without_traceback(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    (root / "README.md").write_text("# App\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True)
    context = tmp_path / "nested.json"
    context.write_text("[" * 10_000 + "]" * 10_000, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_application_assessor",
            "assess",
            str(root),
            "--context",
            str(context),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("agentic-application-assessor: cannot read context JSON:")
    assert "Traceback" not in result.stderr


def test_cli_invalid_auditor_artifact_fails_closed_without_traceback(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    (root / "README.md").write_text("# App\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True)
    context = tmp_path / "context.json"
    context.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "review": {"status": "accepted", "confirmed_on": "2026-08-24", "source": "owner"},
                "application": {
                    "name": "App",
                    "purpose": "Test the CLI.",
                    "stakeholders": ["maintainer"],
                },
            }
        ),
        encoding="utf-8",
    )
    artifact = tmp_path / "auditor.json"
    artifact.write_text('{"schema_version":"1.2","schema_version":"1.2"}\n', encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_application_assessor",
            "assess",
            str(root),
            "--context",
            str(context),
            "--auditor-report",
            str(artifact),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "duplicate object key: schema_version" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.integration
def test_cli_questionnaire_draft_and_explicit_acceptance(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname='fixture-cli'\nversion='0.1.0'\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True)

    generated = subprocess.run(
        [sys.executable, "-m", "agentic_application_assessor", "questionnaire", str(root)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    questionnaire_path = tmp_path / "questionnaire.json"
    questionnaire_path.write_text(generated.stdout, encoding="utf-8")
    questionnaire = json.loads(generated.stdout)
    question_ids = {item["id"] for item in questionnaire["questions"]}
    values = {
        "application.name": {"status": "answered", "value": "Fixture CLI"},
        "application.purpose": {"status": "answered", "value": "Exercise the CLI."},
        "application.stakeholders": {"status": "answered", "value": ["owner"]},
        "requirements.priorities": {"status": "answered", "value": ["correctness"]},
        "requirements.constraints": {"status": "answered", "value": ["local-only"]},
        "requirements.risk-tolerance": {"status": "answered", "value": "low"},
        "requirements.deployment-context": {"status": "unknown"},
        "requirements.evidence-expectations": {"status": "answered", "value": ["repeatable"]},
    }
    answers = {
        "schema_version": "1.0",
        "questionnaire_sha256": hashlib.sha256(generated.stdout.encode()).hexdigest(),
        "submission": {"source": "CLI test owner", "recorded_on": "2026-08-25"},
        "answers": {key: value for key, value in values.items() if key in question_ids},
        "contradictions": [],
        "unknowns": [],
    }
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    draft = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_application_assessor",
            "reconcile",
            str(root),
            "--questionnaire",
            str(questionnaire_path),
            "--answers",
            str(answers_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert json.loads(draft.stdout)["review"]["status"] == "draft"
    accepted = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_application_assessor",
            "reconcile",
            str(root),
            "--questionnaire",
            str(questionnaire_path),
            "--answers",
            str(answers_path),
            "--accept-by",
            "Jack Rory Staunton",
            "--accepted-on",
            "2026-08-25",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert json.loads(accepted.stdout)["review"]["accepted_by"] == "Jack Rory Staunton"


def test_cli_reconcile_error_is_sanitized(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_application_assessor",
            "reconcile",
            str(tmp_path),
            "--questionnaire",
            str(tmp_path / "missing-questionnaire.json"),
            "--answers",
            str(tmp_path / "missing-answers.json"),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("agentic-application-assessor:")
    assert "Traceback" not in result.stderr
