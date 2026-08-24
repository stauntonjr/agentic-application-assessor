---
name: execute-engineering-loop
description: Run a non-trivial repository change through intake, evidence gathering, planning, authorization, implementation, independent verification, integration, reporting, and learning. Use for features, defects, refactors, migrations, or documentation changes that alter durable project state; do not use for a read-only answer.
---

# Execute engineering loop

Read `harness/loops/engineering-loop.yaml` and the relevant role contracts before acting.

## Start

1. Read `AGENTS.md`, `harness/project.yaml`, the handoff, governing Issue, and linked ADRs.
2. Inspect Git status and resolve the exact branch/worktree boundary.
3. Assess context readiness: do you have enough intent, evidence, authority, acceptance criteria, and current-state knowledge to excel? Inspect discoverable facts first. Ask focused follow-ups only for material gaps; record safe assumptions.
4. Invoke `$research-existing-solutions` when novelty, standards, licensing, current external behavior, or buy-versus-build materially affects the plan.
5. Start the evidence boundary:

   ```bash
   python3 tools/loop.py start --issue NUMBER \
     --objective "ACCEPTED OBJECTIVE" \
     --criterion "AC1=MECHANICALLY VERIFIABLE RESULT" \
     --write-path path/to/exact-file \
     --write-prefix path/to/owned-directory \
     --implementer PROVIDER/SESSION-ID
   ```

Do not invent a start commit or dirty baseline after implementation begins. The baseline binds worktree content, staged index identity, and dirty gitlinks. Use stable criterion IDs. Declare exact files with `--write-path` and directory subtrees with `--write-prefix`; never use the repository root as a catch-all.

## Execute the states

Follow the state order and gates in the loop contract.

- Keep the orchestrator as sole owner of shared Git lifecycle, integration, and GitHub planning state.
- Delegate only independent, bounded lanes. Use one write-capable owner per worktree.
- Give every implementer an issue, branch, worktree, path scope, acceptance evidence, and stop condition.
- Use a verifier who did not author the reviewed work.
- Stop after three consecutive failures at the same boundary and escalate with preserved evidence.
- Obtain required human approval before external side effects.

Record exact checks as they finish:

```bash
python3 tools/loop.py record-check --run RUN_ID --name NAME \
  --command "EXACT COMMAND" --status passed --evidence "BOUNDARY PROVEN" \
  --criterion AC1
```

Before independent approval, record the recommended product release impact. Base it on the public compatibility contract in `harness/project.yaml`, not commit-message syntax:

```bash
python3 tools/loop.py record-release-impact --run RUN_ID \
  --level patch --reason "SEMANTIC COMPATIBILITY RATIONALE" \
  --public-contract-change "OPTIONAL CHANGED CONTRACT"
```

Use `none`, `patch`, `minor`, or `major`. `none` means the project contract does not require a product release for this change. This assessment is a recommendation and never authorizes a version bump or publication.

If objective, acceptance, or write scope changes, use `loop.py revise`; if implementation retries without changing the contract, use `loop.py new-attempt`. Prior checks and approvals do not satisfy the new revision or attempt, and a contract revision invalidates prior criterion waivers. `new-attempt` persists each failure and blocks after the third without creating attempt four.

Inspect a preserved run without changing Git state:

```bash
python3 tools/loop.py recovery-status --run RUN_ID --integration-ref main
```

After retry exhaustion, do not delete partial work or continue under a fourth attempt. Prepare a
structured handoff containing `schema_version`, `summary`, `failure_boundary`, `preserved_paths`,
and `next_action`. Only a human-reviewed resume starts a new revision:

```bash
python3 tools/loop.py resume --run RUN_ID --handoff /path/to/handoff.json \
  --by human:IDENTITY
```

The `human:` marker is auditable provenance, not authentication. Resume preserves the working tree,
returns to `understand`, and invalidates the old revision's checks, waivers, impact, and verdict.

After verification, the independent reviewer records a verdict:

```bash
python3 tools/loop.py record-verdict --run RUN_ID \
  --reviewer PROVIDER/SEPARATE-SESSION-ID --verdict approve \
  --criterion AC1 --evidence "RAW REVIEW EVIDENCE"
```

The reviewer identity must differ from every recorded implementer. The approval is bound to the current revision, attempt, commit, and baseline-relative working-tree digest.

Only an explicit human decision may waive a criterion. Record its provenance and rationale with `loop.py waive-criterion --criterion AC1 --by human:IDENTITY --reason "..."`; the label is auditable evidence, not authentication.

Use `references/handoff-contract.md` for every agent handoff.

## Finish

1. Reconcile implementation, tests, docs, ADRs, handoff, Issue, and Project state.
2. Run `make smoke`, `git diff --check`, and `git status --short`.
3. Invoke `$loop-report` or run `python3 tools/loop.py finish --run RUN_ID`. A `reported` finish refuses missing criterion evidence, missing or stale release impact, stale or non-independent approval, and writes outside the declared scope. Use `--state blocked` or `--state abandoned` to preserve an incomplete run truthfully.
4. In Learn, propose challenge, skill, profile, or instruction updates. Do not apply policy changes without human review.

A loop is not complete because code exists. It is complete only when the accepted boundary is verified, independently reviewed where required, reconciled, and reported.
