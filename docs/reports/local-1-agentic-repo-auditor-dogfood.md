# Issue #1 / LOCAL-1 Agentic Repo Auditor dogfood

- Published work item:
  [GitHub Issue #1](https://github.com/stauntonjr/agentic-application-assessor/issues/1).

- Assessment date: 2026-08-24.
- Assessor: `agentic-application-assessor 0.1.0` from the active local implementation loop.
- Target: `/home/jrs/agentic-repo-auditor` at exact outer revision
  `59ae45521ae005039a8ac5ea196293c59779f1c7`, branch `main`, clean.
- Context: `examples/agentic-repo-auditor.context.json`, accepted context schema `1.0`.
- Execution boundary: local static inspection only; no target code, build, dependency, network,
  model, runtime, or Auditor adapter execution.

## Repeatability and integrity evidence

Two independent JSON executions produced the same SHA-256:

`7efd5fd7da86aa9d14158aa7e515c69cc09e939a3c883f74a63deca86d466adf`

The deterministic Markdown SHA-256 was:

`779c9023c31181961b750f4e5f4ccd0a6d89dfc755b457ebab32ab35802bc41f`

Before and after all three executions, the target remained clean and retained:

- HEAD `59ae45521ae005039a8ac5ea196293c59779f1c7`;
- `.git/index` SHA-256
  `1b6aec8a5448b7849ecbc69abb98b16092079e1d2f9ddf438fa77a7de934a56b`; and
- `.git/HEAD` SHA-256
  `28d25bf82af4c0e2b72f50959b2beb859e3e60b9630a5e8c603dad4ddb2b6e80`.

The assessor's target identity was
`sha256:0c5440603c5f00332b50a56ef306d55f5a0bd549ff2c94378c4d41db114777f2`.

## Report result

The report contained 62 evidence records and three claims. Static coverage found two
configuration files, 25 documentation files, two entrypoints, two manifests, 13 schemas, and 13
test files. The accepted purpose and stakeholder declarations were preserved, and the declared
Auditor CLI component path was present. No contradiction was detected at this boundary.

The report explicitly left seven gaps unresolved. Each is now a structured item with a stable ID,
`unavailable` origin, status, and exact context, target-state, or policy source:

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
adapter is tracked by
[Issue #2](https://github.com/stauntonjr/agentic-application-assessor/issues/2) and must validate and
rerun canonical Agentic Repo Auditor `0.1.0` schema-`1.2` JSON against the same target state, as
specified by the accepted intake. Macro Technical Pulse dogfood remains tracked by
[Issue #4](https://github.com/stauntonjr/agentic-application-assessor/issues/4) after that adapter and
a richer accepted context packet.
