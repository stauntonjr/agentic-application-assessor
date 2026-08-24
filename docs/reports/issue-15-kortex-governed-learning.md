# Issue #15: Kortex provenance and governed-learning dogfood

Issue: [#15](https://github.com/stauntonjr/agentic-project-template/issues/15)

Harness run: `20260823T195649Z-e5d7c3d4`

Application repository: [stauntonjr/kortex](https://github.com/stauntonjr/kortex)

## Outcome

`VERIFIED`: The read-only evaluation traces Kortex code, memory, preference, and architecture
authority without changing Kortex, deploying a model, or reading or writing its memory stores. It
adds one reusable forward scenario and a deterministic sanitized evidence fixture to the template.

`VERIFIED`: The Learn observation remains an unapplied Kortex-local proposal. Kortex's committed
ingestion code can extract user or system directives into provenance-linked durable memory, while
its architecture defers automatic policy rewriting and its directive schema has no review-state
field. Before a future consumer treats those nodes as policy, the proposal recommends an explicit
candidate, review, rejection, promotion, provenance, and rollback lifecycle. It has no human
authorization and did not change template or Kortex policy.

`VERIFIED`: Kortex's checkout, GitHub repository, services, model fleet, and data stores were not
mutated. The fixture stores only repository-relative evidence and concise conclusions; it contains
no transcript, prompt, hidden reasoning, environment values, private source, or live memory data.

## Provenance and authority trace

The public repository's default branch was `master` at
[`e0bf62b`](https://github.com/stauntonjr/kortex/commit/e0bf62b6bf6eaee033d3959c731fcd04104913c5)
when inspected. The local checkout was separately observed at committed head `49a1687`, five commits
ahead, with pre-existing uncommitted changes in `gateway/gateway.py`, `memory/ingest.py`, and
`tests/test_gateway.py`. Those three tiers are not interchangeable:

| Domain | Authority used | Explicit boundary |
|---|---|---|
| Code | The selected Git object, tracked source, and tests | Published `e0bf62b`, local committed `49a1687`, and local uncommitted work are separate evidence tiers. Dirty content is excluded from the fixture and publication claims. |
| Memory | `kortex/contracts.py`, `memory/schema.tql`, `memory/chat_ingest.py`, `memory/writeback.py`, `memory/service.py`, and tests | These files prove contracts and implementation, not live TypeDB, Qdrant, Redis, transcript, or embedding state. No store was queried. |
| Preferences | `AGENTS.md`, `docs/spec.md`, `docs/backlog.md`, and reviewed repository changes | Extracted directives and runtime environment values are inputs or derived memory, not approved repository policy. `variables.env` contents were not inspected. |
| Architecture | `AGENTS.md` names `docs/spec.md` as canonical; source, tests, `README.md`, `compose.yaml`, and `.project/spec.yaml` show implemented boundaries | Intended architecture is not running-system proof. No service health or model availability is claimed. |

Kortex deliberately treats chat history as application data and stores raw turns as durable memory.
That is a Kortex-local product rule, not permission for this harness to copy chat history into a
handoff or report. The dogfood fixture records only the distinction and the source paths.

## Learn phase and policy gate

The Learn phase produced `KORTEX-LOCAL-LEARN-001`:

- scope: Kortex only;
- status: `proposed`;
- human review required: yes;
- authorization: none;
- applied to Kortex: no;
- applied to template policy: no.

The regression test fails if that proposal is marked applied, authorized, or promoted. It also
checks the template's forward scenario forbids treating derived directive memory as approved
policy. This is evidence of the review boundary, not approval of the proposal itself. A Kortex
owner would need to open and review a separate application change before it could affect schema,
ingestion, retrieval, or policy consumers.

## Durable handoff and interrupted-session recovery

The fixture contains a concise structured handoff with a summary, failure boundary, preserved
paths, and next action. It declares `sanitized: true`, `contains_raw_transcript: false`, and
`contains_hidden_reasoning: false`; tests also reject transcript, prompt, and reasoning fields.

Two existing recovery contracts were replayed in fresh disposable repositories:

| Fixture | Result | Evidence |
|---|---|---|
| `R004` agent crash | PASS | Partial work persisted, one structured handoff survived process loss, and no destructive Git command ran. |
| `R006` reviewed resume | PASS | Partial work persisted; `human:fixture-owner` resumed into revision 2, attempt 1, state `understand`, with no destructive Git command. |

These exercises test template recovery behavior only. They do not interrupt Kortex or claim that a
Kortex service session was recovered.

## Reusable changes versus Kortex-local exceptions

Reusable template changes:

- `E010-governed-learning-provenance` tests authority tiers, governed learning, sanitized handoff,
  recovery, and local-policy isolation;
- `harness/fixtures/kortex-governed-learning-evaluation.json` pins the deterministic evidence;
- regression assertions prevent proposal promotion, transcript retention, boundary writes, and
  leakage of Kortex rules into universal policy;
- README, handoff, changelog, report, and lock metadata describe the new evidence.

Kortex-local exceptions that remain outside template policy:

- the gateway runs host-native through SparkRun while TypeDB, Qdrant, and Redis are support
  services;
- chat turns are intentional Kortex application data;
- NVIDIA AI Workbench metadata, GPU allocation, ports, aliases, and runtime environment values are
  application configuration;
- the ahead and dirty local checkout remains owner work and is excluded from adoption and
  publication claims.

## Acceptance-criterion coverage

| Criterion | Candidate evidence |
|---|---|
| AC1 | Four-domain authority matrix with distinct published, local committed, dirty, intended, implemented, and live-state boundaries. |
| AC2 | Unapplied Kortex-local Learn proposal with required human review and no authorization; deterministic assertions prevent silent promotion. |
| AC3 | Sanitized structured handoff with no raw transcript, prompt, or hidden reasoning. |
| AC4 | Fresh disposable `R004` and `R006` replays pass and preserve bounded partial work without destructive Git. |
| AC5 | Fixture and report list reusable template changes separately from four Kortex-local exceptions. |

No criterion waiver is proposed. Final completion still requires current-attempt harness checks,
an independent revision-bound verdict, integration, and publication evidence.

## Risks and limitations

- The local Kortex head and dirty paths may change after this snapshot; they are recorded only to
  prevent accidental authority conflation.
- No live memory data, service readiness, GPU behavior, model deployment, or end-to-end Kortex
  retrieval was inspected. This is a governance evaluation, not application verification.
- The proposed directive lifecycle is not a finding that current Kortex rewrites repository
  policy; no such consumer was observed. It is a required guard before that future capability.
- The template fixture is deterministic evidence about boundaries. It is not a substitute for a
  separately authorized Kortex implementation and review.

## Exact template scope

- Start commit: `e5d7c3d4cdb7bc8ed04b3eaf29f25f8699350667`
- Branch: `issue-15-kortex-provenance`
- Declared paths: fixture, evaluation scenarios/tests, this report, README, project handoff,
  changelog, and `harness.lock`
- Product release-impact recommendation: patch; this adds backward-compatible evaluation evidence
  and documentation without changing the harness runtime contract.
