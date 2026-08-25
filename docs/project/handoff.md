# Project handoff

This is an orientation index, not a transcript or second roadmap.

## Read first

1. `AGENTS.md`.
2. `harness/project.yaml` and `docs/project/charter.md`.
3. The active GitHub Issue and
   [Project #16](https://github.com/users/stauntonjr/projects/16) item.
4. `docs/adr/0008-evidence-first-application-assessment.md`.
5. The relevant repository-local skill under `.agents/skills/`.

## Current state

- Product: Agentic Application Assessor `0.1.0`, unreleased.
- Harness: `0.5.0`, active `python-data` profile, one-repository lifecycle.
- Repository: public at
  [stauntonjr/agentic-application-assessor](https://github.com/stauntonjr/agentic-application-assessor);
  dedicated roadmap in [Project #16](https://github.com/users/stauntonjr/projects/16).
- First slice: implemented deterministic, local, read-only static assessment with context/report
  schemas `1.0`, canonical JSON, and Markdown; full gates and independent revision-7 review passed.
- Auditor adapter: Issue #2 imports exactly Agentic Repo Auditor `0.1.0` schema `1.2`
  JSON, supports SHA-1 and SHA-256 Git repositories, rejects stale, cross-collector, or
  during-assessment target mutations, preserves baseline no-artifact output, and preserves Auditor
  findings only as imported evidence; it is integrated on `main`.
- Requirements-questionnaire candidate: Issue #3 adds digest-bound gap-only questions and answer
  reconciliation, reviewable schema-`1.1` context drafts, and an explicit owner/date acceptance
  transition. Attempt 2 restores exact schema-`1.0` compatibility, enforces Draft 2020-12 stable
  question-ID uniqueness, and repairs the accepted-context example. Attempt 3 aligns exact-duplicate
  contradiction and unknown validation on the new context-`1.1` surface and narrows parity claims
  to the Issue #3 artifacts; fresh independent verification and integration remain pending.
- First dogfood: Agentic Repo Auditor; Macro Technical Pulse follows.
- Release/deployment: no tag, GitHub Release, package publication, hosted service, or deployment is
  authorized.

## Accepted product boundaries

- The deterministic core does not execute target code, resolve target dependencies, use the
  network, call a model, or collect live telemetry.
- Every claim carries an origin and source or is explicitly unavailable.
- Architecture views are evidence-labeled proposals, not declarations of intended design.
- Agentic Repo Auditor remains a separate product; its canonical JSON is a versioned imported
  artifact, not duplicated logic.
- Executable analysis, runtime artifacts, and local Sparkrun synthesis require later adapter
  decisions and explicit trust boundaries.

## Next loop

Verify and integrate the requirements questionnaire in
[Issue #3](https://github.com/stauntonjr/agentic-application-assessor/issues/3) before Macro Technical Pulse dogfood in
[Issue #4](https://github.com/stauntonjr/agentic-application-assessor/issues/4).

## Refresh protocol

Update this file only when settled decisions, current state, active work, or the recommended next
loop changes materially. Link to authoritative evidence instead of duplicating it.
