# Issue #2 Agentic Repo Auditor adapter

- Work item: [GitHub Issue #2](https://github.com/stauntonjr/agentic-application-assessor/issues/2).
- Loop: `20260825T013643Z-e7fdcd62`, revision 1, attempt 2.
- Candidate branch/worktree: `issue-2-auditor-adapter` at
  `/home/jrs/agentic-application-assessor-issue2`.
- Product release: `0.1.0`, unreleased; no publication or deployment is authorized.

## Implemented boundary

The optional `--auditor-report` input accepts only a regular non-symlink JSON artifact no larger
than 2 MiB. The adapter requires duplicate-key-free Agentic Repo Auditor `0.1.0` report schema
`1.2`, enforces its closed structure plus bounded strings and collection sizes, validates summary
counts and unique finding IDs, and independently reproduces the Auditor target-state identity to
bind the report to the exact repository being assessed. SHA-1 and SHA-256 Git revisions are both
accepted. Overlapping name, revision, normalized branch, and dirty fields must agree between the
Auditor and Assessor collectors, and a final Assessor identity scan must equal the initial scan.

The Assessor preserves the artifact path basename, SHA-256, schema, tool identity, and complete
Auditor target identity in `inputs.agentic_repo_auditor`. Configuration, summary, every finding,
and every nested evidence record become `imported-tool` evidence with an exact JSON pointer and the
artifact digest. Finding category, status, severity, title, description, remediation, and nested
evidence remain source data. None become application claims or proof of runtime behavior.

The adapter never invokes Agentic Repo Auditor, executes target code, installs target dependencies,
uses the network, or writes the target. Running the Auditor and producing the canonical input
artifact remain caller-controlled actions outside this adapter.

## Acceptance evidence

| Criterion | Candidate evidence |
|---|---|
| AC1 | Strict artifact loader, exact tool/schema checks, duplicate-key rejection, bounded structure, regular-file and symlink checks, normalized cross-collector identity, and initial/final Assessor identity equality. |
| AC2 | Canonical imported evidence IDs and JSON pointers preserve finding dispositions and nested records; input metadata preserves tool, schema, target, and artifact digest; imported records are absent from application claims. |
| AC3 | Adversarial tests cover malformed/incompatible inputs, stale and mid-assessment target mutation, collector disagreement, size, symlink traversal, deep JSON, duplicate keys/IDs, summary inconsistency, and CLI exit `2` without traceback. |
| AC4 | Repeated imported JSON and Markdown remain identical; an exact literal snapshot preserves pre-adapter no-artifact Markdown byte-for-byte; a real SHA-256 Git fixture validates in both report modes. |
| AC5 | Attempt-2 targeted tests, Ruff, Pyright, Draft 2020-12 SHA-256 schema validation, documentation, version, and regenerated lock pass. The candidate-bound full gate and independent verdict remain authoritative loop evidence after this report freezes. |

## Current evidence and limitations

- Attempt 1 was revised after independent review reproduced three gaps: a mixed target-state race,
  rejection of valid SHA-256 Git revisions, and changed no-artifact Markdown.
- Attempt-2 targeted application tests: `33 passed`.
- Ruff `0.12.10` lint and Pyright `1.1.403` passed after formatting the candidate.
- Draft 2020-12 schema validation passed for SHA-256 reports both with and without the optional
  artifact.
- The attempt-1 full gate passed but was invalidated by the revised candidate. Attempt 2 runs one
  final candidate-bound `make smoke` after this report and the ownership lock freeze; its result is
  recorded in the loop rather than preclaimed here.
- The initial sandboxed `uv`/`uvx` attempts could not resolve pinned tools because DNS was
  unavailable; the same checks succeeded with approved dependency-network access.
- The adapter is intentionally pinned to Auditor `0.1.0` and report schema `1.2`; future versions
  require an explicit compatibility change.
- Exact target binding reproduces the versioned Auditor target-identity algorithm because the two
  products deliberately expose different state-ID algorithms. It does not copy or run Auditor
  finding logic.
- Independent review, commit transfer, publication, and Issue closure are not established by this
  report yet.
