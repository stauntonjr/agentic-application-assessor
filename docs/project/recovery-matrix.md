# Recovery and historical challenge coverage

This matrix describes deterministic local evidence. It does not claim process sandboxing, live
provider behavior, GitHub state, or recovery of work that was never written to durable storage.

## Recovery fixtures

Run all fixtures with `python3 tools/recovery_scenarios.py`, or select one with `--fixture RNNN`.
Every scenario creates a disposable Git repository and rejects destructive Git commands.

| Claim | Fixture | Deterministic evidence | Recovery result |
|---|---|---|---|
| Pre-existing dirty work is not attributed to the run | `R001` dirty worktree | `tests.test_recovery_scenarios` and `tests.test_loop.LoopTests.test_preexisting_dirty_path_is_subtracted_from_run_delta` | Existing bytes remain; only the new declared path appears in the delta |
| An interrupted partial loop remains reloadable | `R002` partial loop | `python3 tools/recovery_scenarios.py --fixture R002` | Run ID, state, and partial file survive process boundary |
| A branch behind the integration ref is reported before integration | `R003` stale branch | `tests.test_loop.LoopTests.test_recovery_status_detects_branch_stale_against_integration_ref` | Read-only ancestry check returns `branch_stale: true` |
| A process loss can leave a concise durable handoff without chat history | `R004` agent crash | `python3 tools/recovery_scenarios.py --fixture R004` | Partial file and structured handoff remain; no transcript is stored |
| Three failures stop the run | `R005` retry exhaustion | `tests.test_loop.LoopTests.test_three_consecutive_failures_block_without_starting_a_fourth_attempt` | State becomes `blocked`; attempt ID remains 3; no attempt 4 exists |
| Retry exhaustion can resume under reviewed new evidence | `R006` resumable handoff | `tests.test_loop.LoopTests.test_retry_exhaustion_resumes_only_with_human_reviewed_handoff` | `human:IDENTITY` handoff starts revision 2, attempt 1 in `understand`; partial bytes remain |

## Dogfood-derived challenge candidates

`python3 tools/run_challenges.py` validates provenance and lists candidate versus approved status.
`python3 tools/run_challenges.py --run --include-candidates` executes candidates without promoting
them. Default `make challenges` executes only approved challenges.

| Candidate | Public minimized source | Oracle | Known-bad signature | Current promotion state |
|---|---|---|---|---|
| `C001` unavailable Pi tool retries | Template Issue #2 and `harness/fixtures/s3ntinel-routing-evaluation.json` | Loop stops after three failures | `unbounded unavailable-tool retries` | Candidate; excluded from default replay pending owner review |
| `C002` adoption partial mutation | Template Issue #3 and its public dogfood report | Preflight rejects before any copy | `partial mutation before preflight` | Candidate; excluded from default replay pending owner review |

Promotion is an explicit write:

```bash
python3 tools/run_challenges.py --promote C001 \
  --by human:OWNER \
  --decision "Retain this minimized public fixture"
```

The command records review time and decision. The `human:` marker is auditable provenance rather
than authentication, so repository review and branch protection remain the actual authorization
boundary. Agents may propose or execute candidates but must not invent that marker or promote them
on a human's behalf.

## Data-retention boundary

Fixtures retain only synthetic state and public artifact references. Validation requires
`sanitized: true` and `contains_raw_transcript: false`. Do not add tokens, secrets, private source,
prompts, hidden reasoning, full model responses, or raw session logs. Reduce a failure to the
smallest input, expected oracle, known-bad signature, and affected surface needed for replay.
