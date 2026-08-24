"""Canonical assessment model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCHEMA_VERSION = "1.0"
ORIGINS = (
    "observed",
    "imported-tool",
    "human-declared",
    "derived",
    "model-synthesized",
    "unavailable",
)


@dataclass(frozen=True, order=True)
class Evidence:
    """One content-bound fact or explicit absence."""

    evidence_id: str
    origin: str
    kind: str
    source: str
    value: str
    sha256: str | None = None

    def __post_init__(self) -> None:
        if self.origin not in ORIGINS:
            raise ValueError(f"unsupported evidence origin: {self.origin}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.evidence_id,
            "origin": self.origin,
            "kind": self.kind,
            "source": self.source,
            "value": self.value,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, order=True)
class Claim:
    """A report statement linked to evidence."""

    claim_id: str
    origin: str
    statement: str
    evidence_ids: tuple[str, ...]
    status: str = "supported"

    def __post_init__(self) -> None:
        if self.origin not in ORIGINS:
            raise ValueError(f"unsupported claim origin: {self.origin}")
        if self.status not in {"supported", "proposed", "contradicted", "unavailable"}:
            raise ValueError(f"unsupported claim status: {self.status}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.claim_id,
            "origin": self.origin,
            "status": self.status,
            "statement": self.statement,
            "evidence_ids": list(sorted(self.evidence_ids)),
        }


@dataclass(frozen=True)
class Target:
    """Exact outer Git repository identity assessed by the core."""

    name: str
    revision: str
    branch: str
    dirty: bool
    state_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "revision": self.revision,
            "branch": self.branch,
            "dirty": self.dirty,
            "state_id": self.state_id,
        }


@dataclass(frozen=True)
class Report:
    """Complete deterministic assessment report."""

    tool_version: str
    target: Target
    context_path: str
    context_sha256: str
    evidence: tuple[Evidence, ...]
    claims: tuple[Claim, ...]
    contradictions: tuple[str, ...]
    unknowns: tuple[str, ...]
    coverage: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "tool": {"name": "agentic-application-assessor", "version": self.tool_version},
            "target": self.target.as_dict(),
            "inputs": {
                "context": {
                    "path": self.context_path,
                    "sha256": self.context_sha256,
                    "schema_version": "1.0",
                },
                "agentic_repo_auditor": None,
            },
            "coverage": {key: self.coverage[key] for key in sorted(self.coverage)},
            "evidence": [item.as_dict() for item in sorted(self.evidence)],
            "claims": [item.as_dict() for item in sorted(self.claims)],
            "contradictions": list(sorted(self.contradictions)),
            "unknowns": list(sorted(self.unknowns)),
        }
