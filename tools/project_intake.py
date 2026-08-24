#!/usr/bin/env python3
"""Collect, merge, and render durable project intake records."""

from __future__ import annotations

import argparse
import copy
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from .common import get_nested, load_json, repository_root, set_nested, utc_now, write_json
except ImportError:  # Direct script execution.
    from common import get_nested, load_json, repository_root, set_nested, utc_now, write_json


MODES = ("new", "adopt", "refresh", "gap-only")
ALLOWED_PREFIXES = ("project.", "intent.", "constraints.", "engineering.", "autonomy.")
PROFILE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GENERATED_PARTS = {
    ".git",
    ".harness",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
GENERATED_NAMES = {".coverage"}
QUESTION_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("project.name", "Project name", False),
    ("project.summary", "What does it do, for whom, and why", False),
    ("project.repository", "GitHub repository as OWNER/REPOSITORY", False),
    ("project.profile", "Profile: generic, python-data, web-service, or agent-system", False),
    ("intent.users", "Primary users (comma-separated)", True),
    ("intent.outcomes", "Desired outcomes (comma-separated)", True),
    ("intent.success_metrics", "Measurable success criteria (comma-separated)", True),
    ("intent.in_scope", "In-scope capabilities (comma-separated)", True),
    ("intent.out_of_scope", "Explicit exclusions (comma-separated)", True),
    ("constraints.data_classification", "Data classification", False),
    ("constraints.deployment", "Deployment target or none", False),
    ("constraints.licenses", "Accepted project license or licenses (comma-separated)", True),
    ("engineering.languages", "Languages (comma-separated)", True),
    ("engineering.build_commands", "Build commands (comma-separated)", True),
    ("engineering.test_commands", "Test commands (comma-separated)", True),
    (
        "engineering.command_contract.primary_check",
        "One command that runs the authoritative local/CI check",
        False,
    ),
    (
        "engineering.command_contract.bootstrap",
        "Reproducible dependency/bootstrap command or not-applicable with reason",
        False,
    ),
    (
        "engineering.command_contract.format_check",
        "Format-check command or not-applicable with reason",
        False,
    ),
    ("engineering.command_contract.lint", "Lint command or not-applicable with reason", False),
    (
        "engineering.command_contract.typecheck",
        "Type-check command or not-applicable with reason",
        False,
    ),
    ("engineering.command_contract.unit", "Unit-test command or not-applicable with reason", False),
    (
        "engineering.command_contract.integration",
        "Integration-test command or not-applicable with reason",
        False,
    ),
    (
        "engineering.command_contract.package_smoke",
        "Clean package/build/entrypoint smoke command or not-applicable with reason",
        False,
    ),
    ("engineering.quality.dependency_lock", "Dependency lockfile or conditional policy", False),
    (
        "engineering.quality.coverage_policy",
        "Coverage ratchet, threshold, or explicit exception policy",
        False,
    ),
    ("engineering.versioning.strategy", "Versioning: semver, calver, independent, or none", False),
    ("engineering.versioning.current", "Initial product version", False),
    (
        "engineering.versioning.public_contract",
        "Versioned public contracts: API, CLI, config, schema, artifacts, or user behavior",
        True,
    ),
    (
        "engineering.versioning.source",
        "Canonical product-version source, for example pyproject.toml:project.version",
        False,
    ),
    ("autonomy.level", "Autonomy level: supervised, bounded, or high", False),
)
ESSENTIAL_FIELDS = (
    "project.name",
    "project.summary",
    "project.repository",
    "project.profile",
    "intent.users",
    "intent.outcomes",
    "intent.success_metrics",
    "intent.in_scope",
    "intent.out_of_scope",
    "constraints.data_classification",
    "constraints.deployment",
    "constraints.licenses",
    "engineering.languages",
    "engineering.test_commands",
    "engineering.command_contract.primary_check",
    "engineering.command_contract.bootstrap",
    "engineering.command_contract.format_check",
    "engineering.command_contract.lint",
    "engineering.command_contract.typecheck",
    "engineering.command_contract.unit",
    "engineering.command_contract.integration",
    "engineering.command_contract.package_smoke",
    "engineering.quality.dependency_lock",
    "engineering.quality.coverage_policy",
    "engineering.versioning.strategy",
    "autonomy.level",
)


def normalize_answer(value: Any, *, source: str, recorded_at: str) -> dict[str, Any]:
    if isinstance(value, dict) and "value" in value:
        answer = copy.deepcopy(value)
        answer.setdefault("status", "confirmed")
        answer.setdefault("source", source)
        answer.setdefault("recorded_at", recorded_at)
        return answer
    return {
        "value": value,
        "status": "confirmed",
        "source": source,
        "recorded_at": recorded_at,
    }


def load_answers(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = load_json(path)
    if "answers" in data and isinstance(data["answers"], dict):
        return data["answers"]
    if not isinstance(data, dict):
        raise TypeError("answers file must contain an object")
    return data


def is_resolved(value: Any) -> bool:
    if isinstance(value, str) and value.startswith("not-applicable:"):
        return bool(value.partition(":")[2].strip())
    return value not in (None, "", "TBD", [], {})


def interactive_answers(
    project: dict[str, Any],
    existing: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    print(
        "I will inspect known values and ask only material gaps. "
        "Leave an answer blank to retain the current value or mark it TBD."
    )
    for field, question, is_list in QUESTION_FIELDS:
        prior_record = existing.get(field, {})
        prior = prior_record.get("value") if isinstance(prior_record, dict) else None
        current = prior if is_resolved(prior) else get_nested(project, field)
        if mode == "gap-only" and is_resolved(current):
            continue
        suffix = f" [{current}]" if is_resolved(current) else ""
        response = input(f"{question}{suffix}: ").strip()
        if not response:
            if is_resolved(current):
                continue
            value: Any = []
            status = "TBD"
        else:
            value = (
                [item.strip() for item in response.split(",") if item.strip()]
                if is_list
                else response
            )
            status = "confirmed"
        answers[field] = {
            "value": value,
            "status": status,
            "source": "user-interview",
            "recorded_at": utc_now(),
        }
    return answers


def apply_profile_defaults(
    project: dict[str, Any], profile: dict[str, Any], *, override: bool = False
) -> None:
    for dotted_key, value in profile.get("defaults", {}).items():
        if override or not is_resolved(get_nested(project, dotted_key)):
            set_nested(project, dotted_key, copy.deepcopy(value))


def render(
    base_project: dict[str, Any],
    planning: dict[str, Any],
    answers: dict[str, Any],
    *,
    profile_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    project = copy.deepcopy(base_project)
    requested_profile = answers.get("project.profile")
    if isinstance(requested_profile, dict):
        requested_profile = requested_profile.get("value")
    if is_resolved(requested_profile):
        set_nested(project, "project.profile", copy.deepcopy(requested_profile))

    profile_id = get_nested(project, "project.profile", "generic")
    if not isinstance(profile_id, str) or not PROFILE_ID.fullmatch(profile_id):
        raise ValueError(f"invalid project profile ID: {profile_id}")
    profiles = profile_root or Path(__file__).resolve().parents[1] / "harness/profiles"
    profile_path = profiles / f"{profile_id}.json"
    if not profile_path.is_file():
        raise ValueError(f"unknown project profile: {profile_id}")
    apply_profile_defaults(
        project,
        load_json(profile_path),
        override=bool(base_project.get("template_mode", False)),
    )

    for dotted_key, record in answers.items():
        if dotted_key.startswith(ALLOWED_PREFIXES):
            value = record.get("value") if isinstance(record, dict) else record
            set_nested(project, dotted_key, copy.deepcopy(value))

    missing = [field for field in ESSENTIAL_FIELDS if not is_resolved(get_nested(project, field))]
    if get_nested(project, "engineering.quality.dependency_lock") == "required-if-dependencies":
        missing.append("engineering.quality.dependency_lock")
    strategy = get_nested(project, "engineering.versioning.strategy")
    if strategy == "none":
        set_nested(project, "engineering.versioning.current", "not-applicable")
        set_nested(project, "engineering.versioning.public_contract", [])
        set_nested(project, "engineering.versioning.source", "not-applicable")
    else:
        for field in (
            "engineering.versioning.current",
            "engineering.versioning.public_contract",
            "engineering.versioning.source",
        ):
            if not is_resolved(get_nested(project, field)):
                missing.append(field)
    project["template_mode"] = bool(missing)
    project["project"]["status"] = "draft" if missing else "active"
    project["project"]["lifecycle"] = project["project"].get("lifecycle") or "new"
    project["open_questions"] = [f"Resolve {field}" for field in missing]

    rendered_planning = copy.deepcopy(planning)
    repository = get_nested(project, "project.repository")
    if isinstance(repository, str) and "/" in repository and repository != "OWNER/REPOSITORY":
        owner = repository.split("/", 1)[0]
        rendered_planning["repository"] = repository
        rendered_planning["project"]["owner"] = owner
        if repository.lower() != str(planning.get("repository", "")).lower():
            canonical = rendered_planning["project"].get("canonical_source", {})
            rendered_planning["project"]["topology"] = "dedicated"
            rendered_planning["project"]["number"] = None
            rendered_planning["project"]["title"] = f"{project['project']['name']} Roadmap"
            rendered_planning["project"]["bootstrap"] = {
                "method": "copy",
                "source_owner": canonical.get("owner"),
                "source_number": canonical.get("number"),
                "link_repository": True,
            }
    return project, rendered_planning, missing


def render_charter(project: dict[str, Any], intake_source: str) -> str:
    intent = project["intent"]
    constraints = project["constraints"]
    engineering = project["engineering"]
    versioning = engineering["versioning"]
    if versioning["strategy"] == "none":
        product_version_contract = "- Product versioning: none (no versioned product contract)"
    else:
        product_version_contract = (
            f"- Product versioning: {versioning['strategy']} at {versioning['current']}\n"
            f"- Version source: {versioning['source']}\n"
            f"- Public contract: {', '.join(versioning['public_contract']) or 'TBD'}"
        )

    def bullets(values: Any) -> str:
        if not values:
            return "- TBD"
        if not isinstance(values, list):
            values = [values]
        return "\n".join(f"- {value}" for value in values)

    return f"""# Project charter

Status: {project["project"]["status"]}

## Purpose

{project["project"]["summary"]}

Primary users:

{bullets(intent.get("users"))}

## Outcomes and success measures

Desired outcomes:

{bullets(intent.get("outcomes"))}

Success measures:

{bullets(intent.get("success_metrics"))}

## Scope

### In

{bullets(intent.get("in_scope"))}

### Out

{bullets(intent.get("out_of_scope"))}

## Constraints

- Security: {", ".join(constraints.get("security", [])) or "TBD"}
- Data classification: {constraints.get("data_classification", "TBD")}
- Deployment: {constraints.get("deployment", "TBD")}
- Budget: {constraints.get("budget", "TBD")}
- Licensing: {", ".join(constraints.get("licenses", [])) or "TBD"}

## Engineering and release contract

- Primary check: {engineering["command_contract"]["primary_check"]}
- Dependency lock: {engineering["quality"]["dependency_lock"]}
- Coverage policy: {engineering["quality"]["coverage_policy"]}
{product_version_contract}
- Harness version: {project["harness_version"]}

## Authority

- Autonomy level: {project["autonomy"]["level"]}
- Network writes: {project["autonomy"]["network_writes"]}
- Destructive actions: {project["autonomy"]["destructive_actions"]}
- Release: {project["autonomy"]["release"]}
- Policy changes: {project["autonomy"]["policy_changes"]}

Generated from `harness/project.yaml` and {intake_source}.
"""


def copy_template(source: Path, target: Path) -> None:
    safe_target_path(target, "harness/project.yaml")
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(
            *GENERATED_PARTS,
            *GENERATED_NAMES,
            "*.egg-info",
            "*.pyc",
        ),
    )


def ownership_for(path: str, policy: dict[str, Any]) -> str:
    for rule in policy.get("rules", []):
        if fnmatch.fnmatchcase(path, rule["pattern"]):
            return str(rule["ownership"])
    return str(policy.get("default_ownership", "project-owned"))


def safe_target_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if not relative or path.is_absolute() or ".." in path.parts or str(path) in {".", ""}:
        raise ValueError(f"path must stay inside the target repository: {relative}")
    lexical_root = root if root.is_absolute() else Path(os.path.abspath(root))
    current_root = Path(lexical_root.anchor)
    for part in lexical_root.parts[1:]:
        current_root = current_root / part
        if current_root.is_symlink():
            raise ValueError(f"refusing symlink target repository: {root}")
        if current_root.exists() and not current_root.is_dir():
            if current_root == lexical_root:
                raise ValueError(f"target repository must be a directory: {root}")
            raise ValueError(f"refusing non-directory target ancestor: {root}")
    candidate = root / path
    current = root
    for index, part in enumerate(path.parts):
        current = current / part
        if current.is_symlink():
            raise ValueError(f"refusing target path through symlink: {relative}")
        if index < len(path.parts) - 1 and current.exists() and not current.is_dir():
            raise ValueError(f"refusing target path through non-directory ancestor: {relative}")
    return candidate


def non_overwriting_output(root: Path, canonical: str, proposal: str | None = None) -> Path:
    canonical_path = safe_target_path(root, canonical)
    if not canonical_path.exists():
        return canonical_path
    if proposal is None:
        raise ValueError(f"refusing to overwrite existing target path: {canonical}")
    proposal_path = safe_target_path(root, proposal)
    if proposal_path.exists():
        raise ValueError(f"refusing to overwrite existing target paths: {canonical} and {proposal}")
    return proposal_path


def adoption_output_paths(target: Path) -> dict[str, Path]:
    return {
        "project": non_overwriting_output(target, "harness/project.yaml"),
        "intake": non_overwriting_output(
            target,
            "harness/intake.json",
            "harness/intake.harness-proposed.json",
        ),
        "planning": non_overwriting_output(
            target,
            ".github/planning.json",
            ".github/planning.harness-proposed.json",
        ),
        "charter": non_overwriting_output(
            target,
            "docs/project/charter.md",
            "docs/project/charter.harness-proposed.md",
        ),
        "adoption_report": non_overwriting_output(
            target,
            "docs/project/adoption-gaps.md",
            "docs/project/adoption-gaps.harness-proposed.md",
        ),
    }


def plan_adoption(
    source: Path, target: Path
) -> tuple[dict[str, list[str]], list[tuple[Path, Path, str]]]:
    policy = load_json(source / "harness/ownership.json")
    result: dict[str, list[str]] = {
        "copied": [],
        "upstream_collisions": [],
        "adoption_deferred": [],
        "merge_required_existing": [],
        "merge_required_missing": [],
    }
    copy_plan: list[tuple[Path, Path, str]] = []
    for source_path in sorted(source.rglob("*")):
        relative = source_path.relative_to(source)
        if (
            any(part in GENERATED_PARTS or part.endswith(".egg-info") for part in relative.parts)
            or source_path.name in GENERATED_NAMES
            or source_path.suffix == ".pyc"
        ):
            continue
        if source_path.is_dir():
            continue
        relative_text = relative.as_posix()
        ownership = ownership_for(relative_text, policy)
        target_path = safe_target_path(target, relative_text)
        if relative_text.startswith("tests/"):
            result["adoption_deferred"].append(relative_text)
            continue
        if ownership == "project-owned":
            continue
        if ownership == "merge-required":
            key = "merge_required_existing" if target_path.exists() else "merge_required_missing"
            result[key].append(relative_text)
            continue
        if target_path.exists():
            result["upstream_collisions"].append(relative_text)
            continue
        copy_plan.append((source_path, target_path, relative_text))
        result["copied"].append(relative_text)
    return result, copy_plan


def copy_missing_for_adoption(source: Path, target: Path) -> dict[str, list[str]]:
    result, copy_plan = plan_adoption(source, target)
    for source_path, target_path, _relative_text in copy_plan:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
    return result


def not_evaluated_quality(command: str | None = None) -> dict[str, Any]:
    return {
        "status": "not-evaluated",
        "command": command,
        "baseline_exit_code": None,
        "adopted_exit_code": None,
        "incompatible_paths": [],
        "diagnostic": "application quality compatibility was not evaluated",
    }


def run_adoption_check(root: Path, argv: list[str], *, timeout: int) -> dict[str, Any]:
    try:
        result = subprocess.run(
            argv,
            cwd=root,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"exit_code": None, "output": "", "error": f"timed out after {timeout}s"}
    except OSError as exc:
        return {"exit_code": None, "output": "", "error": str(exc)}
    return {
        "exit_code": result.returncode,
        "output": f"{result.stdout}\n{result.stderr}",
        "error": None,
    }


def adoption_quality_evidence(
    command: str,
    copied_paths: list[str],
    baseline: dict[str, Any],
    adopted: dict[str, Any],
) -> dict[str, Any]:
    output = str(adopted.get("output", "")).replace("\\", "/")
    incompatible_paths = sorted(path for path in copied_paths if path in output)
    baseline_exit = baseline.get("exit_code")
    adopted_exit = adopted.get("exit_code")
    if baseline.get("error") or adopted.get("error"):
        status = "indeterminate"
        diagnostic = baseline.get("error") or adopted.get("error")
    elif baseline_exit != 0:
        status = "indeterminate"
        diagnostic = "application check did not pass before harness files were copied"
    elif adopted_exit == 0:
        status = "compatible"
        diagnostic = "application check passed before and after harness files were copied"
    else:
        status = "incompatible"
        diagnostic = (
            "application check passed before adoption and failed after harness files were copied"
        )
    return {
        "status": status,
        "command": command,
        "baseline_exit_code": baseline_exit,
        "adopted_exit_code": adopted_exit,
        "incompatible_paths": incompatible_paths,
        "diagnostic": str(diagnostic),
    }


def adoption_gap_report(dispositions: dict[str, list[str]], quality: dict[str, Any]) -> str:
    def lines(key: str) -> str:
        return "\n".join(f"- `{path}`" for path in dispositions.get(key, [])) or "- None."

    command = quality.get("command") or "not supplied"
    paths = quality.get("incompatible_paths", [])
    quality_paths = "\n".join(f"- `{path}`" for path in paths) or "- None identified."

    return f"""# Harness adoption gaps

The adopter preserved every pre-existing file. It copied only paths classified as `upstream-owned` by `harness/ownership.json`. Licensing, policy, CI, planning, dependency, and other `merge-required` surfaces were not activated automatically.

## Upstream-owned collisions

These application paths collide with harness internals. The application copy remains authoritative until a deliberate namespace or merge decision is made:

{lines("upstream_collisions")}

## Adoption-deferred paths

These upstream paths were not copied because activating a harness test suite inside an existing application's discovery namespace can change or break its authoritative test command. Reconcile them into a separate harness-test boundary before adoption is active:

{lines("adoption_deferred")}

## Existing merge-required paths

These existing application paths require a deliberate three-way reconciliation:

{lines("merge_required_existing")}

## Missing merge-required paths

These template paths were intentionally not copied into the application. Review the pinned upstream revision before adding or adapting any of them:

{lines("merge_required_missing")}

## Application quality discovery

- Status: `{quality.get("status")}`.
- Exact application command: `{command}`.
- Baseline exit code: `{quality.get("baseline_exit_code")}`.
- Adopted-overlay exit code: `{quality.get("adopted_exit_code")}`.
- Diagnostic: {quality.get("diagnostic")}.

Copied harness paths named by the application command:

{quality_paths}

No application quality configuration, dependency lock, or ignore rule was changed. A check is run
only when the adopter explicitly supplies `--adoption-check`. A missing, indeterminate, or
incompatible result keeps harness adoption provisional.

## Required review

1. Merge the context-readiness, source-precedence, role, loop, safety, verification, and skill-routing rules into the authoritative `AGENTS.md`.
2. Reconcile existing build and test entrypoints with `Makefile` and the harness workflow.
3. Reconcile product version, public contract, dependency lock, coverage policy, and release notes with the existing package or deployment system.
4. Reconcile existing GitHub templates, security settings, workflows, and planning state; never overwrite live conventions blindly.
5. Confirm ignored local runtime paths include `.harness/runs/`, `.harness/challenge-results/`, and `.harness/preferences.local.json`.
6. Resolve every upstream-owned collision before relying on copied tools or tests.
7. Run `python3 tools/harness_check.py` and resolve every error before calling adoption complete.
"""


def adoption_gap_count(dispositions: dict[str, list[str]]) -> int:
    return sum(
        len(dispositions[key])
        for key in (
            "upstream_collisions",
            "adoption_deferred",
            "merge_required_existing",
            "merge_required_missing",
        )
    )


def mark_adoption_state(
    project: dict[str, Any],
    intake: dict[str, Any],
    dispositions: dict[str, list[str]],
    quality: dict[str, Any] | None = None,
) -> int:
    unresolved = adoption_gap_count(dispositions)
    quality = quality or {
        "status": "compatible",
        "command": None,
        "baseline_exit_code": 0,
        "adopted_exit_code": 0,
        "incompatible_paths": [],
        "diagnostic": "compatibility supplied by the caller",
    }
    adoption_ready = unresolved == 0 and quality.get("status") == "compatible"
    context_ready = not intake.get("missing_essential_fields")
    intake["context_readiness"] = "sufficient" if context_ready else "provisional"
    project["project"]["lifecycle"] = "adopt"
    project["project"]["status"] = "active" if adoption_ready and context_ready else "provisional"
    intake["adoption"] = {
        "status": project["project"]["status"],
        "reconciliation_status": "complete" if adoption_ready else "provisional",
        "gap_count": unresolved,
        "dispositions": {key: len(value) for key, value in dispositions.items() if key != "copied"},
        "quality": quality,
    }
    if unresolved:
        project["open_questions"].append(
            f"Resolve {unresolved} harness adoption reconciliation gaps"
        )
    if quality.get("status") != "compatible":
        project["open_questions"].append(
            "Evaluate copied harness paths with the application's authoritative quality command"
        )
    return unresolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", type=Path)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--mode", choices=MODES, default="new")
    parser.add_argument("--target", type=Path)
    parser.add_argument("--apply", action="store_true", help="Write rendered artifacts")
    parser.add_argument(
        "--adoption-check",
        help="Explicit non-mutating application command to run before and after adopt apply",
    )
    parser.add_argument(
        "--adoption-check-timeout",
        type=int,
        default=300,
        help="Seconds allowed for each explicit adoption check (default: 300)",
    )
    args = parser.parse_args()

    if args.adoption_check_timeout < 1:
        parser.error("--adoption-check-timeout must be positive")
    try:
        adoption_check_argv = shlex.split(args.adoption_check) if args.adoption_check else None
    except ValueError as exc:
        parser.error(f"invalid --adoption-check: {exc}")
    if adoption_check_argv == []:
        parser.error("--adoption-check must contain a command")

    source = repository_root(Path(__file__).parent)
    target = Path(os.path.abspath(args.target)) if args.target else source
    source_project = load_json(source / "harness/project.yaml")
    if target != source and not source_project.get("template_mode", False):
        print(
            "error: cross-repository intake must run from the template-mode repository; "
            "run project_intake.py inside the intended application repository",
            file=sys.stderr,
        )
        return 2
    target_exists = (target / "harness/project.yaml").is_file()
    adopting_existing = (
        target != source and target.exists() and not target_exists and args.mode == "adopt"
    )
    if args.adoption_check and not adopting_existing:
        print(
            "error: --adoption-check is supported only when adopting an existing repository",
            file=sys.stderr,
        )
        return 2
    if target.exists() and not target_exists and target != source and not adopting_existing:
        print(f"error: target exists but is not a harness repository: {target}", file=sys.stderr)
        print(
            "hint: use --mode adopt to preserve and overlay an existing repository", file=sys.stderr
        )
        return 2

    base_root = target if target_exists else source
    project = load_json(base_root / "harness/project.yaml")
    planning = load_json(base_root / ".github/planning.json")
    intake_path = base_root / "harness/intake.json"
    existing_record = load_json(intake_path) if intake_path.is_file() else {"answers": {}}
    recorded_at = utc_now()
    merged = copy.deepcopy(existing_record.get("answers", {}))
    provided = load_answers(args.answers)
    for field, value in provided.items():
        merged[field] = normalize_answer(
            value,
            source=str(args.answers) if args.answers else "provided",
            recorded_at=recorded_at,
        )
    if args.interactive:
        merged.update(interactive_answers(project, merged, mode=args.mode))
    if not args.interactive and args.answers is None:
        print("error: provide --answers or --interactive", file=sys.stderr)
        return 2

    rendered_project, rendered_planning, missing = render(
        project,
        planning,
        merged,
        profile_root=base_root / "harness/profiles",
    )
    intake = {
        "schema_version": "1.0",
        "mode": args.mode,
        "captured_at": recorded_at,
        "answers": merged,
        "contradictions": existing_record.get("contradictions", []),
        "missing_essential_fields": missing,
        "context_readiness": "provisional" if missing else "sufficient",
    }

    if not args.apply:
        if adopting_existing:
            dispositions, _copy_plan = plan_adoption(source, target)
            mark_adoption_state(
                rendered_project,
                intake,
                dispositions,
                not_evaluated_quality(args.adoption_check),
            )
        print("dry run; no files written")
        print(
            json.dumps(
                {
                    "target": str(target),
                    "missing": missing,
                    "project": rendered_project,
                    "intake": intake,
                },
                indent=2,
            )
        )
        return 0

    dispositions: dict[str, list[str]] = {
        "copied": [],
        "upstream_collisions": [],
        "adoption_deferred": [],
        "merge_required_existing": [],
        "merge_required_missing": [],
    }
    adoption_outputs: dict[str, Path] | None = None
    quality = not_evaluated_quality(args.adoption_check)
    if adopting_existing:
        adoption_outputs = adoption_output_paths(target)
        baseline_check = (
            run_adoption_check(target, adoption_check_argv, timeout=args.adoption_check_timeout)
            if adoption_check_argv
            else None
        )
        dispositions = copy_missing_for_adoption(source, target)
        if adoption_check_argv and baseline_check is not None:
            adopted_check = run_adoption_check(
                target, adoption_check_argv, timeout=args.adoption_check_timeout
            )
            quality = adoption_quality_evidence(
                args.adoption_check,
                dispositions["copied"],
                baseline_check,
                adopted_check,
            )
        mark_adoption_state(rendered_project, intake, dispositions, quality)
    elif not target_exists:
        copy_template(source, target)
    project_target = (
        adoption_outputs["project"]
        if adoption_outputs is not None
        else safe_target_path(target, "harness/project.yaml")
    )
    intake_target = (
        adoption_outputs["intake"]
        if adoption_outputs is not None
        else safe_target_path(target, "harness/intake.json")
    )
    planning_target = (
        adoption_outputs["planning"]
        if adoption_outputs is not None
        else safe_target_path(target, ".github/planning.json")
    )
    charter_target = (
        adoption_outputs["charter"]
        if adoption_outputs is not None
        else safe_target_path(target, "docs/project/charter.md")
    )
    write_json(project_target, rendered_project)
    write_json(intake_target, intake)
    write_json(planning_target, rendered_planning)
    charter_target.parent.mkdir(parents=True, exist_ok=True)
    intake_reference = f"`{intake_target.relative_to(target).as_posix()}`"
    charter_target.write_text(
        render_charter(rendered_project, intake_reference),
        encoding="utf-8",
    )
    if adoption_outputs is not None:
        adoption_report = adoption_outputs["adoption_report"]
        adoption_report.parent.mkdir(parents=True, exist_ok=True)
        adoption_report.write_text(
            adoption_gap_report(dispositions, intake["adoption"]["quality"]),
            encoding="utf-8",
        )
    print(f"rendered project intake at {target}")
    if missing:
        print("context readiness: provisional; unresolved essential fields:")
        for field in missing:
            print(f"  - {field}")
    else:
        print("context readiness: sufficient for bounded planning")
    if adopting_existing:
        unresolved = adoption_gap_count(dispositions)
        print(
            f"copied {len(dispositions['copied'])} upstream-owned files; "
            f"preserved {unresolved} reconciliation gaps; "
            f"see {adoption_outputs['adoption_report'].relative_to(target).as_posix()}"
        )
        print(
            "harness reconciliation: "
            + (
                "complete"
                if intake["adoption"]["reconciliation_status"] == "complete"
                else "provisional; gaps remain"
            )
        )
        print(
            "harness activation: "
            + (
                "active"
                if rendered_project["project"]["status"] == "active"
                else "provisional; reconciliation and intake must both be ready"
            )
        )
        print(f"application quality compatibility: {intake['adoption']['quality']['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
