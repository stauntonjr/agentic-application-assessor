# Agentic Application Assessor

Agentic Application Assessor is a local-first Python CLI for evidence-backed reviews of an exact
application repository. The first slice combines bounded static inspection and human-reviewed
context into deterministic JSON and Markdown while keeping observations, declarations,
derivations, contradictions, and unknowns visibly distinct. Versioned analysis-artifact adapters
are planned but not yet implemented.

The project is an early, unreleased `0.1.0` implementation. It does not execute target code,
install target dependencies, use the network, call a model, certify security or compliance, or
remediate findings.

## Intended first decision

The first audience is an engineering lead or maintainer onboarding to an unfamiliar application
and deciding what to investigate or improve next. Agentic Repo Auditor is the first dogfood target;
Macro Technical Pulse is the second, deeper domain and data-flow target.

## Trust boundary

- Target inspection is read-only and local.
- Static evidence is bounded to regular files and Git metadata; symlink escapes are rejected.
- Human statements remain `human-declared` and dated.
- Deterministic transformations remain `derived`; missing evidence remains `unavailable`.
- Imported tools retain their own identity, schema, target fields, and artifact digest.
- Model synthesis and executable/runtime collectors are optional later adapters, not part of the
  canonical `0.1.0` core.

See [ADR-0008](docs/adr/0008-evidence-first-application-assessment.md) for the accepted boundary.

## CLI

```bash
agentic-application-assessor assess /path/to/repository \
  --context application-context.json \
  --format json
```

The same inputs must produce byte-identical canonical JSON and deterministic Markdown. The CLI
writes reports only to standard output. The first slice accepts context schema `1.0`; the Agentic
Repo Auditor import named in project scope is the next adapter and is not yet implemented.

## Engineering harness

This repository includes the `0.5.0` agentic engineering harness in a one-repository design.
Project intent is authoritative in `harness/project.yaml`; `AGENTS.md` routes engineering work;
accepted decisions live in `docs/adr/`; and `.github/planning.json` defines expected GitHub
planning state.

Public work is managed in the
[Agentic Application Assessor Roadmap](https://github.com/users/stauntonjr/projects/16). The
delivered baseline is [Issue #1](https://github.com/stauntonjr/agentic-application-assessor/issues/1);
the next product slice is the fail-closed Auditor adapter in
[Issue #2](https://github.com/stauntonjr/agentic-application-assessor/issues/2).

```bash
make smoke
python3 tools/product_version.py
python3 tools/github_planning.py audit --offline
```

The derived repository runs the reusable harness runtime, integrity, recovery, adapter, telemetry,
upgrade, and plugin tests. Template-factory intake/bootstrap unit tests remain an upstream concern;
this active project validates its rendered contract directly with `harness_check`, product tests,
and offline planning audit.

The reusable skills are also packaged by the upstream template as the
`agentic-engineering-harness` Codex plugin. The installed plugin supplies workflows; this
repository remains authoritative for product policy, context, code, evidence, and planning.

## License

Original implementation and documentation are licensed under the [MIT License](LICENSE).
Referenced methods, standards, imported artifacts, and third-party tools retain their own terms.
The project may use general architecture concepts but does not copy or adapt arc42 template text.
