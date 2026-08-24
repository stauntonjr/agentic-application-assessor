# ADR-0003: Add Pi as an experimental reference adapter

- Status: accepted
- Date: 2026-08-21
- Deciders: repository owner
- Governing issue: bootstrap-provider-adapters

## Context

Pi is intentionally a small coding-agent harness with native project instruction, Agent Skills, prompt-template, extension, SDK, and RPC surfaces. Its ecosystem demonstrates active demand for questionnaires, planning, subagents, audited loops, resumability, and reports. However, most packages implement runtime behavior rather than portable repository governance, and project extensions execute with the launching user's permissions.

This template already separates provider-neutral authority, roles, loops, skills, evidence, and GitHub state from Codex-specific role definitions. A Pi integration can exercise that portability, but importing an opinionated Pi distribution would add supply-chain authority and duplicate canonical contracts.

## Decision

Add Pi as an experimental, thin, repository-local adapter:

- Keep `AGENTS.md`, `.agents/skills/`, `harness/roles/`, and `harness/loops/` canonical.
- Use `.pi/settings.json` only for project-local resource discovery and ignored session storage.
- Provide prompt templates that route intake, research, engineering-loop, and report requests to canonical skills.
- Provide one dependency-free TypeScript extension for structured context-readiness questions.
- Install no third-party Pi packages and select no project-wide model or provider.
- Record Pi capabilities and limitations in `harness/adapters/pi.json`.
- Require a separate trusted session or another authorized verifier when independence is required; do not claim Pi core provides subagent isolation.

## Consequences

### Positive

- The same repository contracts work through both Codex and Pi discovery conventions.
- Pi users receive native workflow commands and focused questionnaire UI without copied skill logic.
- Provider-specific capability gaps become machine-readable and testable.
- The initial adapter adds no third-party runtime package or package-update channel.

### Negative

- Pi prompt templates mediate roles and loops rather than enforcing the whole state machine in the runtime.
- Independent verification requires a separate session or an explicitly reviewed orchestration extension.
- The project-local extension adds executable code that must be reviewed before repository trust is granted.
- Fast-moving Pi APIs require version-specific compatibility checks.

### Risks and mitigations

- Extension privilege: keep the extension small, dependency-free, validated, and covered by the repository trust warning.
- Canonical-contract drift: validate every adapter mapping and require prompts to reference canonical skills.
- False capability claims: declare unsupported delegation, verification, and sandbox boundaries in the adapter manifest.
- Personal preference leakage: do not set model, provider, thinking, or enabled-model preferences in project settings.

## Alternatives considered

| Alternative | Evidence | Reason not selected |
|---|---|---|
| Adopt a full Pi harness distribution | Several projects bundle workflows, roles, and policy | Duplicates canonical state and expands dependency trust before a local need is proven |
| Vendor Pi's official subagent example | Demonstrates isolated Pi subprocesses | Example code is not a stable core contract and would materially expand this adapter |
| Add `.pi/agents` files only | Common extensions discover this convention | Pi core does not execute those files, so their presence would overstate support |
| Defer Pi entirely | Codex already exercises one adapter | Misses a strong portability test and the requested questionnaire ergonomics |

## Verification and revisit trigger

`make smoke` must validate adapter manifests, Pi settings, canonical mappings, prompt routing, and questionnaire guardrails. Exercise resource loading against Pi 0.84.1 without installing packages or invoking a model. Revisit experimental status after a real project completes intake, implementation, separate verification, and evidence reporting through Pi, or when Pi exposes a stable native role/delegation contract.
