# Project charter

Status: active

## Purpose

A read-only, local-first Python CLI that compiles versioned evidence from an exact application repository, user-reviewed context, and supported analysis artifacts into deterministic JSON and Markdown assessments of purpose, architecture, interfaces, data movement, quality risks, contradictions, and unknowns.

Primary users:

- engineering leads onboarding to unfamiliar applications
- maintainers of agent-developed applications

## Outcomes and success measures

Desired outcomes:

- An evidence-backed map of application purpose, structure, interfaces, data movement, and important workflows
- Explicit contradictions, coverage gaps, quality risks, and investigation priorities without false completeness
- A safe handoff from repository-readiness evidence to application-level assessment

Success measures:

- Repeated assessment of unchanged inputs produces byte-identical canonical JSON and deterministic Markdown
- Every claim records an exact source, origin class, target identity, and derivation status or is explicitly unavailable
- Assessment changes no target file, Git metadata, network state, or external service
- Dogfood Agentic Repo Auditor first and Macro Technical Pulse second, producing at least one human-accepted follow-up decision
- make smoke passes locally and in CI

## Scope

### In

- Exact local Git target identity and bounded static repository evidence
- User-reviewed application context and quality scenarios
- Agentic Repo Auditor 0.1.0 schema-1.2 JSON import through a fail-closed adapter
- Versioned canonical evidence graph and deterministic Markdown assessment
- Evidence-labeled system-context and container-level architecture proposals
- Contradictions, coverage limits, unknowns, and prioritized follow-up questions

### Out

- Target code execution, dependency installation, builds, tests, or instrumentation in v0.1
- Network access, credentials, authenticated provider evidence, or live production telemetry in v0.1
- Model calls or model-scored findings in the deterministic v0.1 core
- Automatic remediation, compliance certification, security approval, or release-readiness claims
- Organization-wide aggregation

## Constraints

- Security: No secrets in the repository, No target writes or target-code execution in the v0.1 core, Reject symlink escapes and hostile repository-controlled Git helpers, Validate imported schemas, tool identity, artifact digests, and exact target state, Treat source, context, and reports as potentially confidential
- Data classification: potentially confidential source, architecture, domain context, runtime topology, and generated reports; local-only processing by default
- Deployment: local CLI; CI verification may be added within the read-only boundary; no hosted service or production deployment authorized
- Budget: v0.1 must require no paid external service and no external model spend
- Licensing: MIT

## Engineering and release contract

- Primary check: make smoke
- Dependency lock: uv.lock
- Coverage policy: branch-coverage-baseline-required-before-release
- Product versioning: semver at 0.1.0
- Version source: pyproject.toml:project.version
- Public contract: CLI arguments and exit statuses, application-context schema, canonical assessment-report schema, stable evidence and claim identifiers
- Harness version: 0.5.0

## Authority

- Autonomy level: supervised
- Network writes: explicit-human-approval
- Destructive actions: explicit-human-approval
- Release: human-only
- Policy changes: human-review

Generated from `harness/project.yaml` and `harness/intake.json`.
