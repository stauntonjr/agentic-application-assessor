# ADR-0007: Bounded retry recovery and reviewed challenge promotion

Status: accepted

## Context

The engineering-loop contract said to stop after three consecutive failures, preserve partial work,
and escalate, but `loop.py new-attempt` previously allowed unlimited attempts. Dogfood reproduced the
gap: a Pi invocation attempted an unavailable tool 231 times before operator interruption. Earlier
adoption dogfood also found a preflight failure only after unrelated files had been copied. Reports
retained those facts, but there was no minimized executable recovery matrix or governed promotion
path for retaining them as challenges.

## Decision

Bind the retry limit into each run at start. `new-attempt` records the failed attempt; failures one
and two start attempts two and three, while failure three persists the record as `blocked` and does
not create attempt four. A blocked retry-exhausted run may resume only from a structured handoff
with recorded `human:IDENTITY` provenance. Resume preserves the working tree, starts a new
requirement revision at attempt one, re-enters `understand`, and therefore invalidates prior checks,
waivers, release-impact evidence, and verdicts.

Recovery inspection is read-only. `recovery-status` compares the current run with its baseline and,
when supplied, an integration ref. Neither recovery nor the disposable fixture runner invokes Git
reset, clean, checkout, restore, or rebase.

Keep two evidence classes separate:

- `harness/recovery/R*.json` contains sanitized deterministic fixtures for expected recovery
  behavior.
- `harness/challenges/C*.json` contains minimized escaped-defect oracles and known-bad replayers.

A new challenge starts as `candidate`. Validation permits review but default replay excludes it.
`--include-candidates` may execute it without changing status. Promotion requires an explicit
`--by human:IDENTITY` and decision; the marker is auditable provenance, not authentication. An
approved challenge without that provenance fails closed.

Fixtures and challenges must reference public or synthetic evidence, declare sanitization, and
declare that no raw transcript is retained. Resume handoffs reject transcript, prompt, hidden
reasoning, secret, and token fields.

## Consequences

- A retry-exhausted run cannot accidentally continue as attempt four.
- Recovery changes the approach under a new revision instead of laundering old evidence.
- Dirty user work, partial files, and interrupted state remain inspectable and untouched.
- Candidate challenges can be tested before a human decides whether they belong in the permanent
  gate.
- The two initial dogfood-derived challenges remain candidates until an owner reviews their exact
  minimized content.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Count retries only in instructions | The observed 231-call session proved prose is not an enforcement boundary |
| Delete partial work and restart clean | It can erase user work and removes evidence needed to diagnose the failure |
| Resume at attempt four | It makes the documented ceiling false and lets stale evidence remain current |
| Auto-promote every observed failure | Model errors, private text, and accidental behavior must not silently become permanent policy |
| Store raw transcripts for replay | They can contain private source, secrets, prompts, or hidden reasoning and are unnecessary for deterministic minimization |

## Verification

`tests.test_loop` proves the persisted ceiling, fail-closed handoff validation, human-provenance
gate, new revision, preserved bytes, and stale-branch inspection. `tests.test_recovery_scenarios`
replays all six recovery classes. `tests.test_challenges` proves candidate/approved validation and
promotion provenance. The public coverage map is `docs/project/recovery-matrix.md`.
