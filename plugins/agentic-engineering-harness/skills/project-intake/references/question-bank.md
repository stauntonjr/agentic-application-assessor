# Question bank

Ask only questions that repository or GitHub evidence cannot answer. Use small batches in this order and skip irrelevant sections.

## 1. Identity and outcome

- What does the system do, for whom, and what problem does it solve?
- What measurable result defines the first useful release?
- What would make the project not worth continuing?

## 2. Scope and users

- Which capabilities and user journeys are in the first boundary?
- What is explicitly out of scope?
- Who owns product intent, architecture, risk, and release?

## 3. Domain and data

- Which terms, entities, states, invariants, and time semantics are authoritative?
- Which sources are public, licensed, private, synthetic, mutable, or revised?
- What provenance and retention must survive every transformation?

## 4. Quality and nonfunctional requirements

- What are the correctness, latency, availability, scale, accessibility, and recovery targets?
- Which public interfaces require end-to-end acceptance?
- What naive baselines, benchmarks, or held-out evaluations are required?

## 5. Security and autonomy

- What data classification, threat model, and compliance constraints apply?
- Which actions are advisory, reversible, externally visible, privileged, or destructive?
- Which actions always require a human?

## 6. Architecture and delivery

- Which constraints are settled and which need ADRs?
- What environments, deployment model, observability, migration, and rollback exist?
- What commands prove build, test, package, integration, and release boundaries?
- What one command must produce the same authoritative result locally and in CI?
- Which runtime, dependency lock, formatter, linter, type checker, test runner, coverage policy, and clean-package check apply?

## 7. Versioning and release

- What is being versioned independently from the harness: one product, independently versioned packages, or no release artifact?
- Which API, CLI, configuration, schema, artifact, or user-visible behavior is the public compatibility contract?
- Is SemVer, CalVer, independent component versioning, or no formal versioning appropriate?
- What file or system is the canonical product-version source, and what version starts the project?
- Before 1.0, how are breaking changes signaled, and what changelog or migration evidence is required?

## 8. Planning and economics

- Which repository, Issue, Project, milestones, and fields own the work?
- What schedule, budget, dependency, licensing, or operating-cost constraints apply?
- What agent outcomes will be measured: corrections, retries, defects, cycle time, or cost?
