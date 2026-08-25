# ADR-0009: Digest-bound, owner-accepted requirements questionnaire

- Status: accepted
- Date: 2026-08-25
- Decider: human owner
- Governing work item: [GitHub Issue #3](https://github.com/stauntonjr/agentic-application-assessor/issues/3)

## Context

Static repository evidence cannot establish product intent, priorities, constraints, risk
tolerance, deployment reality, or the evidence standard an owner expects. Asking the entire
question bank on every run wastes owner attention, while allowing repository observations or
agent inference to become accepted declarations would break ADR-0008's provenance boundary.

The workflow must remain useful to weaker agents: stable question identifiers, bounded artifacts,
explicit transitions, and deterministic failure behavior are preferable to an unstructured chat
transcript. A draft must be reviewable without becoming accepted assessment input.

## Decision

Add two versioned artifacts and one backward-compatible context revision:

1. Questionnaire schema `1.0` binds stable gap-only questions to the exact Git target, optional
   accepted-context digest, bounded repository evidence, and observed defaults.
2. Answer schema `1.0` binds duplicate-key-free owner answers to the exact questionnaire bytes and
   records source, date, contradictions, and unknowns.
3. Context schema `1.1` adds durable requirements, application provenance, contradictions, and
   unknowns. It supports a reviewable `draft`, but the assessment command continues to require
   `review.status=accepted`. Existing accepted schema-`1.0` context remains valid.

`questionnaire` asks only unresolved stable IDs. Accepted declarations are never offered for
replacement. A narrowly observed package name is attached as a recommendation but never suppresses
the owner-acceptance question or becomes intent by itself. `reconcile` emits a draft by default. It emits accepted context only when
the caller explicitly supplies both owner identity and acceptance date; this is auditable
declaration provenance, not authentication. That explicit transition accepts the rendered packet,
including any preserved unknowns; it does not pretend every gap was answered.

Every artifact is bounded, regular, non-symlink JSON. Reconciliation rechecks exact target state
and input digests. The workflow does not call a model or network, execute or install target code,
or write the target repository. Output exists only on standard output; the caller decides whether
and where to save it.

## Alternatives considered

- Agent-only conversational intake: rejected as the canonical record because it lacks stable
  identity, deterministic validation, and portable review evidence.
- Treat repository metadata as human intent: rejected because observation is not declaration.
- Allow `assess` to consume drafts: rejected because provisional answers would be promoted to
  human-declared claims.
- Overwrite accepted context during reconciliation: rejected because it hides contradictions and
  bypasses owner decision authority.

## Consequences

- Owners can review a deterministic draft and leave unknowns unresolved before acceptance.
- Repository evidence contextualizes questions without acquiring declaration authority; only
  accepted context removes a stable question.
- Explicit acceptance records provenance but does not authenticate the named owner.
- Schema `1.1` is additive, but CLI commands and public schemas expand the product contract.

## Verification and revisit criteria

Verify deterministic reruns, accepted-context gap reduction, observed-default provenance, explicit
acceptance, schema/custom-validator parity for questionnaire `1.0`, answers `1.0`, and context `1.1`,
no-overwrite behavior, stale target/context/questionnaire rejection, duplicate keys,
malformed/deep/oversized/symlinked inputs, and sanitized CLI failures. Legacy context `1.0` schema
and custom-loader behavior remain compatibility-preserved rather than parity-normalized: their
pre-existing differences are outside this decision's scope.
Revisit before adding interactive prompting, authenticated signatures, private preference storage,
or model-assisted answer synthesis.
