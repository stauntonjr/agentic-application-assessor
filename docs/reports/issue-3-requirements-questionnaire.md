# Issue #3 requirements-questionnaire loop report

## Outcome

The candidate adds a deterministic gap-only questionnaire and explicit reconciliation workflow.
It binds questions to exact target and accepted-context evidence, preserves owner answers,
contradictions, and unknowns, emits a draft by default, and requires owner plus date metadata before
emitting accepted context.

## Acceptance evidence

| Criterion | Candidate evidence |
|---|---|
| AC1 | Stable eight-question bank, accepted-context gap filtering, observed package-name recommendation, deployment-signal context, schemas, and deterministic tests. |
| AC2 | Duplicate-key-free bounded inputs; source/date/status fields; observed versus human-declared provenance; preserved contradictions and unknowns. |
| AC3 | Digest-bound reconciliation; accepted declarations cannot be answered or overwritten; draft default; paired `--accept-by` and `--accepted-on` gate. |
| AC4 | Local Git/static reads only; standard-output-only CLI; stale identity and sanitized error tests; no model, network, execution, installation, or target writes. |
| AC5 | Custom and Draft 2020-12 parity tests for questionnaire `1.0`, answers `1.0`, and context `1.1` cover malformed, duplicate, oversized, deep, symlink, stale, conflicting, incomplete, and deterministic cases. |
| AC6 | CLI, schemas, tests, example, ADR, README, changelog, handoff, report, and derived harness lock are included in the declared scope. |

Exact commands and results are recorded in
`.harness/runs/issue-3-questionnaire-workflow/run.json`. Independent verification and integration
remain orchestrator-owned.

Attempt 2 restores the exact public schema-`1.0` array/string compatibility boundary, keeps the
stricter schema-`1.1` bounds, moves stable-ID cardinality rules under the questionnaire array where
Draft 2020-12 evaluates them, and corrects the accepted-context CLI example. Base-contract fixtures
and duplicate-ID custom/schema parity tests cover the verifier findings.

Attempt 3 aligns context-`1.1` contradiction and unknown collection semantics: both the custom
validator and Draft 2020-12 schema reject exact duplicate records while accepting distinct records
that reuse an identifier. Bidirectional regressions cover both collections. Parity claims in this
report are deliberately limited to the questionnaire `1.0`, answer `1.0`, and context `1.1`
surfaces added by this issue. The legacy context-`1.0` public schema and custom loader retain
pre-existing mismatches, including custom 4,096-character component-field bounds and custom record
identifier uniqueness that the public schema does not express; changing those compatibility
semantics is outside Issue #3.

The attempt-1 and attempt-2 independent verdicts were `revise`; their findings and superseded
candidate identities remain in the loop record. Attempt 3 preserves the product release-impact
recommendation as `minor` and requires a fresh independent verdict before integration.

## Semantic effects

- New CLI commands: `questionnaire` and `reconcile`.
- New public questionnaire and answer schemas `1.0`.
- Application context `1.1` adds drafts, requirements, provenance, contradictions, and unknowns;
  accepted `1.0` inputs remain supported.
- `assess` still rejects draft context.

## Risks and limitations

- `--accept-by` is declarative audit metadata, not identity authentication.
- Repository evidence is intentionally narrow; it cannot prove live deployment or owner intent.
- The workflow is structured JSON/stdout rather than an interactive terminal interview.
- This implementer recommends a `minor` product release impact because public CLI and schema
  contracts expand. No release or publication is authorized.
