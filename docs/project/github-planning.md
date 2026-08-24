# GitHub planning topology

GitHub Issues are the authoritative work objects. `.github/planning.json` declares the operational topology around them: repository labels and milestones plus one selected Project's fields, saved views, and repository link.

## Choose the topology

Use `shared` when the repository belongs to one program whose dependencies and delivery decisions benefit from a common roadmap. This harness program uses the public, user-owned [Agentic Engineering Harness Roadmap](https://github.com/users/stauntonjr/projects/13), owned by `stauntonjr`.

Use `dedicated` only when the application needs independent permissions, governance, lifecycle, delivery cadence, or operational volume. A derived repository starts unbound (`number: null`) and can copy Project #13 once as a bootstrap. Copying carries fields and views but not original work items, collaborators, or repository links. It is never a synchronization relationship.

Before live work, confirm these values in `.github/planning.json`:

- `repository`: the exact `OWNER/REPOSITORY` that owns the Issues.
- `project.topology`: `shared` or `dedicated`.
- `project.owner` and `project.number`: the selected live Project; a dedicated Project stays `null` only until bootstrap.
- `project.canonical_source`: the Project used for copy bootstrap.
- `project.bootstrap.method`: `copy` for the canonical field/view baseline, or `create` when deliberate blank-project bootstrap is required.

## Standard fields and views

The managed fields are Status, Area, Work Type, Priority, Risk, Agentability, and Evidence Required. Their ordered single-select options are declared in `.github/planning.json`.

The managed saved views are:

| View | Layout | Filter | Purpose |
|---|---|---|---|
| Roadmap | Roadmap | `is:issue` | Program-level issue timeline |
| Active work | Table | `status:"In Progress"` | Current execution lanes |
| Decisions | Table | `"Work Type":Decision` | Human and architecture decisions |
| High risk | Table | `Risk:High` | Explicit risk-review queue |

## Safe operating sequence

```bash
python3 tools/github_planning.py audit --offline
python3 tools/github_planning.py bootstrap-project       # review create/copy plan
python3 tools/github_planning.py bootstrap-project --yes # authorized bootstrap/reconcile
python3 tools/github_planning.py audit                    # live read-only drift check
python3 tools/github_planning.py apply                    # label/milestone/Project dry run
python3 tools/github_planning.py apply --yes              # authorized additive reconciliation
```

`bootstrap-project --yes` records the newly created/copied Project number in `.github/planning.json`, creates missing fields and basic views, and links the repository. Repeating it against matching state performs no operations. `apply --yes` updates managed labels and milestone descriptions and adds missing Project fields, views, or the repository link. Neither command deletes unmanaged state.

Offline validation rejects malformed or unsupported write-bearing values before any live read or mutation. A duplicate live identity for a managed label, milestone, field, or view is explicit drift; it can never be collapsed into a matching result.

## Manual settings and boundaries

The tool reports but does not replace an existing field with the wrong type/options, rename or rewrite a mismatched view, change the Project title, or delete unmanaged views. Those operations may destroy values or human layout intent and require an explicit reviewed migration.

These settings also remain manual because they are permission-bearing, destructive, or are not completely represented by the portable contract:

- Project visibility, collaborators, roles, and organization template designation;
- built-in workflows, auto-add rules, charts, insights, and status updates;
- view grouping, sorting, visible-field order, column widths, and roadmap date/iteration selection;
- repository rulesets, branch protection, environments, secrets, and workflow permissions;
- removal, archival, renaming, or unlinking of any existing object.

If the typed saved-view API is unavailable, the command fails without claiming convergence. Create the documented views in GitHub's UI, rerun the audit, and keep the evidence with the governing Issue.
