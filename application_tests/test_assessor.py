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
    assert any("Runtime behavior is unavailable" in item for item in first.unknowns)
    assert run("git", "status", "--porcelain=v1", cwd=root).stdout == before


def test_declared_missing_component_path_is_a_contradiction(tmp_path: Path) -> None:
    report = assess(repository(tmp_path), context(tmp_path, "missing"))
    assert report.contradictions == ("component core declares absent paths: missing",)
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
