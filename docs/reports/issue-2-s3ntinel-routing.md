# Issue #2: S3NTINEL domain routing and Project integration

## 1. Outcome and why it matters

`VERIFIED`: A bounded S3NTINEL change can use the reusable `execute-engineering-loop` governance
skill while retaining S3NTINEL's `AGENTS.md` as the authority for environment, Spark, replay,
artifact, and verification semantics. Domain rules were not promoted into universal policy.

`VERIFIED`: The evaluation remained read-only against S3NTINEL. It exercised a local SparkRun Pi
routing session, a separate verifier, a separate release steward, and live Project ownership
without editing the authoritative checkout, Issues, Projects, pull requests, or repository state.

## 2. Planned versus completed

`VERIFIED`: The reusable forward-test corpus now includes a layered domain-routing scenario. A
pinned fixture records exact S3NTINEL commits, local-only rules, live Project membership, Pi
sessions, tool-call counts, retry behavior, role results, and authority boundaries.

`VERIFIED`: This loop evaluated rather than adopted the harness. No harness files were copied into
S3NTINEL, and no S3NTINEL-specific skill was claimed to exist when the repository currently exposes
its domain guidance through `AGENTS.md`.

## 3. User-visible and business-semantic changes

`VERIFIED`: The documented routing rule is now explicit: reusable skills own workflow; the target
repository owns domain facts and commands. GitHub Issues remain canonical work objects, Projects
remain operational views, and neither Project status nor a model verdict grants write or release
authority.

`VERIFIED`: S3NTINEL-specific conda, parquet, host-profile, Py4J, Spark-path, replay, and generated
architecture rules remain local. Derived repositories should not inherit them unless their own
accepted policy says so.

## 4. Architecture, schema, dependency, data, and interface changes

`VERIFIED`: `E009-layered-domain-routing` extends the forward-test corpus without changing runtime
dependencies or the provider-neutral role and skill contracts. The S3NTINEL fixture is evidence,
not an application configuration or adapter.

`VERIFIED`: No S3NTINEL code, data, dependency, schema, architecture artifact, Project, Issue, pull
request, or product interface changed.

## 5. Verification evidence and boundary proven

`VERIFIED`: The target was pinned to S3NTINEL current main
`14ba0416e06f6a9b57a8f7b02fdef1bb09a2f1cc`. The bounded public change was draft PR #54 at exact
remote head `356281f1982b4ec5c3f4fd08a291c3c962b36ee5`, with five changed paths and two successful
historical CI checks. Live metadata still reported the PR draft and behind main.

`VERIFIED`: Pi routing session `6aa2f88c-51f4-4c7f-b61b-255eb9005548` made exactly three
successful read calls: S3NTINEL `AGENTS.md`, S3NTINEL `pyproject.toml`, and the reusable
`execute-engineering-loop` skill. Its first answer emitted only the result token; one no-tool
content retry produced the required six-part routing plan and exact `ROUTING_RESULT: PASS`.

`VERIFIED`: A first verifier invocation accidentally omitted the reviewed context-readiness
extension. It made eight successful reads, then attempted unavailable tool `run` 231 times. Pi
returned 231 not-found errors, no command executed, and the operator interrupted the session
without a verdict. This is invocation-failure evidence, not verifier approval.

`VERIFIED`: The repaired verifier invocation disabled global discovery, explicitly loaded the
reviewed extension, attached the pinned files, and advertised zero tools. Fresh session
`704bcfe3-3ed6-4c97-9cea-93a61c0f9809` found no material inspected-content defect and returned
`APPROVE_CONTENT_ONLY`; one format-only continuation removed Markdown from the exact verdict line.
It explicitly withheld merge readiness because the PR is draft and behind.

`VERIFIED`: Separate zero-tool release-steward session
`e463e85e-a203-4a8a-8700-d71ac72d122e` returned exact `RELEASE_RESULT: NOT_READY`. It separated
content inspection from merge and release authority and identified missing current-main evidence,
an accepted license, and human authorization. It performed no publication action.

`VERIFIED`: Live Project reads found disjoint Issue membership: Project #3 has 16 proposal items,
Project #4 has 10 implementation items, and Project #5 has 25 GPU-migration items. All items point
to `stauntonjr/S3NTINEL`; no Issue appeared in more than one of these views. Project purpose and
Issue ownership are therefore unambiguous in the inspected snapshot.

## 6. Acceptance-criterion coverage, waivers, and verifier verdict

- AC1: covered by E009 and the three-read SparkRun routing probe across reusable skill and local
  repository sources.
- AC2: covered by read-only live Project #3/#4/#5 membership and purpose evidence.
- AC3: covered by separate verifier and release-steward sessions on pinned draft PR #54.
- AC4: covered by the local-rules fixture, README boundary, and absence of S3NTINEL policy in the
  universal `AGENTS.md`.
- AC5: covered by exact commits, session IDs, tool counts, retries, fixture, report, loop evidence,
  lock, tests, planning audit, and final diff checks.

No criterion is waived. The template candidate still requires its own revision-bound independent
verifier before publication; the S3NTINEL content exercise is not that template verdict.

## 7. Baseline-relative write scope and violations

`VERIFIED`: The template loop began at clean merge commit
`1c49ff1866f64c611cb5656b20256f4bdf7e25a0` on isolated branch
`issue-2-s3ntinel-routing`. Only the declared scenario, test, fixture, documentation, report, lock,
and ignored loop-artifact paths are in scope.

`VERIFIED`: The authoritative `/home/jrs/S3NTINEL` checkout contained pre-existing SpecStory edits
and remained untouched. All model inspection used a disposable clone under `/tmp`.

## 8. GitHub Issue, Project, PR, and release state

`VERIFIED`: Template Issue #2 is In Progress in Project #13. S3NTINEL Projects #3, #4, and #5 were
read only. S3NTINEL PR #54 remained open, draft, behind, and unmodified.

`VERIFIED`: No pull request, merge, tag, GitHub Release, package publication, application Project
mutation, or deployment is claimed by this pre-integration report.

## 9. Risks, limitations, failures, and unverified claims

`VERIFIED`: The routing model needed one content retry, and the content verifier needed one verdict
format retry. Local-model outputs require machine-checked structure rather than trust in prompt
wording alone.

`VERIFIED`: Omitting the context-readiness extension reproduced an unbounded invalid-tool loop even
though the advertised built-in allowlist contained only `read`. Operational Pi invocations must use
`--no-extensions --extension .pi/extensions/context-readiness.ts` rather than merely restricting
built-in tools.

`VERIFIED`: The verifier inspected content but did not run the SVG generator, compare generated
bytes, rebase onto current main, or rerun S3NTINEL CI. `APPROVE_CONTENT_ONLY` is deliberately not a
merge-ready or release verdict.

`VERIFIED`: No S3NTINEL repository-local skill package was created. The current local authority is
`AGENTS.md`; packaging those rules as a skill would require separate S3NTINEL authorization and
review.

## 10. Decisions or authorization needed

No template architecture decision remains for the layered-routing rule. Any S3NTINEL adoption,
skill creation, PR update, Project change, merge, license decision, or publication requires
separate authorization in that repository.

## 11. Recommended next loop

After template integration, choose whether to continue with recovery-corpus Issue #14 or request
separate authorization for a write-capable S3NTINEL adoption loop. Do not infer that authorization
from this evaluation.

## 12. Exact revision and change scope

- Engineering loop: `20260823T190447Z-1c49ff18`, revision 1, attempt 1.
- Start commit: `1c49ff1866f64c611cb5656b20256f4bdf7e25a0`.
- Product release-impact recommendation: none; this adds evaluation evidence and routing guidance
  without changing a derived application's public contract.
- Candidate commit, candidate digest, template verifier, PR, merge, and remote CI belong to final
  loop evidence and the GitHub completion record.
