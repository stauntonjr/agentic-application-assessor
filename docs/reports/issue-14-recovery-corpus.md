# Issue #14: recovery semantics and historical challenge corpus

## 1. Outcome and why it matters

`VERIFIED`: Engineering-loop retries now stop mechanically after three consecutive failures. The
third failure is persisted, the run becomes `blocked`, and attempt four is not created. Partial
work is preserved for diagnosis and recovery.

`VERIFIED`: A retry-exhausted run resumes only from a validated structured handoff carrying
`human:IDENTITY` provenance. Resume starts a new revision at attempt one in `understand`, so old
checks, waivers, release-impact evidence, and verifier decisions cannot silently satisfy the
recovered approach.

## 2. Planned versus completed

`VERIFIED`: Six sanitized executable fixtures cover dirty worktrees, partial loops, stale branches,
agent process loss, retry exhaustion, and resumable handoffs. Every fixture runs in a disposable
repository and reports an empty destructive-Git command list.

`VERIFIED`: Two accepted public dogfood failures were reduced to executable challenge manifests:
the 231 unavailable Pi calls from S3NTINEL routing and the partial mutation before adoption
preflight from Macro Technical Pulse. Both are candidates, not approved permanent gates.

## 3. User-visible and engineering-semantic changes

`VERIFIED`: `loop.py new-attempt` now means “record the current attempt as failed and, if allowed,
start the next attempt.” Its third consecutive call at one revision returns a non-zero ceiling
error after durably blocking the run.

`VERIFIED`: New commands expose read-only recovery state and reviewed resume:

- `loop.py recovery-status --run RUN_ID [--integration-ref REF]`;
- `loop.py resume --run RUN_ID --handoff FILE --by human:IDENTITY`;
- `recovery_scenarios.py [--fixture RNNN]`;
- `run_challenges.py --run --include-candidates` for review-only replay;
- `run_challenges.py --promote CNNN --by human:IDENTITY --decision TEXT` for explicit promotion.

## 4. Architecture, schema, dependency, data, and interface changes

`VERIFIED`: ADR-0007 records the retry, revision, recovery, and promotion boundary. Loop-run schema
1.2 now records the retry policy and failed-attempt outcome. The challenge schema is closed and
requires sanitized provenance plus candidate/approved promotion state.

`VERIFIED`: No runtime dependency was added. Recovery uses Python's standard library and disposable
local Git repositories. `harness/recovery/**` is upstream-owned; project challenge instances remain
project-owned so derived repositories choose their retained history.

## 5. Verification evidence and boundary proven

`VERIFIED`: `make smoke` passed 130 unit tests plus harness validation, immutable Actions checking,
compilation, provisional profile handling, challenge validation, and all six recovery replays.

`VERIFIED`: Candidate replay ran both challenge oracles and both minimized known-bad commands. Each
oracle exited zero; each known-bad command exited one with its pinned semantic signature. Candidate
execution did not alter promotion status.

`VERIFIED`: Targeted tests prove blocked persistence, no attempt four, invalid handoff rejection
before mutation, human-provenance gating, preserved partial bytes, new-revision invalidation,
read-only stale-branch detection, candidate promotion validation, and traversal-safe IDs.

`VERIFIED`: The changed universal loop, challenge, recovery, and test files pass Procurement
Intelligence Lab's authoritative Ruff 0.16.3 format and lint configuration. This is a source
compatibility check; no Procurement file, configuration, lock, or environment was changed.

## 6. Acceptance-criterion coverage, waivers, and verifier verdict

- AC1: six `R001`-`R006` fixtures plus `tests.test_recovery_scenarios`.
- AC2: executable `C001` and `C002` candidates with public sanitized provenance and known-bad
  signatures.
- AC3: loop unit tests and `R005`/`R006` prove persisted stop and reviewed recovery without
  destructive Git.
- AC4: `docs/project/recovery-matrix.md` maps every claim to an exact fixture and test.
- AC5: challenge validation, default replay filtering, explicit promotion command, and promotion
  tests keep retention behind human provenance.

No criterion is waived. The exact candidate still requires a separate revision-bound verifier
before integration.

## 7. Baseline-relative write scope and violations

`VERIFIED`: Loop `20260823T192646Z-f4f38e5b`, revision 3, began from clean template main
`f4f38e5b1d264afbe80ca93628e32c0386d2f200` in isolated worktree
`/home/jrs/agentic-project-template-issue14`. The declared scope contains only loop, recovery,
challenge, test, schema, ownership, documentation, smoke, and lock paths.

`VERIFIED`: No application repository, external worktree, deployment, provider, Issue content, or
GitHub Project other than the authorized template Issue #14 status was mutated.

## 8. GitHub Issue, Project, PR, and release state

`VERIFIED`: Template Issue #14 was moved from Todo to In Progress in canonical Project #13 before
implementation. No pull request, merge, tag, GitHub Release, or package publication is claimed by
this pre-integration report.

`REPORTED`: The recommended release impact is `minor` because the unreleased pre-1.0 harness gains
new CLI behavior and recovery contracts. This recommendation does not authorize a version bump or
release.

## 9. Risks, limitations, failures, and unverified claims

`VERIFIED`: The recovery layer preserves bytes already written to durable repository storage; it
cannot recover model context or edits that never reached disk. `human:IDENTITY` is auditable
provenance, not authentication, so branch protection and repository review remain the real
authorization boundary.

`VERIFIED`: `C001` and `C002` are deliberately excluded from default `make challenges` execution
pending an owner review of their exact minimized content. Their candidate replay is evidence of
executability, not evidence of promotion.

`VERIFIED`: Fixtures retain synthetic values and public artifact references only. They do not
retain raw Pi output, prompts, hidden reasoning, private source, tokens, or secrets.

## 10. Decisions or authorization needed

An owner may approve neither, either, or both candidate challenges. Promotion is not required to
exercise them for review, and no agent should invent the human provenance marker.

## 11. Recommended next loop

After integration, either review candidate promotion or continue the next authorized roadmap
dogfood. Do not infer application-repository write authority from this template-only loop.

## 12. Exact revision and change scope

- Engineering loop: `20260823T192646Z-f4f38e5b`, revision 3, attempt 1.
- Start commit: `f4f38e5b1d264afbe80ca93628e32c0386d2f200`.
- Product release-impact recommendation: `minor` for backward-compatible pre-1.0 recovery and
  challenge-governance capabilities.
- Candidate commit, digests, independent verdict, PR, merge, and exact-main CI belong to final loop
  evidence and the GitHub completion record.
