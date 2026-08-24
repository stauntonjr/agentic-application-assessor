# ADR-0008: Evidence-first application assessment boundary

- Status: accepted
- Date: 2026-08-24
- Deciders: human owner
- Governing work item: local bootstrap; reconcile to the first GitHub Issue after publication

## Context

Repository-readiness audits do not explain an application's purpose, system boundaries,
interfaces, data movement, runtime behavior, domain semantics, or decision-relative quality risks.
Landscape research in Agentic Repo Auditor Issue #11 found useful but partial evidence families:
architecture methods require stakeholder context, static analyzers cover modeled languages and
constructs, and runtime tools observe only executed paths. Some collectors execute target or
dependency code, access networks, or expose confidential data.

The product must help an engineering lead understand an unfamiliar application without turning
inference into fact or weakening the read-only safety contract. Its MIT corpus must not copy or
adapt CC BY-SA arc42 template text.

## Decision

Build a separate, local-first evidence compiler with these trust tiers:

1. exact local Git target identity;
2. bounded static repository evidence;
3. dated, human-reviewed declarations;
4. versioned imported analysis artifacts;
5. separately authorized executable analysis;
6. separately authorized runtime evidence; and
7. optional, provenance-recorded model synthesis.

The first `0.1.0` slice implements only tiers 1-3. The accepted product scope includes an explicit
Agentic Repo Auditor JSON adapter within tier 4, but that adapter is the next bounded slice and is
not implemented by the initial public baseline. The canonical core is deterministic and
model-free. It emits versioned JSON plus derived Markdown, preserves contradictions and unknowns,
and labels proposed architecture elements rather than claiming intended design.

The core does not execute target code, install target dependencies, access the network, remediate
findings, certify security/compliance, or collect live telemetry. Local Sparkrun synthesis is a
future optional adapter over the canonical evidence, not an authority for observations.

## Alternatives considered

- Extend Agentic Repo Auditor: rejected because application semantics and runtime evidence would
  blur its accepted repository-readiness contract.
- Adopt one analysis platform: deferred because no single platform covers declared intent, static
  structure, runtime behavior, and quality tradeoffs across languages and trust tiers.
- Generate the report directly with an agent: rejected as the canonical core because it cannot by
  itself guarantee stable identity, reproducible coverage, or a defensible fact/inference boundary.
- Include local-model narrative in `0.1.0`: deferred until prompt/model provenance, privacy,
  evaluation, repeatability, latency, and failure behavior have an accepted adapter contract.

## Consequences

- The first slice is smaller and safer but will expose important evidence as unavailable.
- Every adapter needs explicit version, provenance, licensing, and target-identity validation.
- Runtime and executable evidence require new authorization and isolation decisions.
- The product owns a broader evidence envelope while retaining source formats such as SARIF, SPDX,
  CycloneDX, and Auditor JSON by reference.

## Verification and revisit criteria

Verify byte-identical results for repeated identical inputs, unchanged target state, bounded reads,
symlink rejection, hostile Git-helper neutralization, origin labels, schema validation, and
deterministic Markdown. Revisit when the first two dogfoods show that the static/context boundary
cannot support the intended prioritization decision, or before adding executable/runtime/model
adapters.
