# Outcome telemetry landscape

Research date: 2026-08-23.

## Decision and scope

Issue #17 needs a small, privacy-preserving way to describe engineering-loop outcomes without
turning this repository into an observability backend. The decision is whether to adopt an
existing telemetry protocol or adapt established metric and privacy conventions to the harness's
local JSON evidence model.

The scope is limited to seven outcome measures: human corrections, retries, escaped defects,
acceptance pass rate, active cycle time, wall-clock elapsed time, and accepted-change cost. It does
not include prompt traces, model responses, hidden reasoning, provider billing access, automatic
token collection, remote export, or organization-wide analytics.

## Search method

Queries covered OpenTelemetry metric identity and aggregation, OpenTelemetry generative-AI token
and cost conventions, sensitive-data guidance, opt-in attribute requirements, DORA lead-time
definitions, and NIST privacy data-minimization guidance. Primary standards, canonical
repositories, official documentation, and original program sites were preferred. Search results,
vendor blogs, and community telemetry products were used only to find primary sources and are not
evidence for this decision.

Comparison dimensions were semantic stability, provenance support, unit handling, local/offline
operation, privacy defaults, aggregation safety, implementation weight, and licensing.

## Candidate comparison

| Candidate | Useful evidence | Fit and boundary | License or provenance |
|---|---|---|---|
| [OpenTelemetry Metrics Data Model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/) | A metric stream has a name, unit, point kind, and attributes; compatible streams can be reaggregated across time and attributes. | Adapt its explicit name/unit/provenance and reaggregation principles. An OTLP SDK, collector, and exporter are unnecessary for this local slice. | OpenTelemetry specification, canonical project; repository materials are Apache-2.0. |
| [OpenTelemetry GenAI metrics](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-metrics.md) | The canonical conventions mark these metrics as Development and say token usage should be reported only when readily available. | Do not invent token or cost measurements. Keep absent values unavailable and defer provider-specific ingestion while conventions are still developing. | OpenTelemetry semantic-conventions repository, Apache-2.0. |
| [OpenTelemetry sensitive-data guidance](https://opentelemetry.io/docs/security/handling-sensitive-data/) and [opt-in attribute requirements](https://opentelemetry.io/docs/specs/semconv/general/attribute-requirement-level/) | Data minimization, purpose limitation, aggregation/anonymization, and opt-in treatment for risky or expensive attributes are explicit implementer responsibilities. | Adopt opt-in ingestion, a content-free allowlist, local stdout output, and de-identified aggregation. No claim is made that a schema alone prevents every operational disclosure. | Canonical OpenTelemetry documentation, Apache-2.0 project. |
| [DORA metrics](https://dora.dev/guides/dora-metrics/) | Change lead time measures commit-to-production delivery performance. | Use DORA only as a terminology boundary. Harness elapsed and active cycle time are not deployment lead time and are not labeled as DORA metrics. | Official DORA program guidance; referenced, not copied. |
| [NIST Privacy Framework](https://www.nist.gov/privacy-framework/privacy-framework) | A risk-based privacy framework supports identifying data-processing purposes and reducing unnecessary data handling. | Use as a governance cross-check for minimization and retention defaults, not as a certification claim. | Official U.S. National Institute of Standards and Technology publication page. |

## Findings

OpenTelemetry supplies the most relevant portable shape, but adopting its runtime would add an
export and dependency surface without solving the harness-specific questions of loop identity,
acceptance evidence, and human correction semantics. The useful part is the separation of metric
name, unit, value, attributes/provenance, and aggregation behavior.

Provenance cannot be collapsed into one numeric field. A provider receipt, a human count, a manual
estimate, and a missing observation have materially different evidentiary strength. The summary
therefore records `locally-measured`, `provider-reported`, `inferred`, or `unavailable` plus a
bounded method. Missing values remain null and unavailable; they are never silently converted to
zero or estimated.

Aggregation must preserve unit and provenance boundaries. USD, person-minutes, and compute-seconds
cannot be summed together. The local aggregate removes run identifiers, retains counts by origin,
and produces descriptive totals and extrema only within each compatible unit. It is an interchange
boundary for a future organization tool, not that tool itself.

Privacy is strongest when collection never starts. The CLI therefore reads only an explicit,
strictly allowlisted input document. It rejects content-bearing and secret-like field names, emits
to stdout by default, does not retain the raw input, does not contact a provider, and does not
export. Explicitly written summaries live only under ignored `.harness/telemetry/` and have
caller-managed retention.

## Build, adopt, adapt, and defer

- Build a dependency-free local summarizer and aggregate validator around the existing loop
  record, because acceptance, retries, and revision semantics are harness-specific.
- Adapt OpenTelemetry metric identity, unit separation, provenance labeling, and reaggregation
  principles without claiming OTLP compatibility.
- Adopt data-minimization and opt-in defaults from OpenTelemetry and NIST guidance.
- Defer OTLP exporters, collectors, remote storage, dashboards, provider token/cost adapters,
  billing APIs, and organization-wide analytics.
- Do not reuse DORA terminology for loop timing; deployment performance requires different event
  boundaries and evidence.

## Recommendation

Implement the narrow local JSON boundary in Issue #17. This gives projects stable schemas and a
testable privacy contract now, while leaving provider adapters and organization analytics to a
separate project that can choose its own access controls, retention policy, and storage model.

Confidence is high for the local boundary and medium for future interoperability. The core
OpenTelemetry metric model is mature, but the GenAI conventions are explicitly Development and
may change. A future spike should map a de-identified aggregate—not raw loop summaries—to the then
current OpenTelemetry conventions, test mixed-unit rejection, and obtain an explicit privacy and
retention decision before enabling any exporter.

## Unknowns and drift checks

- Provider-reported cost receipt formats and rights vary and were not inspected or integrated.
- No authoritative cross-provider accepted-change-cost semantic was found; the local schema keeps
  cost units explicit rather than asserting comparability.
- GenAI semantic-convention status and metric names are drift-prone. Recheck the canonical page
  before adding an adapter.
- Organization aggregation needs a separate threat model, minimum cohort policy, retention
  schedule, access model, and deletion path. Those are deliberately outside this repository slice.
