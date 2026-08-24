# Project handoff

This is an orientation index, not a transcript or second roadmap.

## Read first

1. `AGENTS.md`.
2. `harness/project.yaml` and `docs/project/charter.md`.
3. The active GitHub Issue and Project item once publication is complete.
4. `docs/adr/0008-evidence-first-application-assessment.md`.
5. The relevant repository-local skill under `.agents/skills/`.

## Current state

- Product: Agentic Application Assessor `0.1.0`, unreleased.
- Harness: `0.5.0`, active `python-data` profile, one-repository lifecycle.
- Repository: local greenfield bootstrap; public GitHub creation follows local acceptance,
  independent verification, and secret/history scanning.
- First slice: deterministic, local, read-only static assessment with canonical JSON and Markdown.
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

Implement and verify the smallest read-only assessment slice, publish the verified repository, and
bootstrap its dedicated GitHub Project from the canonical harness Project #13. Dogfood evidence
must record exact target identity and demonstrate that target state did not change.

## Refresh protocol

Update this file only when settled decisions, current state, active work, or the recommended next
loop changes materially. Link to authoritative evidence instead of duplicating it.
