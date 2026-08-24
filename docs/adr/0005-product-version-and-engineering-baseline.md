# ADR-0005: Separate product versioning and profile-driven engineering baseline

Status: accepted

## Context

The harness already has a release version used for template upgrades. A derived application needs an independent compatibility and release contract. Concrete engineering tools also vary by language, artifact, deployment model, and repository risk, while the capabilities they provide are broadly consistent.

## Decision

Keep `harness_version` independent from `engineering.versioning.current`. Require project intake to select a versioning strategy, identify the public compatibility contract, name the canonical version source, and define pre-1.0 behavior. [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) is a supported choice, not a universal mandate.

Require every completed engineering loop to record a product release impact of `none`, `patch`, `minor`, or `major` with rationale. Agents recommend impact; the human release authority approves version changes and publication.

Profiles define required capabilities and defaults. The portable contract covers a primary local/CI command, runtime and dependency reproducibility, formatting, linting, type checking, tests, coverage policy, and clean package or build smoke. A profile selects concrete tools; unsupported checks are resolved explicitly rather than silently passing.

GitHub security defaults include dependency updates, dependency review, CodeQL, secret scanning and push protection expectations, least-privilege permissions, and full-commit-SHA Action references. Repository settings remain audited external state and are not inferred from committed workflow files.

## Consequences

- Harness upgrades do not imply application releases.
- Version numbers carry meaning only after the public contract is defined.
- CI and local commands share one declared boundary, while local hooks remain optional accelerators.
- Language-specific tools do not leak into the provider-neutral core.
- Private repositories without the required GitHub security entitlement skip the bundled dependency-review and CodeQL jobs unless explicitly enabled.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Use the harness version as the application version | Couples unrelated release streams and makes upgrades look like product releases |
| Require SemVer for every project | SemVer requires a meaningful public compatibility contract and is a poor fit for some continuously delivered or date-oriented systems |
| Hard-code one Python toolchain globally | The template must support non-Python and mixed-language projects |
| Let commit syntax publish automatically | Commit labels do not reliably establish semantic compatibility or human release authorization |
