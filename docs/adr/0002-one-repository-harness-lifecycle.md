# ADR-0002: Keep the harness and application in one repository

- Status: accepted
- Date: 2026-08-21
- Deciders: repository owner
- Governing issue: bootstrap-upgrade-lifecycle

## Context

Repository-root instructions, project-local skills, GitHub configuration, engineering evidence, and application code must remain discoverable and reviewable together. Making the harness or application a submodule would create separate Git histories, two-step commits, split GitHub authority, and instruction-discovery ambiguity. A copied template, however, needs an explicit way to receive upstream improvements without silently overwriting project policy.

## Decision

Keep each application and its harness in the same repository root. Treat `agentic-project-template` as an upstream factory that creates or adopts derived repositories, not as a runtime submodule.

Track the originating release, commit, file checksums, and ownership classes in `harness.lock`. Classify template artifacts as `upstream-owned`, `project-owned`, or `merge-required`. Compare a derived repository with a newer release using the locked base, current local content, and new upstream content. Apply only reviewed plans, require an explicit resolution for every manual operation, write a rollback receipt, and refuse rollback over later modifications.

Release lookup and fetch are opt-in network operations. Project-owned and merge-required files are never overwritten merely because a newer template exists.

## Consequences

### Positive

- Agents, CI, GitHub planning, application code, and durable evidence share one authoritative repository boundary.
- Derived projects can identify local drift without Git ancestry to the template.
- Safe upstream-only changes can be automated while policy and project state remain human-reviewed.
- Every applied upgrade has provenance and a recoverable receipt.

### Negative

- Derived repositories contain a copy of the harness rather than a lightweight dependency pointer.
- Upgrades that touch project policy require explicit per-file resolution.
- Release publishing must regenerate `harness.lock` with the final release commit.

### Risks and mitigations

- Stale plans could overwrite later work: recheck local and source hashes at apply time.
- A rollback could erase post-upgrade edits: compare current hashes with the receipt before restoring.
- A malicious upstream could alter instructions or scripts: pin repository, release, commit, and checksums and retain human review for trust-sensitive files.
- Ownership rules could be too broad: make the rule set versioned and require manual review when a file's ownership changes.

## Alternatives considered

| Alternative | Evidence | Reason not selected |
|---|---|---|
| Harness as submodule | Central version pointer | Root instructions and GitHub state would be split from the application |
| Application as submodule | Clean control-plane repository | Creates two commits and separate CI, Issue, PR, and release boundaries for one product |
| Copy once with no upgrade channel | Simplest bootstrap | Derived projects silently diverge and cannot evaluate upstream improvements safely |
| Automatic overwrite from template | Low upgrade effort | Can destroy accepted project policy and locally evolved workflows |

## Verification and revisit trigger

Unit tests must demonstrate three-way classification, refusal of unresolved manual operations, apply receipts, rollback, stale-plan detection, path confinement, and lock validation. Revisit if agent products support a portable, root-discoverable, cryptographically verified harness package that preserves repository-local authority without duplicating files.
