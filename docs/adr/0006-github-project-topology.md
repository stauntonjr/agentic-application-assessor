# ADR-0006: Render GitHub planning state into a shared program Project

- Status: accepted
- Date: 2026-08-23
- Deciders: human owner and orchestrator
- Governing issue: #4

## Context

GitHub repository templates copy files, not repository settings or planning topology. GitHub Project copies do carry views and custom fields, but they do not carry the original Issues, collaborators, or repository links. A copy is therefore useful for bootstrap but cannot be an ongoing synchronization mechanism. GitHub Issues already provide the authoritative work identity and history; duplicating that backlog in files or draft Project items would create conflicting sources of truth.

The live user-owned [Agentic Engineering Harness Roadmap](https://github.com/users/stauntonjr/projects/13) already spans the template and Agentic Repo Auditor. It is the program-level view for harness development and dogfood convergence. Application repositories may need independent planning when their governance, permissions, delivery cadence, or release lifecycle diverges from the harness program.

As of 2026-08-23, GitHub CLI 2.45.0 can create, copy, link, and manage fields but has no `gh project` saved-view command. GitHub.com's typed GraphQL schema exposes Project view reads and create/update mutations. GitHub documents that a Project copy contains views and fields but excludes original items, collaborators, and repository links.

## Decision

1. Issues remain the canonical work objects in their owning repositories. Projects are operational views, and repository reports are evidence artifacts rather than backlogs.
2. `stauntonjr` owns canonical Project #13. It is the shared program Project for the reusable harness, auditor, and cross-repository dogfood work.
3. `.github/planning.json` is the desired-state contract. Ongoing reconciliation renders labels, milestones, standard fields, basic saved views, and the repository link into the selected live Project.
4. Copying Project #13 is an optional one-time bootstrap for a dedicated application Project. It is not a sync relationship. A copied Project must be linked to its repository after creation and then reconciled from its own `.github/planning.json`.
5. A different repository rendered from this template starts with `topology: dedicated`, no live Project number, and Project #13 as its canonical copy source. Intake or adoption may instead select a shared Project when the owner explicitly chooses that topology and supplies its number.
6. A dedicated Project is justified only when permissions, governance, lifecycle, delivery cadence, or operational volume require independent control. Cross-repository dependency work remains visible in Project #13 through the canonical Issues, not duplicate draft items.
7. Reconciliation is additive and fail-closed. It creates missing managed state but does not delete unmanaged labels, milestones, fields, views, items, or links. Existing field/view incompatibilities remain manual because destructive replacement could lose data or layout intent.

## Consequences

### Positive

- One shared roadmap shows program dependencies without moving Issue authority out of repositories.
- Dedicated application Projects can reuse the same fields and views without becoming coupled to future changes in Project #13.
- Drift is inspectable and routine reconciliation is idempotent.
- Unmanaged human customization survives automation.

### Negative

- Copies can drift and must be reconciled independently.
- Some Project settings still require a human in the GitHub UI.
- The saved-view implementation depends on GitHub.com's current GraphQL schema because the stable CLI lacks equivalent commands.

### Risks and mitigations

- GitHub may change the Project view API. The tool uses typed mutations, fails closed on unsupported results, and retains a documented manual fallback.
- A shared Project can become noisy. Repository filters, canonical Issue ownership, and the dedicated-Project trigger keep the boundary explicit.
- Copying could be mistaken for synchronization. The planning guide and dry-run output label it as bootstrap only.

## Alternatives considered

| Alternative | Evidence | Reason not selected |
|---|---|---|
| Copy Project #13 for every repository | GitHub copies views and fields but not original items, collaborators, or repository links | Creates unnecessary Projects and no durable sync relationship |
| Render every repository into a dedicated Project | Desired state can reproduce fields and basic views | Loses the useful shared program roadmap and fragments cross-repository dependencies |
| Use only one shared Project forever | Project #13 already spans repositories successfully | Does not accommodate independent permissions, governance, cadence, or release lifecycles |
| Store the backlog in repository files | Files are easy to template | Duplicates Issue identity, history, dependencies, and lifecycle state |
| Let automation replace mismatched fields and views | Could force exact convergence | Replacement can destroy field values, layout decisions, or unmanaged work |

## Verification and revisit trigger

- `python3 tools/github_planning.py audit --offline` validates the local contract.
- `python3 tools/github_planning.py audit` reports live label, milestone, field, view, title, and repository-link drift.
- `python3 tools/github_planning.py bootstrap-project --yes` must be idempotent after create or copy bootstrap.
- Revisit if GitHub publishes a stable higher-level API for complete Project templates, if Project #13 becomes operationally unmanageable, or if two dogfoods show that the shared-versus-dedicated trigger is insufficient.

Primary references: [GitHub Project copying](https://docs.github.com/en/issues/planning-and-tracking-with-projects/creating-projects/copying-an-existing-project), [managing Project views](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/managing-your-views), and [`gh project copy`](https://cli.github.com/manual/gh_project_copy).
