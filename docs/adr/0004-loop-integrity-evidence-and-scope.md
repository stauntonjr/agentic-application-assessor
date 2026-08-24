# ADR-0004: Bind loop completion to evidence, candidate identity, and write scope

- Status: accepted
- Date: 2026-08-21
- Deciders: repository owner
- Governing issue: bootstrap-loop-integrity

## Context

The original engineering loop required acceptance evidence, independent review, and write ownership in prose, but its executable run record could still report completion when checks were not mapped to acceptance criteria, a reviewer had inspected an older candidate, or implementation changed undeclared paths. Those are integrity failures rather than reporting omissions.

Current Pi ecosystem implementations provide useful prior art. `pi-goal-list-loop-audit` separates mechanical verification evidence from an auditor verdict and rejects stale objective revisions. `rpiv-mono` captures a run-start dirty baseline and distinguishes pre-existing repository debt from writes attributable to the current run. `pi-dynamic-workflows` uses stable work-unit identity and bounded, explicit completion ledgers. The concepts are portable; no third-party source or prompt is copied. In particular, `pi-goal-list-loop-audit` is AGPL-3.0, so this repository uses an independent implementation.

## Decision

Every new engineering-loop run must:

1. preserve the original accepted objective as an immutable seed and assign a stable ID to each acceptance criterion;
2. capture a content-aware snapshot of all dirty and untracked paths, including index blob identity, `assume-unchanged` and `skip-worktree` paths, forcibly visible submodule state, and recursively fingerprinted dirty gitlinks or embedded repositories, before the run record is written;
3. declare exact file paths and/or directory prefixes the implementer may change;
4. identify the implementer sessions so that they cannot record the independent approval;
5. link checks to criterion IDs and to the current contract revision and implementation attempt;
6. bind verifier verdicts to the current revision, attempt, commit, and baseline-relative working-tree digest; and
7. refuse the `reported` terminal state when an unwaived criterion lacks passed evidence, the latest verdict is absent, non-approving, incomplete, or stale, or the baseline-relative delta contains undeclared writes.

Blocked and abandoned runs remain reportable without satisfying the completion gate so incomplete work is preserved truthfully. Requirement or scope changes increment the run revision and invalidate prior waivers; implementation retries increment the attempt identity. Existing check and verdict records remain in history but cannot satisfy the new revision or attempt. A criterion waiver must record a `human:IDENTITY` authority label and reason; this is auditable provenance rather than authentication.

Schema 1.2 also requires a current product release-impact assessment. The verifier candidate identity binds its digest so changing `none`, `patch`, `minor`, `major`, rationale, or declared public-contract changes after approval makes that approval stale.

This decision does not yet add an append-only transition journal, deterministic cross-session resume, retry-class taxonomy, failure memos, runtime watchdogs, or open-ended metric loops.

## Consequences

### Positive

- Completion claims have a deterministic acceptance-to-evidence chain.
- A post-review code change or requirement revision automatically invalidates approval.
- Pre-existing dirty user work is preserved without being blamed on the current run.
- Newly changed undeclared files fail closed and are never deleted automatically.
- Provider adapters can use their own session identifiers without changing the canonical data model.

### Negative

- Starting and closing a loop requires more explicit metadata.
- Content and index hashing adds local I/O proportional to the dirty working set; dirty gitlinks also require recursive repository inspection.
- A repository that changes concurrently after verification must be reviewed again even if the change is unrelated but within the recorded run delta.
- Identity separation is artifact-based; the harness cannot cryptographically prove that two labels represent different people or processes.

### Risks and mitigations

- Overly broad prefix declarations could neutralize scope control: reject the repository root and document narrow prefixes.
- A reviewer could provide a false identity: retain raw evidence and provider session references; treat identity as auditable provenance, not authentication.
- Baseline fingerprints could expose repository content: store hashes and Git status only, never file contents.
- Ignored, uninspectable, or embedded nested repositories could hide changes: override submodule ignore settings, fingerprint inspectable nested repositories recursively, and fail closed rather than record a null directory digest.
- Index visibility flags could hide tracked changes: enumerate `assume-unchanged` and `skip-worktree` paths independently of porcelain status and fingerprint their index and worktree state.
- Users could weaken acceptance after a failure: preserve revision history and require the new revision to be reviewed independently.

## Alternatives considered

| Alternative | Evidence | Reason not selected |
|---|---|---|
| Keep prose-only gates | Existing v0.3 loop | Cannot mechanically reject false completion |
| Require a clean tree before every loop | Common CI practice | Conflicts with safe preservation of unrelated user work and shared local environments |
| Bind approval only to `HEAD` | Git commit identity | Misses uncommitted and unborn-repository candidates |
| Adopt a Pi workflow package | Pi ecosystem prior art | Adds runtime/provider coupling and unnecessary dependency authority |
| Copy upstream prompts or implementation | Faster initial implementation | Provenance and licensing risk; canonical behavior should remain provider-neutral |

## Verification and revisit trigger

Unit tests must demonstrate criterion-linked completion, stale-verdict rejection, pre-existing dirty-path subtraction, untracked scope-escape rejection, missing-evidence rejection, and implementer self-approval rejection. `make smoke` must pass, and the Pi adapter must continue to load offline.

Revisit if Git supplies a safer portable working-tree snapshot primitive, provider runtimes expose authenticated reviewer/session identities, or dogfooding shows that content-aware dirty-set hashing creates unacceptable cost.
