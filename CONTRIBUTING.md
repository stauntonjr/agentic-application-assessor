# Contributing

Use an Issue or another accepted work item to define the objective and mechanically verifiable acceptance criteria. Read `AGENTS.md`, `harness/project.yaml`, the relevant ADRs, and the applicable repository skill before changing durable state.

For non-trivial changes:

1. Start a bounded run with `python3 tools/loop.py start`.
2. Declare exact write paths or narrow directory prefixes.
3. Keep generated, personal, secret, and runtime state out of commits.
4. Run `make smoke` and the checks required by the selected project profile.
5. Record product release impact as `none`, `patch`, `minor`, or `major` with a reason.
6. Obtain review from an identity that did not implement the candidate.
7. Reconcile documentation, changelog, versioning, migration, and planning state.

Do not publish, deploy, create releases, or mutate GitHub state without the authorization required by `harness/project.yaml`.

## Pull requests

Explain the user-visible and semantic effect, acceptance evidence, tests, compatibility impact, migrations, security considerations, and residual risk. Preserve unrelated local work and stage only reviewed paths.

## Tooling

The harness itself has no runtime dependencies. Use `make smoke` for its authoritative local and CI boundary. Derived projects select concrete formatter, linter, type checker, test runner, dependency lock, coverage policy, and package smoke commands through intake and their profile.
