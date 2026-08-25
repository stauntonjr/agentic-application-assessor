# Agentic Application Assessor

Agentic Application Assessor is a local-first Python CLI for evidence-backed reviews of an exact
application repository. The first slice combines bounded static inspection and human-reviewed
context into deterministic JSON and Markdown while keeping observations, declarations,
derivations, contradictions, and unknowns visibly distinct. It can also import one canonical
Agentic Repo Auditor `0.1.0` schema-`1.2` JSON report as provenance-preserving evidence.

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
- Auditor findings retain status, severity, category, source location, and nested evidence as
  `imported-tool` evidence. They are not promoted into application claims.
- Model synthesis and executable/runtime collectors are optional later adapters, not part of the
  canonical `0.1.0` core.

See [ADR-0008](docs/adr/0008-evidence-first-application-assessment.md) for the accepted boundary.

## CLI

```bash
agentic-application-assessor assess /path/to/repository \
  --context application-context.json \
  --auditor-report repository-audit.json \
  --format json
```

The same inputs must produce byte-identical canonical JSON and deterministic Markdown. The CLI
writes reports only to standard output. Context schema `1.0` remains required. The optional
Auditor input must be a regular non-symlink file no larger than 2 MiB, contain duplicate-key-free
JSON from exactly `agentic-repo-auditor 0.1.0` using report schema `1.2`, and identify the exact
current target state using either a SHA-1 or SHA-256 Git object identity. The Assessor rechecks its
own complete target identity before returning and rejects a state change during assessment.
Incompatible, stale, malformed, or structurally excessive artifacts fail with exit status `2`.
The Assessor reads the artifact; it never invokes the Auditor, executes the target, or treats
imported findings as verified application behavior.

### Gap-only requirements questionnaire

Generate a canonical questionnaire from the exact repository and, when available, an accepted
context:

```bash
agentic-application-assessor questionnaire /path/to/repository \
  --context accepted-context.json > questionnaire.json
```

Stable questions cover unresolved intent, priorities, constraints, risk tolerance, deployment
context, and evidence expectations. Accepted declarations are omitted. Bounded repository
observations contextualize questions and can offer recommendations, but remain `observed`; only
accepted context removes a question, and observations do not silently become owner intent.
Questionnaire and answer artifacts use schema `1.0` and are bound by the SHA-256
digest of the exact questionnaire bytes. Copy
[`examples/application-questionnaire.answers.json`](examples/application-questionnaire.answers.json),
replace its digest and answers, then create a reviewable draft:

```bash
agentic-application-assessor reconcile /path/to/repository \
  --questionnaire questionnaire.json \
  --answers application-questionnaire.answers.json \
  --context accepted-context.json > draft-context.json
```

Omit `--context` in both commands when no accepted context exists. Reconciliation never overwrites
an accepted declaration: an answer for a question that was omitted fails closed. It preserves
contradictions, explicit unknowns, answer source/date/status, exact target identity, and accepted
context digest. To emit application-context schema `1.1` with `review.status=accepted`, explicitly
repeat reconciliation with both acceptance fields. When the questionnaire was generated with an
accepted context, retain the same `--context` input during this acceptance transition:

```bash
agentic-application-assessor reconcile /path/to/repository \
  --questionnaire questionnaire.json \
  --answers application-questionnaire.answers.json \
  --context accepted-context.json \
  --accept-by "OWNER NAME" \
  --accepted-on 2026-08-25 > accepted-context.json
```

The owner marker is provenance, not authentication. `assess` rejects drafts and continues to accept
legacy schema-`1.0` accepted context. Inputs must be duplicate-key-free regular non-symlink JSON no
larger than 256 KiB. The commands write only to standard output and do not call a model or network,
execute target code, install dependencies, or modify the target repository.
Supplying the two acceptance flags is an operator assertion over the complete rendered packet;
explicit unknowns may remain in accepted context and are not silently converted into answers.

## Engineering harness

This repository includes the `0.5.0` agentic engineering harness in a one-repository design.
Project intent is authoritative in `harness/project.yaml`; `AGENTS.md` routes engineering work;
accepted decisions live in `docs/adr/`; and `.github/planning.json` defines expected GitHub
planning state.

Public work is managed in the
[Agentic Application Assessor Roadmap](https://github.com/users/stauntonjr/projects/16). The
delivered baseline is [Issue #1](https://github.com/stauntonjr/agentic-application-assessor/issues/1),
and the fail-closed Auditor adapter is tracked in
[Issue #2](https://github.com/stauntonjr/agentic-application-assessor/issues/2).
The requirements-questionnaire workflow is tracked in
[Issue #3](https://github.com/stauntonjr/agentic-application-assessor/issues/3).

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
