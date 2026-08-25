from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

import pytest  # pyright: ignore[reportMissingImports]

from agentic_application_assessor.assess import assess
from agentic_application_assessor.context import load_context
from agentic_application_assessor.errors import AssessmentError
from agentic_application_assessor.model import Claim, Evidence, Report, Target
from agentic_application_assessor.render import render_json, render_markdown


def run(
    *args: str, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, env=env)


def repository(tmp_path: Path, object_format: str | None = None) -> Path:
    root = tmp_path / "application"
    root.mkdir(parents=True)
    init = ["git", "init"]
    if object_format is not None:
        init.append(f"--object-format={object_format}")
    init.extend(["-b", "main"])
    run(*init, cwd=root)
    run("git", "config", "user.name", "Test", cwd=root)
    run("git", "config", "user.email", "test@example.invalid", cwd=root)
    (root / "src").mkdir()
    (root / "src/app.py").write_text("print('not executed')\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "[project]\nname='fixture'\nversion='0.1.0'\n", encoding="utf-8"
    )
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-m", "fixture", cwd=root)
    return root


def context(tmp_path: Path, component_path: str = "src") -> Path:
    path = tmp_path / "context.json"
    payload = {
        "schema_version": "1.0",
        "review": {"status": "accepted", "confirmed_on": "2026-08-24", "source": "test owner"},
        "application": {
            "name": "Fixture",
            "purpose": "Exercise deterministic assessment.",
            "stakeholders": ["maintainer"],
        },
        "components": [
            {
                "id": "core",
                "name": "Core",
                "responsibility": "Fixture behavior",
                "paths": [component_path],
            }
        ],
        "workflows": [],
        "data_assets": [],
        "quality_scenarios": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def auditor_payload(
    root: Path, *, entries: list[dict[str, Any]] | None = None, dirty: bool = False
) -> dict[str, Any]:
    revision = run("git", "rev-parse", "HEAD", cwd=root).stdout.strip()
    branch = run("git", "branch", "--show-current", cwd=root).stdout.strip() or "DETACHED"
    state_payload = {
        "name": root.name,
        "revision": revision,
        "branch": branch,
        "entries": entries or [],
    }
    state_id = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(state_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    finding = {
        "id": "security.policy",
        "category": "security",
        "status": "warn",
        "severity": "medium",
        "title": "Security policy",
        "description": "A vulnerability-reporting policy is discoverable.",
        "evidence": [{"kind": "path-presence", "path": ".", "value": "none found"}],
        "remediation": "Add SECURITY.md.",
    }
    return {
        "schema_version": "1.2",
        "tool": {"name": "agentic-repo-auditor", "version": "0.1.0"},
        "target": {
            "name": root.name,
            "revision": revision,
            "branch": branch,
            "dirty": dirty,
            "state_id": state_id,
        },
        "configuration": {
            "disabled_checks": [],
            "evidence": {"project_contract": None, "primary_check": None},
        },
        "summary": {
            "total": 1,
            "by_status": {
                "pass": 0,
                "warn": 1,
                "fail": 0,
                "not-applicable": 0,
                "unknown": 0,
            },
            "by_severity": {"info": 0, "low": 0, "medium": 1, "high": 0},
        },
        "findings": [finding],
    }


def auditor_dirty_entry(root: Path, relative: str, status: str) -> dict[str, Any]:
    path = root / relative
    metadata = path.stat()
    worktree = hashlib.sha256()
    worktree.update(
        f"file\0{metadata.st_mode & 0o7777:o}\0".encode("ascii") + relative.encode("utf-8") + b"\0"
    )
    worktree.update(path.read_bytes())
    worktree.update(b"\0")
    index = run("git", "ls-files", "--stage", "-z", "--", relative, cwd=root).stdout
    return {
        "path": relative,
        "status": status,
        "worktree": worktree.hexdigest(),
        "index": hashlib.sha256(index.encode("utf-8")).hexdigest(),
        "index_flags": [],
    }


def auditor_report(root: Path, tmp_path: Path, payload: object | None = None) -> Path:
    path = tmp_path / "auditor.json"
    path.write_text(
        json.dumps(auditor_payload(root) if payload is None else payload, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return path


BASELINE_MARKDOWN = """# Application assessment

- Tool: `agentic-application-assessor 0.1.0`
- Report schema: `1.0`
- Target: `fixture` at `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
- Branch: `main`
- Dirty outer worktree: `no`
- State identity: `sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb`

## Executive findings

- **application.purpose** [human-declared; supported]: Fixture purpose.

## Evidence coverage

| Kind | Count |
|---|---:|
| documentation | 1 |

## Contradictions

- None detected at the inspected boundary.

## Unknowns and limits

- **unknown.runtime-behavior** [unavailable] `tool-policy:test`: Runtime unavailable.

## Evidence index

- `context.application.purpose` [human-declared] `context.json#/application/purpose`: Fixture purpose.

This report does not claim runtime coverage, security approval, compliance, release readiness, or intended architecture beyond accepted declarations.
"""


def test_assessment_is_deterministic_and_explicit_about_unknowns(tmp_path: Path) -> None:
    root = repository(tmp_path)
    source = context(tmp_path)
    before = run("git", "status", "--porcelain=v1", cwd=root).stdout
    first = assess(root, source)
    second = assess(root, source)
    assert render_json(first) == render_json(second)
    assert render_markdown(first) == render_markdown(second)
    assert first.target.dirty is False
    assert {item.origin for item in first.evidence} >= {"observed", "human-declared"}
    assert any("Runtime behavior is unavailable" in item.statement for item in first.unknowns)
    assert all(item.claim_id and item.origin and item.source for item in first.unknowns)
    assert run("git", "status", "--porcelain=v1", cwd=root).stdout == before


def test_auditor_import_is_deterministic_provenance_not_claims(tmp_path: Path) -> None:
    root = repository(tmp_path)
    source = context(tmp_path)
    artifact = auditor_report(root, tmp_path)
    before = run("git", "status", "--porcelain=v1", cwd=root).stdout
    first = assess(root, source, artifact)
    second = assess(root, source, artifact)
    assert render_json(first) == render_json(second)
    assert render_markdown(first) == render_markdown(second)
    payload = first.as_dict()
    imported = payload["inputs"]["agentic_repo_auditor"]
    assert imported == {
        "path": "auditor.json",
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "schema_version": "1.2",
        "tool": {"name": "agentic-repo-auditor", "version": "0.1.0"},
        "target": auditor_payload(root)["target"],
    }
    imported_evidence = [item for item in payload["evidence"] if item["origin"] == "imported-tool"]
    assert {item["id"] for item in imported_evidence} == {
        "auditor.artifact",
        "auditor.configuration",
        "auditor.summary",
        "auditor.finding.security.policy",
        "auditor.finding.security.policy.evidence.0000",
    }
    finding = next(
        item for item in imported_evidence if item["id"] == "auditor.finding.security.policy"
    )
    assert json.loads(finding["value"]) == {
        key: value
        for key, value in auditor_payload(root)["findings"][0].items()
        if key != "evidence"
    }
    assert all(item["sha256"] == imported["sha256"] for item in imported_evidence)
    assert all(item["origin"] != "imported-tool" for item in payload["claims"])
    assert payload["coverage"]["imported-auditor-findings"] == 1
    assert payload["coverage"]["imported-auditor-finding-evidence"] == 1
    assert run("git", "status", "--porcelain=v1", cwd=root).stdout == before


def test_assessment_without_auditor_artifact_is_backward_compatible(tmp_path: Path) -> None:
    root = repository(tmp_path)
    source = context(tmp_path)
    assert render_json(assess(root, source)) == render_json(assess(root, source, None))
    assert assess(root, source).as_dict()["inputs"]["agentic_repo_auditor"] is None


def test_no_auditor_markdown_matches_the_pre_adapter_baseline() -> None:
    report = Report(
        "0.1.0",
        Target(
            "fixture",
            "a" * 40,
            "main",
            False,
            "sha256:" + "b" * 64,
        ),
        "context.json",
        "c" * 64,
        (
            Evidence(
                "context.application.purpose",
                "human-declared",
                "purpose",
                "context.json#/application/purpose",
                "Fixture purpose.",
            ),
        ),
        (
            Claim(
                "application.purpose",
                "human-declared",
                "Fixture purpose.",
                "context.json#/application/purpose",
                ("context.application.purpose",),
            ),
        ),
        (),
        (
            Claim(
                "unknown.runtime-behavior",
                "unavailable",
                "Runtime unavailable.",
                "tool-policy:test",
                (),
                "unavailable",
            ),
        ),
        {"documentation": 1},
    )
    assert render_markdown(report) == BASELINE_MARKDOWN


def test_assessment_rejects_target_mutation_between_initial_and_final_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    assessor_module = importlib.import_module("agentic_application_assessor.assess")
    original = assessor_module.target_identity
    calls = 0

    def mutating_identity(target: Path) -> Any:
        nonlocal calls
        calls += 1
        if calls == 2:
            (root / "README.md").write_text("changed during assessment\n", encoding="utf-8")
        return original(target)

    monkeypatch.setattr(assessor_module, "target_identity", mutating_identity)
    with pytest.raises(AssessmentError, match="target changed during assessment"):
        assess(root, context(tmp_path))
    assert calls == 2


def test_auditor_and_assessor_overlapping_identity_fields_must_agree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    payload = auditor_payload(root)
    payload["target"].update(branch="other", dirty=True)
    auditor_module = importlib.import_module("agentic_application_assessor.auditor")
    monkeypatch.setattr(auditor_module, "auditor_target_identity", lambda _: payload["target"])
    with pytest.raises(AssessmentError, match="collectors disagree: branch, dirty"):
        assess(root, context(tmp_path), auditor_report(root, tmp_path, payload))


def test_detached_branch_names_are_normalized_across_collectors(tmp_path: Path) -> None:
    root = repository(tmp_path)
    run("git", "checkout", "--detach", cwd=root)
    payload = auditor_payload(root)
    report = assess(root, context(tmp_path), auditor_report(root, tmp_path, payload))
    assert report.target.branch == "(detached)"
    assert report.auditor_input is not None
    assert report.auditor_input.target.branch == "DETACHED"


def test_auditor_import_accepts_real_sha256_git_repository(tmp_path: Path) -> None:
    root = repository(tmp_path, "sha256")
    payload = auditor_payload(root)
    report = assess(root, context(tmp_path), auditor_report(root, tmp_path, payload))
    assert len(report.target.revision) == 64
    assert report.auditor_input is not None
    assert report.auditor_input.target.revision == report.target.revision


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda payload: payload.update(schema_version="1.1"), "schema_version must be 1.2"),
        (
            lambda payload: payload["tool"].update(version="0.2.0"),
            "must identify agentic-repo-auditor 0.1.0",
        ),
        (
            lambda payload: payload["target"].update(revision="0" * 40),
            "target does not match the assessed repository: revision",
        ),
        (
            lambda payload: payload["summary"].update(total=2),
            "summary.total does not match findings",
        ),
        (
            lambda payload: payload["findings"][0]["evidence"][0].update(value=""),
            "evidence\\[0\\].value must be a non-empty string",
        ),
    ],
)
def test_auditor_import_rejects_incompatible_or_mismatched_reports(
    tmp_path: Path, mutator: Callable[[dict[str, Any]], None], message: str
) -> None:
    root = repository(tmp_path)
    payload = auditor_payload(root)
    mutator(payload)
    with pytest.raises(AssessmentError, match=message):
        assess(root, context(tmp_path), auditor_report(root, tmp_path, payload))


def test_auditor_import_rejects_artifact_after_target_state_changes(tmp_path: Path) -> None:
    root = repository(tmp_path)
    artifact = auditor_report(root, tmp_path)
    (root / "README.md").write_text("changed after audit\n", encoding="utf-8")
    with pytest.raises(AssessmentError, match="target does not match.*dirty, state_id"):
        assess(root, context(tmp_path), artifact)


def test_auditor_import_accepts_exact_dirty_target_state(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "README.md").write_text("intentionally dirty\n", encoding="utf-8")
    entry = auditor_dirty_entry(root, "README.md", " M")
    payload = auditor_payload(root, entries=[entry], dirty=True)
    report = assess(root, context(tmp_path), auditor_report(root, tmp_path, payload))
    imported = report.as_dict()["inputs"]["agentic_repo_auditor"]
    assert imported["target"] == payload["target"]
    assert report.target.dirty is True


def test_auditor_import_rejects_duplicate_keys_and_finding_ids(tmp_path: Path) -> None:
    root = repository(tmp_path)
    payload = auditor_payload(root)
    path = auditor_report(root, tmp_path, payload)
    raw = path.read_text(encoding="utf-8").replace(
        '"schema_version": "1.2",',
        '"schema_version": "1.2",\n  "schema_version": "1.2",',
        1,
    )
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(AssessmentError, match="duplicate object key: schema_version"):
        assess(root, context(tmp_path), path)

    payload = auditor_payload(root)
    payload["findings"].append(dict(payload["findings"][0]))
    payload["summary"]["total"] = 2
    payload["summary"]["by_status"]["warn"] = 2
    payload["summary"]["by_severity"]["medium"] = 2
    with pytest.raises(AssessmentError, match="duplicate finding IDs: security.policy"):
        assess(root, context(tmp_path), auditor_report(root, tmp_path, payload))


def test_auditor_import_rejects_symlink_oversize_and_deep_json(tmp_path: Path) -> None:
    root = repository(tmp_path)
    actual = auditor_report(root, tmp_path)
    linked = tmp_path / "linked-auditor.json"
    linked.symlink_to(actual)
    with pytest.raises(AssessmentError, match="traverses a symlink"):
        assess(root, context(tmp_path), linked)

    actual.write_bytes(b" " * (2 * 1024 * 1024 + 1))
    with pytest.raises(AssessmentError, match="exceeds the 2 MiB adapter bound"):
        assess(root, context(tmp_path), actual)

    actual.write_text("[" * 10_000 + "]" * 10_000, encoding="utf-8")
    with pytest.raises(AssessmentError, match="cannot read Auditor report JSON"):
        assess(root, context(tmp_path), actual)


def test_declared_missing_component_path_is_a_contradiction(tmp_path: Path) -> None:
    report = assess(repository(tmp_path), context(tmp_path, "missing"))
    assert report.contradictions[0].claim_id == "contradiction.component.core.missing-paths"
    assert report.contradictions[0].source == "context.json#/components/0/paths"
    assert (
        next(
            item for item in report.claims if item.claim_id == "architecture.component.core"
        ).status
        == "contradicted"
    )


def test_context_is_strict_and_rejects_symlink(tmp_path: Path) -> None:
    source = context(tmp_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AssessmentError, match="unsupported properties"):
        load_context(source)
    actual = context(tmp_path)
    linked = tmp_path / "linked.json"
    linked.symlink_to(actual)
    with pytest.raises(AssessmentError, match="traverses a symlink"):
        load_context(linked)


def test_context_rejects_invalid_date_and_unnormalized_identifier(tmp_path: Path) -> None:
    source = context(tmp_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["review"]["confirmed_on"] = "not-a-date"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AssessmentError, match="RFC 3339 full-date"):
        load_context(source)
    payload["review"]["confirmed_on"] = "2026-08-24"
    payload["components"][0]["id"] = " core "
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AssessmentError, match="surrounding whitespace"):
        load_context(source)


def test_recognized_target_symlink_fails_closed(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "outside").symlink_to(tmp_path / "context.json")
    run("git", "add", "outside", cwd=root)
    run("git", "commit", "-m", "symlink", cwd=root)
    # Only recognized paths are read; rename the symlink to an entrypoint to force inspection.
    (root / "outside").rename(root / "main.py")
    run("git", "add", "-A", cwd=root)
    run("git", "commit", "-m", "recognized symlink", cwd=root)
    with pytest.raises(AssessmentError, match="is a symlink"):
        assess(root, context(tmp_path))


def test_repository_filter_and_fsmonitor_are_not_executed(tmp_path: Path) -> None:
    root = repository(tmp_path)
    sentinel = tmp_path / "fired"
    helper = tmp_path / "helper.sh"
    helper.write_text(f"#!/bin/sh\ntouch '{sentinel}'\ncat\n", encoding="utf-8")
    helper.chmod(0o755)
    (root / ".gitattributes").write_text("*.py filter=evil\n", encoding="utf-8")
    run("git", "add", ".gitattributes", cwd=root)
    run("git", "commit", "-m", "attributes", cwd=root)
    run("git", "config", "filter.evil.clean", str(helper), cwd=root)
    run("git", "config", "core.fsmonitor", str(helper), cwd=root)
    (root / "src/app.py").write_text("changed\n", encoding="utf-8")
    assess(root, context(tmp_path))
    assert not sentinel.exists()


def test_target_must_be_exact_repository_root(tmp_path: Path) -> None:
    root = repository(tmp_path)
    with pytest.raises(AssessmentError, match="exact Git repository root"):
        assess(root / "src", context(tmp_path))


def test_symlinked_target_root_is_rejected(tmp_path: Path) -> None:
    root = repository(tmp_path)
    linked = tmp_path / "linked-repository"
    linked.symlink_to(root, target_is_directory=True)
    with pytest.raises(AssessmentError, match="target path traverses a symlink"):
        assess(linked, context(tmp_path))


def test_detached_head_has_explicit_branch_identity(tmp_path: Path) -> None:
    root = repository(tmp_path)
    run("git", "checkout", "--detach", cwd=root)
    assert assess(root, context(tmp_path)).target.branch == "(detached)"


def test_submodule_state_fails_closed(tmp_path: Path) -> None:
    child = repository(tmp_path / "child-boundary")
    root = repository(tmp_path / "outer-boundary")
    run(
        "git",
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(child),
        "vendor/child",
        cwd=root,
    )
    run("git", "commit", "-m", "submodule", cwd=root)
    with pytest.raises(AssessmentError, match="submodules are unsupported"):
        assess(root, context(tmp_path))


def test_embedded_repository_state_fails_closed(tmp_path: Path) -> None:
    root = repository(tmp_path / "outer-boundary")
    nested = root / "vendor/nested"
    nested.mkdir(parents=True)
    run("git", "init", "-b", "main", cwd=nested)
    run("git", "config", "user.name", "Test", cwd=nested)
    run("git", "config", "user.email", "test@example.invalid", cwd=nested)
    (nested / "README.md").write_text("nested\n", encoding="utf-8")
    run("git", "add", ".", cwd=nested)
    run("git", "commit", "-m", "nested", cwd=nested)
    with pytest.raises(AssessmentError, match="embedded Git repositories are unsupported"):
        assess(root, context(tmp_path))


def test_local_git_config_includes_fail_closed(tmp_path: Path) -> None:
    root = repository(tmp_path)
    included = tmp_path / "outside.gitconfig"
    included.write_text("[core]\n\tfsmonitor = /tmp/untrusted-helper\n", encoding="utf-8")
    run("git", "config", "--local", "include.path", str(included), cwd=root)
    with pytest.raises(AssessmentError, match="config includes are unsupported"):
        assess(root, context(tmp_path))


def test_state_identity_binds_dirty_and_untracked_file_content(tmp_path: Path) -> None:
    root = repository(tmp_path)
    source = context(tmp_path)
    clean = assess(root, source)
    note = root / "notes.bin"
    note.write_bytes(b"first")
    first_untracked = assess(root, source)
    note.write_bytes(b"second")
    second_untracked = assess(root, source)
    assert (
        len(
            {
                clean.target.state_id,
                first_untracked.target.state_id,
                second_untracked.target.state_id,
            }
        )
        == 3
    )
    (root / "README.md").write_text("first dirty value\n", encoding="utf-8")
    first_dirty = assess(root, source)
    (root / "README.md").write_text("second dirty value\n", encoding="utf-8")
    second_dirty = assess(root, source)
    assert first_dirty.target.state_id != second_dirty.target.state_id
    assert render_json(first_dirty) != render_json(second_dirty)


def test_caller_git_environment_cannot_redirect_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actual = repository(tmp_path / "actual-boundary")
    other = repository(tmp_path / "other-boundary")
    (other / "other.txt").write_text("different revision\n", encoding="utf-8")
    run("git", "add", "other.txt", cwd=other)
    run("git", "commit", "-m", "different", cwd=other)
    expected = run("git", "rev-parse", "HEAD", cwd=actual).stdout.strip()
    other_revision = run("git", "rev-parse", "HEAD", cwd=other).stdout.strip()
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    report = assess(actual, context(tmp_path))
    assert report.target.revision == expected
    assert report.target.revision != other_revision
