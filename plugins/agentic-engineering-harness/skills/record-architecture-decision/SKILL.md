---
name: record-architecture-decision
description: Create or supersede a durable architecture decision record with evidence, alternatives, consequences, ownership, and revisit criteria. Use for material boundaries, technology choices, data models, autonomy, security, or operational policy; do not use ADRs for routine implementation status.
---

# Record architecture decision

Read `references/decision-criteria.md` and `docs/adr/000-template.md`.

## Procedure

1. Identify the governing Issue, human decider, decision deadline, and narrow boundary.
2. Inspect implemented behavior, current ADRs, constraints, benchmarks, and primary documentation.
3. Invoke `$agentic-engineering-harness:research-existing-solutions` when external patterns, standards, or alternatives materially affect the choice.
4. Separate observed evidence, assumptions, and unknowns.
5. Describe credible alternatives, including keeping the current design.
6. Record the decision, positive and negative consequences, risks, mitigations, verification, and revisit trigger.
7. Mark the ADR `proposed` until the authorized human or governance process accepts it.
8. On acceptance, update affected architecture docs, project contract, Issue, and handoff in the same loop.
9. To change an accepted decision, add a new ADR that supersedes it; do not rewrite history.

Use the next available four-digit number and a short kebab-case filename. Do not claim benchmark or production evidence that was not collected.
