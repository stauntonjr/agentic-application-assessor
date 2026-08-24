from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest  # pyright: ignore[reportMissingImports]

from agentic_application_assessor.assess import assess
from agentic_application_assessor.context import load_context
from agentic_application_assessor.errors import AssessmentError
from agentic_application_assessor.render import render_json, render_markdown


def run(
    *args: str, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, env=env)


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "application"
    root.mkdir(parents=True)
    run("git", "init", "-b", "main", cwd=root)
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
