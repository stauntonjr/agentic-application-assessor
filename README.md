# Agentic Application Assessor

Agentic Application Assessor is a local-first Python CLI for evidence-backed reviews of an exact
application repository. It combines bounded static inspection, human-reviewed context, and
supported analysis artifacts into deterministic JSON and Markdown while keeping observations,
declarations, derivations, contradictions, and unknowns visibly distinct.

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

## Planned CLI

```bash
agentic-application-assessor assess /path/to/repository \
  --context application-context.json \
  --format json
```

The same inputs must produce byte-identical canonical JSON and deterministic Markdown. The CLI
writes reports only to standard output unless the caller explicitly selects an output path outside
the target repository.

## Engineering harness

This repository includes the `0.5.0` agentic engineering harness in a one-repository design.
Project intent is authoritative in `harness/project.yaml`; `AGENTS.md` routes engineering work;
accepted decisions live in `docs/adr/`; and `.github/planning.json` defines expected GitHub
planning state.

```bash
make smoke
python3 tools/product_version.py
python3 tools/github_planning.py audit --offline
```

The reusable skills are also packaged by the upstream template as the
`agentic-engineering-harness` Codex plugin. The installed plugin supplies workflows; this
repository remains authoritative for product policy, context, code, evidence, and planning.

## License

Original implementation and documentation are licensed under the [MIT License](LICENSE).
Referenced methods, standards, imported artifacts, and third-party tools retain their own terms.
The project may use general architecture concepts but does not copy or adapt arc42 template text.
