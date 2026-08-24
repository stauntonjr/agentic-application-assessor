# Engineering baseline

## Universal capability contract

Every instantiated project resolves these capabilities during intake:

| Capability | Contract |
|---|---|
| Primary check | One authoritative command runs the required local and CI boundary |
| Runtime | Supported runtime versions are explicit |
| Dependencies | Dependencies are locked when present and updated through reviewed pull requests |
| Static quality | Formatter, linter, and type-checking disposition are explicit |
| Verification | Unit plus profile-required integration, contract, regression, or end-to-end tests |
| Coverage | Ratchet from an observed baseline or record an explicit exception |
| Packaging | Exercise the installed package, binary, container, or deployed entrypoint in a clean boundary |
| Security | Dependency review, code scanning, secret controls, least privilege, and immutable Action references |
| Release | Product version, changelog, migration impact, artifact identity, and human authorization |

`TBD` is valid only while the repository remains in template or provisional intake mode. Do not implement a check as a successful no-op. Mark it not applicable with a recorded reason or configure a real command.

`make smoke` is the authoritative portable entrypoint. In an instantiated project it dispatches every capability listed in `engineering.quality.required_checks` through `tools/run_quality.py`, after the configured bootstrap command. The same entrypoint runs in CI.

## Profiles

The `generic` profile names capabilities without imposing an ecosystem. The `python-data` profile supplies pinned `uv` commands for Ruff, Pyright, pytest, pytest-cov, and Hypothesis. It requires a measured branch-coverage baseline before release. Once a product package exists, intake must replace the profile's explicit `not-applicable` package-smoke value with a clean-install command; `tools/python_package_smoke.py` is the dependency-free default helper. A project must separately exercise its real public entrypoint. Web-service and agent-system profiles add their domain-specific boundaries without selecting a language toolchain.

Local hooks are optional. CI remains authoritative because hooks can be skipped.

## GitHub boundary

The repository includes Dependabot for GitHub Actions, dependency review, and CodeQL for the Python harness. Add application languages and package ecosystems during adoption. Every external Action or reusable workflow is pinned to a full commit SHA, and `.github/actions-allowlist.json` records the exact write permissions reviewed for each workflow. Secret scanning, push protection, repository rules, and CodeQL eligibility are live GitHub settings and require a separate audit; their presence must not be inferred from files alone.

Public release artifacts should add checksums and, when useful to consumers, an SBOM and build-provenance attestation. Test-only artifacts do not need release attestations.
