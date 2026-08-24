# Issue #27: application quality discovery during adoption

## 1. Outcome and why it matters

`VERIFIED`: Existing-repository adoption can now compare an explicitly supplied application
quality command before and after harness files are copied. The intake and adoption-gap report
record the exact command, both exit codes, the compatibility classification, and copied paths named
by failing output.

`VERIFIED`: A missing check, an already-failing baseline, an execution error or timeout, or a
post-copy regression cannot look like a ready harness. Those outcomes keep adoption provisional
without mislabeling a pre-existing application failure as a harness regression.

## 2. Planned versus completed

`VERIFIED`: Issue #27's five acceptance criteria are implemented. Adopt mode has explicit
before/after discovery, incompatible or indeterminate results fail closed, copied Python sources
conform to the selected mature application's locked Ruff contract, deterministic regressions cover
the state transitions, and a fresh Procurement replay exercises the real application command.

`VERIFIED`: The selected sustainable boundary is source conformance for universal upstream-owned
Python files. No application ignore, lint configuration, dependency lock, or harness-only exclusion
was introduced.

## 3. User-visible and business-semantic changes

`VERIFIED`: Adopters opt in with `--adoption-check 'COMMAND'`. The command is tokenized without a
shell and runs from the application root once before copying and once after copying. It is not
guessed or run automatically.

`VERIFIED`: Quality compatibility and file reconciliation are independent evidence. A compatible
command does not activate an overlay with unresolved file gaps, and zero file gaps do not activate
an overlay whose application quality compatibility is missing, incompatible, or indeterminate.

## 4. Architecture, schema, dependency, data, and interface changes

`VERIFIED`: `harness/intake.json` adoption records add a required `quality` object with status,
command, baseline and adopted exit codes, incompatible copied paths, and a diagnostic. Active or
complete adoption requires quality status `compatible`; provisional adoption permits ordinary file
gaps, non-compatible quality evidence, or both.

`VERIFIED`: The CLI adds `--adoption-check` and `--adoption-check-timeout`. The option is rejected
outside adoption of an existing repository. The implementation adds no runtime dependency and
uses `subprocess.run` with an argument vector, captured output, a working-directory boundary, and a
finite timeout.

## 5. Verification evidence and boundary proven

`VERIFIED`: The historical Procurement reproduction at
`0f9d1a45af078ebf969f9ced11fc2e93adb542d0` used locked Ruff 0.16.3. Before conformance,
`uv run ruff format --check .` named `tools/pi_tool_probe.py`; `uv run ruff check .` reported 26
violations across 12 copied paths. Exact commands, paths, version, and the no-policy-change boundary
are pinned in `harness/fixtures/procurement-quality-discovery.json`.

`VERIFIED`: In a fresh disposable Procurement clone, `uv sync --locked --all-groups` installed the
locked environment. An unsandboxed baseline `make check` passed Ruff, Pyright, architecture and
challenge validation, 236 application tests including the loopback HTTP integration, 89.95% branch
coverage, the coverage ratchet, and all subordinate checks.

`VERIFIED`: The candidate adopter then ran exact command `make check` before and after copying 78
upstream-owned files. Both exit codes were 0 and the intake recorded status `compatible` with no
incompatible paths. The independent reconciliation state remained provisional with 44 gaps: 5
upstream collisions, 12 adoption-deferred tests, 16 existing merge-required paths, and 11 missing
merge-required paths.

`VERIFIED`: `git diff --exit-code`, the staged diff check, and targeted diffs for `pyproject.toml`,
`uv.lock`, and `.gitignore` remained clean in the disposable application. The authoritative
Procurement checkout was not mutated.

## 6. Acceptance-criterion coverage, waivers, and verifier verdict

- AC1: covered by explicit command execution, stored before/after exits, and the real Procurement
  `make check` replay.
- AC2: covered by not-evaluated, pre-existing-baseline-failure, synthetic post-copy-regression, and
  compatible-with-file-gaps tests.
- AC3: covered by exact Ruff 0.16.3 format/lint over every copied Python source and the complete
  post-adoption Procurement `make check`.
- AC4: covered by the derived-repository CLI regression, byte-preservation assertions, pinned
  fixture, and fresh disposable replay.
- AC5: covered by schema validation, documentation, lock/smoke/version/planning checks, exact diff
  review, and the required Pi review before integration.

No criterion is waived. A revision-bound verifier verdict must be recorded in engineering loop
`20260823T184228Z-9f845c50` before publication.

## 7. Baseline-relative write scope and violations

`VERIFIED`: The loop began from clean commit
`9f845c500eba73ccec7df303b381e915983629f5` on isolated branch
`issue-27-quality-discovery`. Implementation, conformance, test, fixture, schema, documentation,
report, and lock paths are declared. A broad local Ruff invocation briefly touched two undeclared
files; both were immediately restored byte-for-byte and are absent from the final diff. Final scope
evidence is generated by the completion gate.

## 8. GitHub Issue, Project, PR, and release state

`VERIFIED`: Issue #27 is open and In Progress in Project #13. No application Issue, Project, label,
milestone, view, configuration, lock, or ignore rule changed.

`VERIFIED`: No pull request, merge, tag, GitHub Release, package publication, or deployment is
claimed by this pre-integration report.

## 9. Risks, limitations, failures, and unverified claims

`VERIFIED`: The adopter cannot prove that a user-supplied command is non-mutating. Documentation
therefore requires an authoritative non-mutating check, and application preservation is separately
verified by Git state and byte-oriented regressions.

`VERIFIED`: Path attribution is evidence-oriented: it lists copied relative paths literally named
by the failing command output. A tool that emits no paths still yields an incompatible status from
its post-copy nonzero exit, but the path list may be empty.

`VERIFIED`: The first sandboxed Procurement baseline failed only because the environment denied
local socket creation. The same exact command passed when rerun with loopback authority. That
sandbox failure is environmental evidence, not an application or harness regression.

## 10. Decisions or authorization needed

No architecture decision remains for Issue #27. Merge and release authority remain with the human
owner. A harness release is not part of this loop.

## 11. Recommended next loop

With the three measured adoption blockers addressed, select the next scheduled roadmap issue from
Project #13 after merge and exact-main CI verification.

## 12. Exact revision and change scope

- Engineering loop: `20260823T184228Z-9f845c50`, revision 1, attempt 1.
- Start commit: `9f845c500eba73ccec7df303b381e915983629f5`.
- Product release-impact recommendation: patch; this adds fail-closed adoption evidence and source
  compatibility without changing a derived application's public product contract.
- Candidate commit, working-tree digest, verifier identity, PR, merge, and remote CI belong to the
  final loop evidence and GitHub completion record rather than a self-referential source file.
