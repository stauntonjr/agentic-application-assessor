# Macro Technical Pulse dogfood report

Issue: [#3](https://github.com/stauntonjr/agentic-project-template/issues/3)
Harness run: `20260823T133820Z-cf31c78d`
Application snapshot: Macro Technical Pulse Issue #6 at `b41e3bc`
Final disposable checkout: `/tmp/agentic-mtp-dogfood-r5-final.WoKp8Y/app`

## Outcome and why it matters

The one-repository adoption path preserved Macro Technical Pulse's tracked application
bytes and exposed its unresolved license as the only essential intake gap. Dogfooding also
found eight unsafe intake/adoption behaviors and three Pi/provider limitations before the template
was used on a live application repository.

The application repository, its GitHub Issues, and its Projects were not mutated. This report
describes an isolated snapshot and the template changes required to make adoption fail safely.

## Planned versus completed

Completed:

- cloned the clean Macro Technical Pulse Issue #6 worktree into an isolated temporary checkout;
- ran adopt/gap-only intake and generated an explicit reconciliation report;
- preserved all tracked application bytes and re-ran the application's 44 tests;
- exercised context readiness, research, engineering-loop, and executive-report Pi paths with
  Pi 0.84.1 and a local SparkRun model;
- implemented regressions for non-overwriting adoption and application-owned planning validators.

Not yet complete at this report revision:

- independent revision-bound verification of the template candidate;
- publication and canonical Issue/Project closure.

The revision-2 candidate completed its full harness smoke, lock reconciliation, offline Pi
compatibility check, and live read-only MTP planning audit before review. Revisions 3 and 4 then
repeated the safety regressions and fresh MTP adoption after repairing the regular-file-ancestor
defect and the CLI target-root-symlink normalization bypass.

## User-visible and business-semantic changes

Adoption now copies only paths classified as `upstream-owned`. It does not silently install a
template license, changelog, dependency lock, active workflow, merge-required policy file, or
harness test suite into an existing application. Every deferred or conflicting path is listed in
`docs/project/adoption-gaps.md` for explicit reconciliation.

Independent revision-1 review found that the first repair still followed target-directory
symlinks and overwrote pre-existing generated/proposal/report paths. Revision-2 review then found
that an existing regular file used as a target ancestor caused a partial copy before failure.
Revision 3 preflights every copy and output path, rejects a symlink target root, symlink traversal,
and non-directory ancestors before any copy, selects a proposal path without overwriting the
canonical artifact, and refuses when both canonical and proposal paths already exist. Local review
then found that the revision-3 CLI resolved its target before validation and erased root-symlink
evidence. Revision 4 preserves the lexical absolute target and validates every target-root ancestor.
Revision-4 adjacent review found that greenfield copy entered its mutation phase before invoking
that validation. Revision 5 gives both adoption and new-project copy the same pre-copy root check.

An application-owned `tools/github_planning.py` can remain authoritative. Harness validation uses
that trusted module's `load_config(path)` boundary when it does not implement the template's
`validate_contract` function, and fails closed if the application validator rejects the contract.

## Architecture, schema, dependency, data, and interface changes

- `tools/project_intake.py` uses `harness/ownership.json` as the copy policy.
- Adoption output selection is non-overwriting and all copy/output paths are checked for symlink
  traversal before mutation.
- `harness/ownership.json` classifies the planning implementation as `merge-required` and the
  generated lock as `upstream-owned`.
- `tools/harness_check.py` supports a narrow application-validator compatibility boundary.
- No application data model, package dependency, provider, or GitHub planning contract changed.
- No external model provider or paid API was used for the Pi lane.

## Adoption evidence

The final revision-5 isolated retry copied 78 upstream-owned files and reported 38 paths requiring human
reconciliation. It did not copy `LICENSE`, `CHANGELOG.md`, `uv.lock`, active harness workflows,
or harness tests. `git diff --exit-code` remained clean for tracked Macro Technical Pulse bytes,
and all 44 pre-existing application tests passed with
`PYTHONPATH=src python3 -m unittest discover -s tests -v`. A retry without the application's
`PYTHONPATH=src` boundary failed import discovery and is not counted as application evidence. A
later revision-4 retry was initially launched from the template checkout and correctly failed its
then-stale lock check; it too is rejected as application evidence. The command rerun from the exact
disposable application root passed all 44 tests.

The generated intake remained provisional because `constraints.licenses` is unresolved. This is
the correct activation boundary: absence of a license is a human decision, not permission to copy
the template's MIT license.

This boundary is consistent with the researched ecosystem patterns. GitHub documents that a
repository created from a template starts with copied files and unrelated history, not a maintained
update relationship. Copier provides an answer/provenance file and three-way update behavior, but
still requires manual review when it cannot reconcile a conflict. These sources support explicit
ownership and reconciliation; neither grants permission to overwrite application policy.

Primary references:

- [GitHub: Creating a repository from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template)
- [Copier: Updating a project](https://copier.readthedocs.io/en/stable/updating/)

## Pi and SparkRun evidence

The lane ran on DGX host `spark-3a8f` using:

- SparkRun 0.2.40;
- Docker-hosted vLLM `0.26.1rc1.dev1105+g040700aaa.d20260822`;
- `Intel/Qwen3-Coder-Next-int4-AutoRound` from the existing host cache;
- Pi 0.84.1 provider `local-vllm` at `http://127.0.0.1:8000/v1`;
- Pi session `248f2f09-8ea2-48d3-8412-1d96e949ebc7` stored outside the repository.

Pi's official custom-model documentation explicitly supports vLLM through an
OpenAI-compatible provider and documents provider-specific compatibility flags:
[Pi custom models](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/models.md).

The direct endpoint returned `LOCAL_SPARKRUN_OK`; Pi then returned
`PI_LOCAL_SPARKRUN_OK` with all tools and repository resources disabled. The reviewed adapter run
explicitly loaded `.pi/extensions/context-readiness.ts`, repository-local skills, and workflow
prompts. Its initial tool set was read-only: `read`, `grep`, `find`, `ls`, and
`harness_questionnaire`.

### Pi sequence results

1. **Intake — recovered:** the adapter invoked `harness_questionnaire`; print mode correctly
   reported that structured UI was unavailable, and the model asked the sole license question
   directly.
2. **Research — inaccurate:** the model preserved the safe no-license boundary, but claimed
   primary-source research while offline, assigned high confidence without evidence, and described
   MIT as providing an implicit patent grant. Those statements are reported model output, not
   accepted research evidence.
3. **Loop attempt — interrupted:** Qwen repeatedly called unavailable tool names, including 147
   `run_shell_command` calls. Pi returned a tool-not-found result each time; no command executed.
4. **No-tools retry — failed:** Pi sent an empty `tools` array and vLLM returned HTTP 400 because
   that endpoint requires the field to be omitted or non-empty.
5. **One-read-tool retry — recovered:** with only `read` advertised and an instruction not to call
   tools, the model produced a bounded handoff that kept the license unresolved and mutations at
   zero.
6. **Report — completed with review required:** the model separated verified, reported, and
   inferred claims, but misidentified itself as the model identity and included several claims that
   need independent confirmation.

The session contained no `bash`, `edit`, or `write` tool. Invalid tool names were rejected by Pi,
so the runaway attempt did not cross the read-only boundary.

## Acceptance-criterion coverage

| Criterion | Current status | Evidence |
|---|---|---|
| AC1 | candidate passed; independent verdict pending | Fresh revision-5 adoption preserved tracked bytes, emitted reconciliation gaps, passed 44 application tests, rejected target-root and descendant symlinks plus non-directory ancestors, and preserved existing generated artifacts. |
| AC2 | candidate passed; independent verdict pending | Intake found the license gap. Unsupported local-model research was rejected, while the accepted adoption boundary is grounded in the cited GitHub, Copier, and Pi primary documentation. |
| AC3 | candidate checks passed; independent verdict pending | Criterion-linked tests, full smoke, ownership lock, and Pi compatibility checks pass through revision 7; the required independent final verdict is the remaining gate. |
| AC4 | candidate passed with recorded limitations | Genuine Pi 0.84.1/SparkRun intake-to-report execution completed after two recorded retries and no GitHub writes. |
| AC5 | candidate evidence complete; publication pending | Corrections, retries, escaped revision-1 through revision-4 gaps, model limitations, accepted evidence, and canonical planning state are recorded. Elapsed time from run start through the revision-7 candidate was 1 hour 58 minutes. |

No waiver is proposed. A Pi-authored report is not an independent verifier verdict.

## Baseline-relative write scope

Template changes are limited to the declared run paths. The isolated application checkout contains
generated adoption artifacts, but no tracked application delta. No write-scope violation is known
at this report revision.

## GitHub and release state

- Template Issue #3 and its Project #13 item are the canonical work item.
- The item is In Progress.
- Macro Technical Pulse retains its existing Issues and Projects; no duplicate roadmap was created.
- No PR or release has been created for this loop.
- The changes remain under the unreleased harness 0.5.0 line; no version bump is proposed.

## Risks, limitations, and failures

- The owner selected MIT after this dogfood; applying that decision to the application remains a
  separate, reviewed application change.
- Local Qwen tool-name adherence was insufficient in this original session. Follow-up Issue #23
  adds strict sampling plus a deterministic unavailable-tool ceiling and re-tests the model.
- Pi 0.84.1 `--no-tools` continuations with prior tool history remain incompatible with this vLLM
  endpoint because Pi serializes an empty tool list; Issue #23 documents the tested safe pattern.
- SparkRun's user service helper scripts lacked executable permission and had never loaded the
  configured model successfully; their owner execute bits were repaired on the DGX host.
- The SparkRun proxy did not auto-register the healthy port-8000 backend. Pi worked because its
  existing `local-vllm` provider connects directly to port 8000.
- Pi research output requires the same evidence and verifier gates as any other implementer output.
- Revision-1 independent review escaped two adoption defects: target symlink traversal and
  overwriting existing generated/proposal/report paths. Revision-2 review found the separate
  regular-file-ancestor partial-copy defect. Local revision-3 review found the separate CLI
  root-symlink normalization bypass. Revision-4 adjacent review found the greenfield copy-order
  inconsistency. Revision-5 regressions and a fresh MTP adoption passed; revision 6 is the
  report-accuracy correction. Publication staging then exposed six Markdown hard-break spaces that
  the unstaged-file whitespace check had not inspected; revision 7 removes them and requires an
  indexed-diff check before the final exact-digest confirmation.

## Decisions or authorization needed

- Post-loop decision: on 2026-08-23, Macro Technical Pulse's owner selected MIT. This report records
  the decision but does not claim the application repository has already been relicensed.
- Follow-up Issue #23 owns the Pi/vLLM strict-tool, invalid-call ceiling, and empty-tool continuation
  work; those changes remain separate from the completed adoption fix.

## Recommended next loop

Obtain an independent verdict on the pinned revision-7 candidate. Publish and close the canonical
Issue/Project item only if all Issue #3 criteria pass; otherwise revise against the verifier's
reproduction and repin.

## Exact revision and scope

Start commit: `cf31c78d449068a98aaf7562579b35ed1f418961`
End commit: pending
Template branch: `main`
Application snapshot: `b41e3bc`

## Post-loop application reconciliation — 2026-08-23

The current-state claims in this section supersede the report's earlier pending-state statements;
they do not rewrite what the isolated dogfood knew or changed at run time.

- The Macro Technical Pulse owner selected MIT after the isolated dogfood, then applied that
  decision through [MTP Issue #30](https://github.com/stauntonjr/macro-technical-pulse/issues/30)
  and [PR #31](https://github.com/stauntonjr/macro-technical-pulse/pull/31).
- PR #31 merged to MTP `main` as `1f06504d850d1160bef9fa6228c3ebdc4e8f02ae`; default-branch
  [CI run 32653405251](https://github.com/stauntonjr/macro-technical-pulse/actions/runs/32653405251)
  passed, Project #7 records the work Done with Evidence Approved, and the post-write planning
  audit reported 26 configured items with zero drift.
- GitHub's repository-license endpoint identifies the application `LICENSE` as SPDX `MIT`.
  MTP ADR 0010 limits that grant to original project source and documentation; it does not
  relicense third-party software, provider payloads, market data, exchange observations, derived
  datasets, trademarks, or preserved legacy artifacts.
- The license gap that correctly kept the isolated intake provisional is therefore resolved on
  the application default branch. This does not claim that the full reusable harness was adopted
  into MTP, nor does it retroactively make the dogfood checkout active.
- Template Issue #23 separately published the Pi tool-call hardening as `d118dad`; the original Pi
  failures above remain preserved as historical evidence rather than being rewritten as successes.
