# Issue #11: Procurement Intelligence Lab adversarial adoption dogfood

## Outcome and why it matters

`VERIFIED` — The 0.5.0 adopter safely overlaid a disposable clone of Procurement Intelligence Lab
at `0f9d1a45af078ebf969f9ced11fc2e93adb542d0` without modifying any tracked application file. It
copied 74 upstream-owned files and surfaced 44 reconciliation gaps instead of overwriting
application governance, planning, CI, packaging, or tool modules.

`VERIFIED` — Preservation is not activation. The dogfood exposed three template defects that make
the copied harness provisional: false-active lifecycle state, application-module shadowing in the
copied validator, and copied tools that fail the application's authoritative formatter. These are
recorded separately as Template Issues
[#25](https://github.com/stauntonjr/agentic-project-template/issues/25),
[#26](https://github.com/stauntonjr/agentic-project-template/issues/26), and
[#27](https://github.com/stauntonjr/agentic-project-template/issues/27).

`VERIFIED` — Procurement's own semantic evidence remains strong: 221 unit tests, the real HTTP
integration boundary, a clean installed wheel, and all eleven executable historical-defect
challenges passed when run with their required local permissions. Every known-bad mutation was
rejected, including sparse XLSX coordinates and the shipped browser scope contract.

`VERIFIED` — A second clean clone at the identical commit passed the full authoritative
`make check`: format, lint, strict typing, architecture, semantic preflight, supply chain, all 236
tests, the 85% coverage ratchet at 89.95%, and documentation structure. This counterfactual proves
the adopted overlay—not Procurement main—introduces the Ruff failure.

`VERIFIED` — REST check-run inspection for the exact application commit shows successful static,
unit 3.12/3.13, coverage, contract, integration, regression, package-smoke, challenge-manifest,
CodeQL, and Dependabot checks. A separate scheduled
[roadmap stewardship run 32039041277](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/32039041277)
is red because its advisory Gemini review step failed after the durable planning snapshot succeeded;
it is not an application test result or merge gate.

## Planned versus completed

The plan was to exercise adopt mode on a current isolated checkout, preserve the application's
governance and separate wiki, replay a historical escaped defect, route unit/integration/package/
sparse-input/public-interface evidence, obtain Pi evidence, audit planning drift, and turn every
template defect into a bounded Issue.

Completed:

- `VERIFIED` — cloned current default-branch commit `0f9d1a4` into
  `/tmp/agentic-pil-adoption.jPkSXP/repo`; the authoritative checkout and wiki were not used as
  write targets;
- `VERIFIED` — rendered evidence-backed Python-data intake in `adopt` mode with no missing essential
  fields and no contradictions in the supplied project facts;
- `VERIFIED` — preserved every tracked application file; `git diff --name-status` remained empty;
- `VERIFIED` — exercised Procurement challenge manifests C001-C011 on current code and against
  their executable known-bad mutations;
- `VERIFIED` — ran package, real HTTP, Pi offline-registration, guarded broad Pi, and narrow
  read-only Pi evidence paths;
- `VERIFIED` — created separate correction Issues #25-#27 rather than folding repairs into this
  report or mutating Procurement;
- `VERIFIED` — the post-adoption live Project #6 audit reports no missing fields, labels,
  milestones, or managed views. The first retry exposed that host GitHub CLI 2.45 lacks the
  application's requested `gh api --slurp` flag; a disposable read-only pagination compatibility
  shim then ran the unchanged application planner to completion.

## User-visible and business-semantic changes

`VERIFIED` — There are no Procurement product, domain, data, API, CLI, HTTP, or policy changes. The
application clone contains untracked harness overlay files only. No application commit, branch, PR,
Issue, Project item, wiki page, deployment, or release was written.

`VERIFIED` — The intake restates existing repository evidence: the project is a public,
synthetic-data reference architecture; source assertions remain distinct from truth; original
project source is MIT; production procurement authority, confidential data, and unreviewed actions
remain out of scope. These are derived adoption records, not new product decisions.

## Architecture, schema, dependency, data, and interface changes

`VERIFIED` — No existing application file changed. Adopt mode added only missing files classified as
upstream-owned plus non-overwriting generated/proposal artifacts. Its gap report classified:

- five upstream-owned collisions;
- twelve harness tests deferred outside the application's test-discovery namespace;
- sixteen existing merge-required application paths;
- eleven missing merge-required template paths.

`VERIFIED` — The adapter left Procurement's `AGENTS.md`, `Makefile`, `pyproject.toml`, `uv.lock`,
workflows, planning contract, license, release policy, and application tools authoritative.

`VERIFIED` — The generated state nevertheless says `project.lifecycle: new` and
`project.status: active`, while the generated gap report says the adoption cannot be active until
collisions and merge-required surfaces are reconciled. Issue #25 owns this state-semantic defect.

`VERIFIED` — The copied `tools/harness_check.py` resolves `check_actions_supply_chain` through
Procurement's existing module and raises `ImportError` for the template-only `check_workflows` API.
Issue #26 owns the namespace/invocation boundary.

`VERIFIED` — Procurement's locked Ruff 0.16.3 discovers the copied `tools/pi_tool_probe.py` and
`tools/project_intake.py` and requires different formatting. Issue #27 owns adoption compatibility
with application-wide quality discovery; the application gate will not be weakened or silently
given ignores.

## Verification evidence and boundary proven

| Evidence | Result | Boundary proven |
|---|---|---|
| `project_intake.py --mode adopt --apply` | passed; 74 copied, 44 gaps | non-overwriting overlay and explicit reconciliation inventory |
| `git diff --name-status` in disposable clone | empty | no tracked application file changed |
| `uv sync --locked --all-groups` | passed after network-enabled retry | exact locked development environment is reproducible |
| `make unit` | 221 passed | application unit semantics |
| `make integration` | 1 passed after loopback-enabled retry | shipped browser form reaches the real HTTP boundary |
| `make package-smoke` | passed | sdist-to-wheel build, clean install, runtime resource, and advertised demo |
| `make challenges` | C001-C011 passed; every known bad rejected | current oracles and executable historical-defect rejection |
| clean-clone `make check` at the same commit | 236 passed; 89.95% coverage; all static/architecture/semantic/supply-chain gates passed | authoritative application main is green without the overlay |
| REST check runs for `0f9d1a4` | all deterministic application/CodeQL gates green; separate advisory roadmap review red | remote baseline agrees with local product evidence without hiding the advisory failure |
| C002 | current sparse-XLSX oracle passed; mutation rejected | missing XML cells do not shift business columns |
| C003 | current real-HTTP oracle passed; mutation rejected | default browser flow carries required project scope |
| C004 | current and known-bad package checks passed/rejected | clean wheel contains and runs its runtime fixture |
| `python3 tools/pi_adapter_check.py ...` | Pi 0.84.1 offline contract passed | copied extension registers strict questionnaire and bounded invalid-tool guard |
| `python3 tools/harness_upgrade.py status` | `ok: true`; matching/modified/missing paths classified | provenance lock preserves adoption divergence instead of treating application-owned paths as upstream matches |
| `python3 tools/product_version.py` | `0.1.0` from `pyproject.toml:project.version` | copied version resolver honors the application's SemVer source |
| `python3 tools/run_quality.py` | bootstrap passed, then formatter failed on the same two copied tools | profile dispatch reaches Procurement's authoritative command and reports the overlay incompatibility |
| native `make github-plan-audit` retry | failed before comparison because host `gh` 2.45 rejects `api --slurp` | the failure is CLI compatibility, not planning drift |
| application planner via disposable read-only pagination shim | passed; zero missing fields, labels, milestones, or views; 25 fields, 103 items, 11 views | live Project #6 matches Procurement's desired planning contract without a Project write |
| broad Pi session `01a02fa1-6457-7db7-8d51-025655ef6494` | guarded abort | 15 reads followed by three unavailable `run` attempts; no unavailable tool executed and no unbounded loop continued |
| narrow Pi session `01a02fa2-97c3-7439-a07f-c8a3ec54fbf9` | `PROVISIONAL`; exactly two reads | model independently identified the active/provisional state contradiction |
| narrow Pi session `01a02fa2-fb62-733d-ad95-a7a598100b21` | `APPROVE C002 C003`; exactly two reads | model recognized both complete challenge manifests without executing them |
| report review session `01a02fa5-8e51-7000-8000-000000000011` | `APPROVE`; exactly one read | model found the pre-publication report complete, internally consistent, evidence-labeled, and honest about provisional adoption |

Failed attempts are part of the evidence:

- `VERIFIED` — the sandboxed `uv sync` could not resolve PyPI. The same locked command passed with
  approved network access; this was not a dependency-resolution failure.
- `VERIFIED` — sandboxed C003 could not create an ephemeral loopback socket. The exact integration
  and challenge commands passed with approved local-socket access; this was not a product failure.
- `VERIFIED` — `python3 tools/harness_check.py` fails at import because of the application tool
  collision. This is a template adoption failure and remains unresolved under Issue #26.
- `VERIFIED` — `make check` stops at Ruff on two newly copied template tools. This is an overlay
  compatibility failure under Issue #27. The identical clean-clone command passes all 236 tests and
  every pre-test gate, so the failure is baseline-relative overlay evidence rather than an
  application regression.
- `VERIFIED` — a broad five-file Pi review did not complete, but the invalid-tool ceiling stopped
  the three unavailable calls. Two narrow two-file sessions completed cleanly. The supported local
  usage pattern remains narrow, explicit read-only lanes rather than a claim of general autonomy.
- `VERIFIED` — the first planning retry reached the milestone request but host `gh` 2.45 rejected
  the application's `--slurp` option. The disposable shim removed only that unsupported flag and
  decoded every paginated JSON value before invoking the unchanged read-only audit; the completed
  comparison reported no planning drift.
- `VERIFIED` — after the one-read report verdict settled, an unrelated globally auto-discovered Pi
  extension attempted its configured Trilium shutdown sync and failed certificate validation. It
  changed no repository or GitHub state and did not affect model evidence. The exact-candidate
  rerun disables global extensions and loads only the project adapter.

## Acceptance-criterion coverage, waivers, and revision-bound verifier verdict

| Criterion | Current state | Evidence |
|---|---|---|
| AC1 | passed | exact disposable clone, empty tracked diff, 44-gap report, untouched authoritative checkout/wiki |
| AC2 | passed | C002/C003/C004 current and known-bad executions; full C001-C011 challenge run |
| AC3 | passed with explicit failures retained | clean baseline primary check passes 236 tests at 89.95%; adopted unit, HTTP integration, package, and challenges pass; overlay primary check and harness validator expose template defects |
| AC4 | passed | rate-limit retry retained; native `gh` 2.45 incompatibility retained; completed application-planner audit reports no Project #6 drift |
| AC5 | passed | Issues #25-#27; no Procurement GitHub write |
| AC6 | passed | offline Pi contract, bounded broad-task abort, two successful narrow read-only sessions |

`VERIFIED` — Local Qwen approved the pre-publication report after exactly one permitted read and no
other model tool call. The exact post-lock candidate receives a separate revision-bound verdict in
the loop record. Pi remains model-review evidence, not human/risk approval or application activation.

## Baseline-relative write scope and violations

`VERIFIED` — The disposable application clone's tracked delta is empty. Harness overlay files are
untracked by design and remain outside the authoritative Procurement repository.

`VERIFIED` — The template loop declares only this report, `docs/project/handoff.md`, and
`harness.lock`. Exact candidate identity and scope violations will be recorded after the planning
retry and final edits.

## GitHub Issue, Project, PR, and release state

- `VERIFIED` — Template Issue #11 is open and its Project #13 item is In Progress.
- `VERIFIED` — correction Issues #25-#27 are open and are native sub-issues of #11. Project #13
  classifies #25 as In Progress/P0, #26 as Todo/P0, and #27 as Todo/P1; all three are Platform,
  Ready, Medium-risk Bugs with Evidence Required.
- `VERIFIED` — no Procurement Issue, Project #6 item, PR, release, tag, or repository file was
  mutated.
- `VERIFIED` — no template PR, merge, release, or tag exists for this report candidate yet.

## Risks, limitations, failures, and unverified claims

- The overlay is provisional. A complete intake questionnaire does not resolve code/module, test,
  CI, policy, release, license, planning, or dependency merge boundaries.
- Application-wide discovery means untracked copied files can break quality commands even when
  tracked files are untouched.
- The copied validator cannot currently diagnose this repository because of a module-name collision.
- Local Qwen completed narrow two-file reviews but failed the broader synthesis prompt. The guard
  bounds unsafe retry behavior; it does not guarantee task success.
- Global Pi extensions can add unrelated shutdown side effects; exact verifier lanes therefore
  disable global extension discovery and load only the project adapter.
- Procurement's native planning command currently requires a newer GitHub CLI than host `gh`
  2.45 for `api --slurp`; the read-only compatibility shim proves current planning convergence but
  does not repair that application-tool portability limitation.
- Public C001-C011 oracles are semantics coverage, not a held-out agent score.
- The separate wiki has pre-existing uncommitted documentation work and was deliberately left alone.

## Decisions or authorization needed

No application decision is required for this report. Activating the harness in Procurement would
require a separate application-owned Issue and explicit authority to reconcile its governance,
tool namespace, tests, quality discovery, CI, planning, and release surfaces. This dogfood does not
grant that authority.

## Recommended next loop

1. Repair Issue #25 so adopt-mode state stays provisional until reconciliation is complete.
2. Repair Issue #26 with an isolated harness tool/import boundary and a real collision regression.
3. Repair Issue #27 with a derived-repository quality-discovery regression without weakening the
   application gate.
4. Re-run this exact Procurement adoption after those fixes, then decide whether a reviewed
   application-owned adoption issue is worthwhile.
5. Continue the scheduled S3NTINEL and Kortex dogfoods only after the adoption boundary is stable.

## Exact revision and change scope

- Template start commit: `d691f5e7d6bfa71f56554b07a90a86ecf8d817d7`.
- Template branch: `issue-11-procurement-adoption-dogfood`.
- Template loop: `20260823T172051Z-d691f5e7`.
- Application snapshot: `0f9d1a45af078ebf969f9ced11fc2e93adb542d0`.
- Disposable clone: `/tmp/agentic-pil-adoption.jPkSXP/repo`.
- Publication commit: recorded by the linked Issue and PR because a commit cannot embed its own
  content-derived identity.
- Product release impact: `none`; this is a report-only evidence update with no harness or
  application behavior change.
