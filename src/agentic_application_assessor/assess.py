"""Bounded static assessment compiler."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path, PurePosixPath

from . import __version__
from .auditor import load_auditor_artifact
from .context import load_context
from .errors import AssessmentError
from .git import target_identity
from .model import Claim, Evidence, Report


MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_FILES = 50_000
MAX_EVIDENCE = 2_000
MANIFESTS = {
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "requirements.txt",
    "uv.lock",
}
DEPLOYMENT_NAMES = {"Dockerfile", "compose.yaml", "compose.yml", "docker-compose.yml", "Procfile"}
ENTRYPOINT_NAMES = {"__main__.py", "main.py", "cli.py", "manage.py", "app.py"}


def _kind(relative: str) -> str | None:
    path = PurePosixPath(relative)
    parts = path.parts
    name = path.name
    if name in MANIFESTS:
        return "manifest"
    if name in ENTRYPOINT_NAMES or name.endswith(".service"):
        return "entrypoint"
    if name.endswith(".schema.json") or "schemas" in parts:
        return "schema"
    if name.lower().startswith(("openapi", "swagger")) or path.suffix in {".proto", ".graphql"}:
        return "interface"
    if name in DEPLOYMENT_NAMES or any(
        part in {"deploy", "deployment", "k8s", "terraform"} for part in parts
    ):
        return "deployment"
    if any(part in {"tests", "test", "application_tests", "spec"} for part in parts):
        return "test"
    if name in {"README.md", "AGENTS.md"} or "docs" in parts or "adr" in parts:
        return "documentation"
    if name.startswith(".") and name.endswith(("rc", "config")) or name in {"Makefile", "tox.ini"}:
        return "configuration"
    return None


def _safe_file(root: Path, relative: str) -> tuple[Path, os.stat_result]:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise AssessmentError(f"unsafe repository path: {relative!r}")
    cursor = root
    metadata: os.stat_result | None = None
    for index, part in enumerate(path.parts):
        cursor /= part
        try:
            metadata = cursor.lstat()
        except OSError as exc:
            raise AssessmentError(f"cannot inspect repository path {relative}: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise AssessmentError(f"repository path is a symlink: {relative}")
        if index < len(path.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise AssessmentError(f"repository path has non-directory ancestor: {relative}")
    if metadata is None or not stat.S_ISREG(metadata.st_mode):
        raise AssessmentError(f"repository path is not a regular file: {relative}")
    if metadata.st_size > MAX_FILE_BYTES:
        raise AssessmentError(f"recognized evidence file exceeds 2 MiB: {relative}")
    return cursor, metadata


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(131072), b""):
                value.update(chunk)
    except OSError as exc:
        raise AssessmentError(f"cannot read evidence file {path}: {exc}") from exc
    return value.hexdigest()


def assess(target: Path, context_path: Path, auditor_report: Path | None = None) -> Report:
    root, identity, paths = target_identity(target)
    if len(paths) > MAX_FILES:
        raise AssessmentError("repository contains too many visible files to assess safely")
    context, context_sha256 = load_context(context_path)
    evidence: list[Evidence] = []
    coverage: dict[str, int] = {}
    visible = set(paths)
    for relative in paths:
        kind = _kind(relative)
        if kind is None:
            continue
        path, _ = _safe_file(root, relative)
        coverage[kind] = coverage.get(kind, 0) + 1
        evidence.append(
            Evidence(
                f"static.{kind}.{hashlib.sha256(relative.encode()).hexdigest()[:16]}",
                "observed",
                kind,
                relative,
                "recognized regular file",
                _digest(path),
            )
        )
        if len(evidence) > MAX_EVIDENCE:
            raise AssessmentError("recognized evidence exceeds the 2,000-item safety bound")
    review_source = context["review"]["source"]
    application = context["application"]
    evidence.append(
        Evidence(
            "context.application.purpose",
            "human-declared",
            "purpose",
            f"{context_path.name}#/application/purpose",
            application["purpose"],
        )
    )
    evidence.append(
        Evidence(
            "context.application.stakeholders",
            "human-declared",
            "stakeholders",
            f"{context_path.name}#/application/stakeholders",
            "; ".join(application["stakeholders"]),
        )
    )
    evidence.append(
        Evidence(
            "context.review",
            "human-declared",
            "review",
            f"{context_path.name}#/review",
            f"accepted on {context['review']['confirmed_on']} from {review_source}",
        )
    )
    claims = [
        Claim(
            "application.purpose",
            "human-declared",
            application["purpose"],
            f"{context_path.name}#/application/purpose",
            ("context.application.purpose",),
        ),
        Claim(
            "application.audience",
            "human-declared",
            "Stakeholders: " + ", ".join(application["stakeholders"]),
            f"{context_path.name}#/application/stakeholders",
            ("context.application.stakeholders",),
        ),
    ]
    contradictions: list[Claim] = []
    for component_index, component in enumerate(context.get("components", [])):
        evidence_id = f"context.component.{component['id']}"
        component_source = f"{context_path.name}#/components/{component_index}"
        evidence.append(
            Evidence(
                evidence_id,
                "human-declared",
                "component",
                component_source,
                f"{component['name']}: {component['responsibility']}",
            )
        )
        missing = sorted(
            path
            for path in component["paths"]
            if path not in visible
            and not any(item.startswith(path.rstrip("/") + "/") for item in visible)
        )
        status = "proposed"
        if missing:
            status = "contradicted"
            contradictions.append(
                Claim(
                    f"contradiction.component.{component['id']}.missing-paths",
                    "derived",
                    f"Component {component['id']} declares absent paths: {', '.join(missing)}",
                    f"{component_source}/paths",
                    (evidence_id,),
                    "contradicted",
                )
            )
        claims.append(
            Claim(
                f"architecture.component.{component['id']}",
                "human-declared",
                f"Proposed component {component['name']}: {component['responsibility']}",
                component_source,
                (evidence_id,),
                status,
            )
        )
    for group, singular in (
        ("workflows", "workflow"),
        ("data_assets", "data asset"),
        ("quality_scenarios", "quality scenario"),
    ):
        for record_index, record in enumerate(context.get(group, [])):
            namespace = group.replace("_", "-")
            evidence_id = f"context.{namespace}.{record['id']}"
            summary = record.get("description") or record.get("response") or record.get("name")
            evidence.append(
                Evidence(
                    evidence_id,
                    "human-declared",
                    singular,
                    f"{context_path.name}#/{group}/{record_index}",
                    str(summary),
                )
            )
    unknowns: list[Claim] = []
    for group, label in (
        ("components", "application components"),
        ("workflows", "important runtime workflows"),
        ("data_assets", "data assets and movement"),
        ("quality_scenarios", "decision-driving quality scenarios"),
    ):
        if not context.get(group):
            namespace = group.replace("_", "-")
            unknowns.append(
                Claim(
                    f"unknown.context.{namespace}",
                    "unavailable",
                    f"No accepted context declares {label}.",
                    f"{context_path.name}#/{group}",
                    (),
                    "unavailable",
                )
            )
    for kind in ("manifest", "entrypoint", "interface", "deployment", "test", "documentation"):
        if coverage.get(kind, 0) == 0:
            unknowns.append(
                Claim(
                    f"unknown.static.{kind}",
                    "unavailable",
                    f"Static inventory found no recognized {kind} evidence.",
                    f"target:{identity.state_id}#inventory/{kind}",
                    (),
                    "unavailable",
                )
            )
    unknowns.extend(
        [
            Claim(
                "unknown.runtime-behavior",
                "unavailable",
                "Runtime behavior is unavailable because target execution is outside the v0.1 trust boundary.",
                "tool-policy:adr-0008#decision",
                (),
                "unavailable",
            ),
            Claim(
                "unknown.production-topology",
                "unavailable",
                "Production topology is unavailable because live infrastructure and network access are outside the v0.1 trust boundary.",
                "tool-policy:adr-0008#decision",
                (),
                "unavailable",
            ),
            Claim(
                "unknown.model-synthesis",
                "unavailable",
                "Model synthesis is unavailable because the canonical v0.1 core is model-free.",
                "tool-policy:adr-0008#decision",
                (),
                "unavailable",
            ),
        ]
    )
    auditor_input = None
    if auditor_report is not None:
        imported = load_auditor_artifact(auditor_report, root, identity)
        evidence.extend(imported.evidence)
        if len(evidence) > MAX_EVIDENCE:
            raise AssessmentError("combined evidence exceeds the 2,000-item safety bound")
        coverage["imported-auditor-findings"] = imported.finding_count
        coverage["imported-auditor-finding-evidence"] = imported.nested_evidence_count
        auditor_input = imported.descriptor
    final_root, final_identity, final_paths = target_identity(target)
    if final_root != root or final_identity != identity or final_paths != paths:
        raise AssessmentError("target changed during assessment")
    return Report(
        __version__,
        identity,
        context_path.name,
        context_sha256,
        tuple(evidence),
        tuple(claims),
        tuple(contradictions),
        tuple(unknowns),
        coverage,
        auditor_input,
        context_schema_version=context["schema_version"],
    )
