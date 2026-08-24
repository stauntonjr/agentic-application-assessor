---
name: loop-report
description: Produce a comprehensive executive summary for an engineering-loop boundary from Git, recorded checks, agent handoffs, decisions, risks, and GitHub references. Use at loop close, handoff, status review, or before integration; do not use conversation recollection as factual evidence.
---

# Loop report

Read `references/report-contract.md`. Locate the loop run under `.harness/runs/` or require explicit start and end revisions.

## Collect

Use the deterministic collector first:

```bash
python3 tools/loop.py finish --run RUN_ID
```

Inspect the generated JSON evidence and Markdown report. Confirm:

- start and end commits;
- dirty working-tree state;
- commits, changed paths, and diff statistics;
- linked Issue and PR references;
- exact checks and their results;
- acceptance criteria and their linked current-revision/current-attempt evidence;
- baseline-relative changed paths and declared-scope violations;
- agent handoffs and revision-bound independent-review decision;
- decisions, deferrals, retries, failures, and unresolved risks;
- current-revision product release impact and identified public-contract changes;
- elapsed time and available cost/token telemetry.

Do not claim live GitHub, deployment, or release state unless it was read during this loop.

`finish --state reported` is a completion gate. If it refuses the run, preserve the error and generate a truthful blocked or abandoned report instead of weakening the criteria, widening scope, or fabricating reviewer identity.

## Write the executive narrative

Lead with the outcome and why it matters. Cover planned versus completed work, user-visible effects, architecture/interfaces, verification, GitHub state, risk, decisions needed, and next loop.

Label every material claim:

- `VERIFIED`: supported by a named artifact, command, diff, API result, or check.
- `REPORTED`: provided by a person or agent but not independently confirmed.
- `INFERRED`: reasoned from evidence; state the inference.

Never label a command that was not run as passed. Never treat compilation, unit tests, or a clean diff as proof of a deployed or authenticated end-to-end system.

## Publish

Detailed run data stays in `.harness/runs/`. Commit a concise report under `docs/reports/` only when it has durable project value. Post to an Issue, PR, or Project only with authorized GitHub writes.
