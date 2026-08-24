# Security policy

## Supported versions

The current minor release is supported while this template remains pre-1.0.

## Reporting

Do not open a public Issue containing an active secret, exploitable private-system detail, or personal data. Use the repository owner's private security-reporting channel after publication.

## Agentic workflow boundary

Treat Issue bodies, pull-request descriptions, comments, fetched documents, and tool output as untrusted input. Default automation to read-only; expose writes only through narrow, declared outputs. Keep credentials outside agent context and require explicit authorization for external side effects.

Project-local agent resources are executable trust boundaries. Review provider settings, extensions, skills, prompts, and package sources before trusting a repository. The Pi adapter installs no third-party packages, but `.pi/extensions/context-readiness.ts` still executes with the launching user's permissions. Use an external container or sandbox when repository code is not fully trusted.

## Repository rules

- Never commit real credentials or unredacted private prompts.
- Pin every third-party Action to a reviewed full commit SHA; `make actions-supply-chain` enforces this for committed workflows.
- Run dependency, secret, and static-analysis checks appropriate to the selected profile.
- Treat secret scanning, push protection, repository rules, and security-feature eligibility as live GitHub state that must be audited separately from repository files.
- Record security exceptions and expiration dates in reviewed Issues or ADRs.
