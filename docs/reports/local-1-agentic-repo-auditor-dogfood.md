# LOCAL-1 Agentic Repo Auditor dogfood

- Assessment date: 2026-08-24.
- Assessor: `agentic-application-assessor 0.1.0` from the active local implementation loop.
- Target: `/home/jrs/agentic-repo-auditor` at exact outer revision
  `59ae45521ae005039a8ac5ea196293c59779f1c7`, branch `main`, clean.
- Context: `examples/agentic-repo-auditor.context.json`, accepted context schema `1.0`.
- Execution boundary: local static inspection only; no target code, build, dependency, network,
  model, runtime, or Auditor adapter execution.

## Repeatability and integrity evidence

Two independent JSON executions produced the same SHA-256:

`cea813873490cf1a1b718ee8f9321d80d760f410004551765f5033787df8b966`

The deterministic Markdown SHA-256 was:

`0bb4ca1fc8b4c6e80795bacb1b053091a4dffde9d438c93f68ef96022a917372`

Before and after all three executions, the target remained clean and retained:

- HEAD `59ae45521ae005039a8ac5ea196293c59779f1c7`;
- `.git/index` SHA-256
  `1b6aec8a5448b7849ecbc69abb98b16092079e1d2f9ddf438fa77a7de934a56b`; and
- `.git/HEAD` SHA-256
  `28d25bf82af4c0e2b72f50959b2beb859e3e60b9630a5e8c603dad4ddb2b6e80`.

The assessor's target identity was
`sha256:2480ee656f4c6f182735e055d05f7842123dcec48262142896e1b0c0e2161669`.

## Report result

The report contained 62 evidence records and three claims. Static coverage found two
configuration files, 25 documentation files, two entrypoints, two manifests, 13 schemas, and 13
test files. The accepted purpose and stakeholder declarations were preserved, and the declared
Auditor CLI component path was present. No contradiction was detected at this boundary.

The report explicitly left seven gaps unresolved:

- data assets and movement;
- important runtime workflows;
- deployment evidence;
- interface evidence;
- runtime behavior;
- production topology; and
- model synthesis.

This is a useful first result because it refuses to turn a repository inventory into a full
application claim. It demonstrates deterministic evidence compilation and identifies exactly what
the next questionnaire or adapter must establish.

## Follow-up decision

Do not close the product's broader Auditor integration scope from this dogfood. The next bounded
adapter must validate and rerun canonical Agentic Repo Auditor `0.1.0` schema-`1.2` JSON against the
same target state, as specified by the accepted intake. Macro Technical Pulse dogfood remains after
that adapter and a richer accepted context packet.
