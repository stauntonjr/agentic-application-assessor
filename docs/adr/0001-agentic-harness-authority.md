# ADR-0001: Separate portable harness contracts from provider adapters

- Status: accepted
- Date: 2026-08-21
- Deciders: repository owner
- Governing issue: bootstrap

## Context

Agent tools discover instructions, skills, roles, and permissions through different product-specific paths. Manually maintained copies drift. Large global instruction files also consume context even when most procedures are irrelevant.

## Decision

Keep authority, roles, loops, schemas, and project intent under `harness/` and `docs/`. Keep `AGENTS.md` as a short routing and invariant layer. Store reusable workflows in `.agents/skills/` for progressive disclosure. Provider-specific files, beginning with `.codex/agents/`, are thin adapters that point back to canonical contracts and may narrow but never broaden authority.

Keep Issues as canonical work objects. Treat GitHub Projects and generated loop reports as derived operational views.

## Consequences

### Positive

- Core governance remains portable across agent products.
- Skills load only when relevant.
- Authority drift can be detected by the harness validator.
- Provider adapters can evolve independently.

### Negative

- A new provider requires a small adapter and adapter validation.
- Some contracts are split across machine-readable and human-readable files.

### Risks and mitigations

- Adapter drift: validate referenced canonical role files in CI.
- Instruction overload: keep `AGENTS.md` short and move procedures into skills.
- False confidence: label report claims by evidence status.

## Alternatives considered

| Alternative | Evidence | Reason not selected |
|---|---|---|
| One large `AGENTS.md` | Easy to discover | Poor progressive disclosure and weak machine validation |
| Provider-specific full copies | Native integration | High drift and duplicated policy |
| External-only control plane | Central updates | Derived repos lose durable, reviewable local authority |

## Verification and revisit trigger

`make smoke` validates required canonical files, role adapters, skill metadata, and loop references. Revisit if a provider supports a stable shared role/loop manifest directly.
