# Issue #4 Macro Technical Pulse dogfood report

## Outcome

The complete deterministic workflow ran against a clean, detached checkout of Macro Technical
Pulse `main` at `1f06504d850d1160bef9fa6228c3ebdc4e8f02ae`. Jack Rory Staunton reviewed and
accepted the application requirements on 2026-08-25. Questionnaire generation, answer
reconciliation, Agentic Repo Auditor import, canonical JSON assessment, and Markdown rendering all
completed without changing the target.

The run is successful as a safety and provenance exercise, but it also exposes an important product
limit: Agentic Application Assessor `0.1.0` is not yet a comprehensive application-understanding
tool. It inventories bounded repository evidence and safely imports Auditor findings, but the final
assessment promotes only the accepted purpose and stakeholder statements. It does not yet use the
accepted priorities, constraints, risk tolerance, deployment context, or evidence expectations to
explain the application's architecture or to rank gaps. It also has no accepted component, data
asset, workflow, or quality-scenario declarations to analyze.

That limitation is a product finding, not a reason to reinterpret Macro Technical Pulse as a
governance project. The application roadmap below follows the owner's stated product objectives.

The first exact schema validation also caught a direct compatibility defect: the Assessor correctly
emitted context schema `1.1` in its input descriptor, while the public report schema still required
`1.0`. This candidate widens that descriptor to the two supported context versions and adds an
end-to-end regression using a reconciled schema-`1.1` context. The report schema itself remains
`1.0` because the change makes its existing descriptor truthful rather than changing report shape.

## Exact evidence boundary

- Target: clean disposable checkout of
  `stauntonjr/macro-technical-pulse@1f06504d850d1160bef9fa6228c3ebdc4e8f02ae`.
- Target identity: Assessor
  `sha256:f88420a4169764cdf464b0d286cf7ec57e80d5f17e65706c833e41831fe1581f`;
  Auditor `sha256:5725e4ff07db889061f00d3b37a08bb2d883b7929ef4de538bb1543341cf2890`.
- Questionnaire: `sha256:4333b47be7a4694e0995f698345eea5b0fe19a672bfaef418608934a905f5bc9`.
- Owner answers: `sha256:0d1dca205e1de8297c5d88619ef69790de58378d0d557a2812e9ce4619104185`.
- Accepted context: schema `1.1`,
  `sha256:0065cafb9a92036cfe6dc4d06e033df3d6009820c4aaeec38f6f7eeef9f8be76`.
- Auditor artifact: Agentic Repo Auditor `0.1.0`, schema `1.2`,
  `sha256:93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`.
- Assessment JSON: Agentic Application Assessor `0.1.0`, schema `1.0`,
  `sha256:fff4358a7342e5da4b29ee008e4b482b081b39963e3f4b5d3591ee6f45ec5290`.
- Assessment Markdown:
  `sha256:8a5e60a612aea8e3d5e974e12096a52d2046215dbf67e8bf216a7b9defd9b917`.

Two fresh assessment executions reproduced the tracked JSON and Markdown byte for byte. The target
remained clean and at the same revision after generation. Neither product executed target code,
installed target dependencies, used target credentials, or wrote to Macro Technical Pulse.

## Owner-confirmed purpose

Macro Technical Pulse exists to capture and gather economic and market data streams, store them for
feature engineering and machine-learning price-prediction models, deploy trained models on live
streams, and visualize the collected data, engineered features, signals, and predictions.

Technical-response measurement is a possible later analysis of price sensitivity to external
signals. It is not the application's purpose and must not displace ingestion, storage,
visualization, feature engineering, model development, or deployment.

## Owner-confirmed delivery order

1. Establish reliable economic and market source-data collection and API consumption.
2. Define source-data schemas and database storage once ingestion is established.
3. Build visualization for collected data, features, signals, and predictions.
4. Develop feature-engineering pipelines.
5. Develop and validate machine-learning price-prediction models.
6. Deploy trained models on live data streams.
7. Later evaluate price sensitivity to external signals through technical-response analysis.
8. Defer comprehensive revision handling until a working prototype demonstrates the need.

Reproducibility remains useful where it protects model evaluation and source provenance, but a
general immutable-artifact replay system is not a prototype prerequisite.

## Verified repository evidence

The deterministic static collector found 27 documentation files, two entrypoint signals, one
manifest, and four tests. It found no recognized static deployment or interface evidence. Those
counts prove only that bounded files were present; they do not prove runtime behavior, production
topology, feature correctness, model quality, or operational readiness.

The imported Auditor artifact contains 13 findings: four pass, eight warn, and one fail. The high
finding is mutable third-party GitHub Actions references. The warnings cover repository-instruction
wording, the absence of `.agents/skills`, contribution/security/dependency-update/CodeQL policy,
the lack of a recognized project contract, and the lack of a machine-readable primary check.

Those findings remain `imported-tool` evidence. The Assessor does not promote them into application
claims. Some are useful hygiene work, especially immutable Actions references. Others need product
context: Macro Technical Pulse uses `.codex/skills`, so the `.agents/skills` warning is not evidence
that it lacks project skills. None of these hygiene findings should supersede the owner-confirmed
product roadmap.

## What the assessment could establish

- The exact target and every imported artifact are digest-bound.
- The accepted context distinguishes repository observations from owner declarations.
- The owner-confirmed purpose and stakeholders appear as supported, human-declared claims.
- Auditor configuration, summary, findings, and nested evidence retain exact JSON-pointer and
  artifact-digest provenance.
- No contradiction was recorded in the owner review.
- Unknowns are explicit rather than filled with model inference.

## What remains unknown

Owner-review unknowns:

- database technology and storage topology;
- live-stream providers, latency requirements, and service-level objectives;
- model serving, retraining, promotion, rollback, monitoring, and retirement policies;
- monetary budget and delivery deadline.

Assessor unknowns:

- accepted component boundaries;
- data assets, schemas, ownership, retention, and movement;
- important runtime workflows;
- decision-driving quality scenarios;
- runtime behavior and production topology;
- static deployment and interface evidence;
- model-assisted synthesis, which is intentionally outside the deterministic `0.1.0` core.

These unknowns are not equal. Database design becomes an immediate product decision after working
source ingestion. Model operations and revision handling can remain open until their prerequisite
prototype stages exist.

## Product findings for Agentic Application Assessor

### 1. Accepted requirements are preserved but underused

The questionnaire captures priorities, constraints, risk tolerance, deployment context, and
evidence expectations. The assessment report records the context artifact and digest but turns only
purpose and stakeholders into claims. A comprehensive report should summarize the remaining
accepted requirements, use them to distinguish relevant from incidental findings, and retain their
human-declared provenance.

### 2. The questionnaire does not fill the architectural context it later reports as missing

The gap-only questionnaire asks eight high-level questions. It does not gather components, data
assets and movement, important workflows, or quality scenarios even though the assessment explicitly
expects those context sections. A later questionnaire version should gather these progressively,
without requiring an exhaustive architecture exercise before a prototype.

### 3. Static analysis is inventory-level, not semantic

File counts and entrypoint heuristics are useful evidence routing, but they do not explain data
flows, source adapters, schema evolution, persistence, visualization, feature generation, model
training, or serving. The next product slice should add bounded, evidence-backed analyzers for the
application's real artifacts rather than use an unconstrained summary model.

### 4. Finding prioritization needs owner-goal alignment

Repository-security findings and missing policy files are real, but a comprehensive executive
assessment must not allow them to crowd out the product's ingestion, storage, visualization, and ML
objectives. Findings should be ranked by accepted objectives, dependencies, risk, and prototype
stage, with their origin preserved.

### 5. Dogfood repaired report/context schema compatibility

The canonical MTP report initially failed Draft 2020-12 validation only because its truthful
context input version was `1.1`. The public assessment-report schema now accepts both supported
context versions, and a regression validates a real reconciled `1.1` assessment against that
schema. This is a compatibility repair discovered by the complete workflow, not an MTP finding.

## Bounded follow-up

For Macro Technical Pulse, continue its existing planner-owned roadmap rather than create duplicate
Issues from this dogfood. The immediate planning sequence is source ingestion and API consumption,
then schemas and database storage. Existing project work should be audited before any new item is
created. Pinning mutable GitHub Actions is a small, independently bounded security repair.

For Agentic Application Assessor, one follow-up should add requirement-aware reporting and a
progressive architecture/data-flow context pass. Model/runtime adapters remain later roadmap items;
they are not required to recognize the deterministic core's present semantic gap.

## Acceptance map

| Criterion | Candidate evidence |
|---|---|
| AC1 | Exact-target questionnaire and accepted schema-`1.1` context preserve observed recommendations, owner declarations, source, date, status, contradictions, and unknowns. |
| AC2 | Fresh JSON and Markdown runs match the tracked SHA-256 digests byte for byte; target revision and clean state remain unchanged. |
| AC3 | Canonical Auditor `0.1.0` schema-`1.2` artifact imports with exact digest/pointers and no claim promotion. |
| AC4 | This report separates verified evidence, owner declarations, imported findings, unknowns, product limitations, and staged priorities; MTP was not mutated. |
| AC5 | The exact artifacts validate after repairing report/context-version compatibility; authoritative checks and independent review remain required before integration. |

## Release impact

Recommended product release impact: `patch`. The public report schema is widened to accept the
already supported context versions `1.0` and `1.1`; the report shape, CLI, runtime behavior,
dependencies, and product version do not change. No tag, package publication, deployment, or MTP
change is authorized by this report.
