# Issue #17: privacy-preserving outcome telemetry

Issue: [#17](https://github.com/stauntonjr/agentic-project-template/issues/17)

Harness run: `20260823T200949Z-fa1e7451`

## Outcome

The candidate adds an opt-in, dependency-free local telemetry boundary for the seven requested
engineering-loop outcomes. It separates locally measured, provider-reported, inferred, and
unavailable values; derives only what the loop record can prove; and leaves missing optional data
unavailable instead of converting it to zero.

The CLI prints to stdout by default, writes only when explicitly asked, restricts written output
to ignored `.harness/telemetry/`, rejects symlink traversal, retains no raw input, makes no network
calls, and exports nothing. Its input allowlist excludes content-bearing and secret-like fields.

The de-identified aggregate is deliberately modest: it validates every summary, removes run
identifiers, counts provenance, and keeps unlike units separate. Organization storage,
correlation, dashboards, provider adapters, and billing access remain outside this issue.

## Acceptance-criterion coverage

| Criterion | Candidate evidence |
|---|---|
| AC1 | Versioned input, per-loop summary, and aggregate schemas define human corrections, retries, escaped defects, acceptance pass rate, cycle time, elapsed time, and accepted-change cost. |
| AC2 | Each measurement carries one bounded origin and method; absent values are explicit null/unavailable, and incompatible origin-method pairs fail validation. |
| AC3 | Ingestion is explicit-CLI-only, stdout is the default, raw inputs are not retained, content/secret fields fail closed, and the tool performs no provider or network access. |
| AC4 | `summarize` emits one validated loop summary; `aggregate` removes run identifiers and retains unit/provenance boundaries for a future external reporting project. |
| AC5 | Configuration, documentation, and adversarial tests enforce disabled-by-default collection, content-free inputs, caller-managed written-summary retention, local path containment, and no organization export. |

No criterion waiver is proposed. Completion requires current-attempt full harness checks, an
independent revision-bound verdict, integration, and publication evidence.

## Research decision

The design adapts the OpenTelemetry metric model's explicit name, unit, provenance, and compatible
aggregation concepts without adopting an SDK, collector, OTLP transport, or exporter. It treats
OpenTelemetry GenAI conventions as drift-prone because the canonical page marks them Development,
and it does not invent token or cost values when none are available. DORA is used only to prevent
a terminology mistake: harness timing is not commit-to-production lead time.

See `docs/research/outcome-telemetry-landscape.md` for the dated primary-source comparison and
`docs/project/outcome-telemetry.md` for the operational contract.

## Verification scope

Targeted tests cover derivation, terminal versus in-progress acceptance, explicit zero versus
unavailable values, retrospective observation time, interval overlap and wall-boundary escape,
forbidden fields, unexpected fields, incompatible provenance, non-finite numbers, malformed
summary import, mixed cost units, identity removal, stdout defaults, output containment, and
symlink traversal.

Full harness checks, lock consistency, independent verification, and remote publication are still
pending at this candidate stage and must not be inferred from the targeted results.

## Risks and deferred work

- A human can still supply an incorrect count or estimate; provenance identifies the evidence
  class but does not prove the underlying receipt or review.
- Written local summaries may still be sensitive operational data. The caller owns retention and
  filesystem access after requesting a write.
- The aggregate is not anonymous merely because direct run IDs are absent; small cohorts and
  external context can re-identify data. Minimum cohorts and organizational privacy controls are
  deferred.
- Provider token/cost ingestion, billing APIs, remote export, dashboards, and organization-wide
  analytics require a separate project and explicit authority.

## Exact template scope

- Start commit: `fa1e7451cf0c835fa0287620e7f7dd85d08a8a22`
- Branch: `issue-17-outcome-telemetry`
- Declared paths: telemetry configuration and schemas, one local CLI, tests, research and operator
  documentation, README, handoff, changelog, ignore rules, and `harness.lock`.
- Product release-impact recommendation: minor, because the candidate adds a new opt-in public
  telemetry CLI and versioned interchange schemas without changing existing default behavior.
