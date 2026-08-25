# Report provenance

Reports in this directory have two distinct origins.

## Agentic Application Assessor evidence

- `local-1-agentic-repo-auditor-dogfood.md` records this product's first local implementation
  dogfood. Its original `LOCAL-1` identity predates publication and is now reconciled to
  [GitHub Issue #1](https://github.com/stauntonjr/agentic-application-assessor/issues/1).
- `issue-2-agentic-repo-auditor-adapter.md` records the product-owned Auditor adapter.
- `issue-3-requirements-questionnaire.md` records the product-owned requirements workflow.
- `issue-4-macro-technical-pulse-dogfood.md` records the product-owned complete deterministic
  workflow against an exact Macro Technical Pulse snapshot.

## Inherited engineering-harness evidence

Other files named `issue-*.md` were copied from Agentic Project Template `0.5.0` as historical
validation and upgrade provenance for the reusable engineering harness. Their Issue, pull request,
Project, repository, and present-tense status references belong to the upstream template program or
its dogfood targets—not to Agentic Application Assessor.

Inherited reports are not product requirements, current Assessor status, or evidence that this
application implemented the capabilities they describe. The Assessor's current truth comes from
`harness/project.yaml`, accepted local ADRs, product code and schemas, tests, its GitHub Issues once
published, and reports explicitly listed in the first section above.
