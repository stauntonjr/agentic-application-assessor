---
name: manage-github-planning
description: Audit, diff, and reconcile repository Issues, labels, milestones, GitHub Project fields, items, and views against .github/planning.json. Use for planning setup, drift checks, backlog administration, or post-loop reconciliation; never mutate or delete GitHub state without explicit authorization.
---

# Manage GitHub planning

Treat `.github/planning.json` as desired topology, Issues as canonical work objects, and the live Project as the operational view.

## Required sequence

1. Read `AGENTS.md`, `harness/project.yaml`, `.github/planning.json`, and relevant Issues.
2. Inspect repository identity and authentication without exposing credentials.
3. Validate local desired state with `python3 tools/github_planning.py audit --offline`.
4. For a new repository, preview Project creation or canonical-Project copying with `python3 tools/github_planning.py bootstrap-project`. Use `--yes` only after authorization.
5. Read live state with `python3 tools/github_planning.py audit`; this includes the selected Project title, fields, basic saved views, and repository link.
6. Preview the smallest label and milestone reconciliation with `python3 tools/github_planning.py apply`.
7. Explain every proposed write and obtain authorization.
8. Apply only with `--yes`. Re-audit live state afterward.

Read `references/safety.md` before live writes.

## Work-item rules

- Search for duplicates before creating an Issue.
- Give every Issue observable acceptance criteria, one primary milestone, and one primary Project ownership lane.
- Use dependencies instead of duplicating work across Projects.
- Move work to Done only when acceptance evidence is complete on the integration branch.
- Use `Closes #N` only for a fully complete Issue; otherwise use `Part of #N`.

## Completion

Report exact object names, URLs or IDs when available, counts, writes performed, and residual drift. A successful command exit is not sufficient; re-read the changed objects.

The tool can create or copy a Project, link it to the repository, and create missing fields and basic saved views. It creates or updates labels and milestones separately. Existing field/view mismatches and complex view layout settings remain manual because replacing them could destroy values or human layout intent. Read `docs/project/github-planning.md` for the shared-versus-dedicated decision and exact boundary.
