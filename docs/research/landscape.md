# Agentic engineering harness landscape

Research date: 2026-08-21.

## Findings

The ecosystem has mature components but no dominant full repository operating system. The widely adopted projects emphasize specification, instruction discovery, standards, or skill catalogs. The closest complete template repositories remain young and lightly adopted.

| Resource | Observed strength | Boundary or caution |
|---|---|---|
| [AGENTS.md](https://github.com/agentsmd/agents.md) | Portable repository guidance | Instructions alone do not enforce behavior |
| [GitHub Spec Kit](https://github.com/github/spec-kit) | Intent-driven spec, plan, task, and implementation lifecycle | Specification lifecycle is not the whole control plane |
| [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) | Product, architecture, development, and testing perspectives | Large methodology; tailor to avoid ceremony |
| [Agent OS](https://github.com/buildermethods/agent-os) | Standards profiles and structured specification | Less coverage of CI, GitHub state, and evidence reporting |
| [Awesome Copilot](https://github.com/github/awesome-copilot) | Broad agent, skill, hook, and workflow catalog | Catalog rather than one coherent operating model |
| [Harness Engineering](https://github.com/ArtemisAI/Harness_Engineering) | Session loops, roles, schemas, and CI ideas | Very young; no declared license in the inspected metadata |
| [Agentic Engineering Starter Pack](https://github.com/tngwilkins/agentic-engineering-starter-pack) | Staged knowledge base and human gates | GPL-3.0; concepts were reviewed but code was not copied |
| [Agentic Engineering](https://github.com/affectionatec/agentic-engineering) | Durable specs, decisions, and independent verification | Young project and documentation-heavy approach |
| [Agentic Engineering Harness](https://github.com/ldaume/agentic-engineering-harness) | Evidence-driven value-stream and autonomy patterns | Blueprint/catalog rather than project control plane |
| [Project Bootstrap skill](https://github.com/garethrhughes/skills/blob/main/project-bootstrap/SKILL.md) | Phased questionnaire and profile defaults | Very large, stack-specific interview |
| [GitHub Agentic Workflows](https://docs.github.com/en/copilot/concepts/agents/about-github-agentic-workflows) | Bounded AI automation with safe outputs | Public preview; untrusted-input and permission risks remain |
| [Pi](https://github.com/earendil-works/pi) | Minimal, extensible coding-agent harness with native skills, prompts, extensions, SDK, and RPC | Project extensions run with user permissions; orchestration remains user-selected |
| [rpiv-mono](https://github.com/juicesharp/rpiv-mono) | Structured questions, durable tasks, reviewers, and typed workflows | Opinionated and fast-moving component suite rather than portable project governance |
| [Pi Dynamic Workflows](https://github.com/QuintinShaw/pi-dynamic-workflows) | Parallel pipelines, worktrees, journals, budgets, and resumability | Adds a runtime orchestration layer and dependency trust surface |
| [Pi Goal/List/Loop Audit](https://github.com/DraconDev/pi-goal-list-loop-audit) | Mechanical goal contracts, evidence-aware audit, stale-revision refusal, and loop plateau controls | AGPL-3.0; concepts only were reviewed and independently reimplemented |
| [Pi Subagent Tasks](https://github.com/harms-haus/pi-subagent-tasks) | Work-review-resume gates, exact session identity, worktree isolation, and bounded recovery | Young Pi-specific orchestrator; patterns do not justify a canonical dependency |
| [MinhDuyDEV Pi Harness](https://github.com/MinhDuyDEV/pi-harness) | Full Pi distribution with roles, skills, policy, prompts, and evidence | Direct prior art but currently lightly adopted and tied to a narrow Pi version range |

Live GitHub metadata observed during research:

- Spec Kit: about 130,689 stars, MIT.
- BMAD Method: about 52,147 stars; GitHub metadata did not declare a SPDX license.
- Agent OS: about 5,310 stars, MIT.
- AGENTS.md: about 23,779 stars, MIT.
- Awesome Copilot: about 38,099 stars, MIT.
- Harness Engineering: 14 stars, marked as a template, no declared SPDX license.
- Agentic Engineering Starter Pack: 10 stars, marked as a template, GPL-3.0.
- Pi: about 95,070 stars, 11,766 forks, MIT, with activity observed on the research date.
- rpiv-mono: about 654 stars, 120 forks, MIT.
- Pi Dynamic Workflows: about 432 stars, 87 forks, MIT.
- Pi Goal/List/Loop Audit: 12 stars, 7 forks, AGPL-3.0.

Counts are a dated snapshot and will drift.

## Current product contracts used

- [OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills): repository skills live under `.agents/skills`, use concise triggering descriptions, and load through progressive disclosure.
- [OpenAI AGENTS.md documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md): project guidance is layered from repository root toward the current directory and closer files override broader guidance.
- [OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents): use parallel agents mainly for independent read-heavy work; custom project agents live in `.codex/agents` and require name, description, and developer instructions.
- [GitHub repository template documentation](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template): templates copy repository files and directory structure. Projects, rulesets, secrets, permissions, and other live settings need separate reconciliation.

## Skill and prompt discovery hubs

The reusable research skill now carries a dated [source-hub registry](../../.agents/skills/research-existing-solutions/references/source-hubs.md). It routes future research through four distinct evidence tiers:

- authoritative specifications and first-party examples;
- broad skill indexes for discovery recall;
- coherent workflow systems for methodology comparison;
- prompt libraries for interaction patterns and vocabulary, not direct production adoption.

The registry includes Agent Skills, OpenAI Skills, Anthropic Skills, Awesome Copilot, skills.sh, VoltAgent, Composio, Superpowers, prompts.chat, DAIR.AI, LangSmith, and lower-trust community prompt sites. It also defines an admission gate covering canonical provenance, pinned revisions, complete instruction and script inspection, permissions, licensing, security, isolated validation, and durable decision evidence.

Popularity is intentionally not an allowlist. Live GitHub metadata showed several hubs with tens or hundreds of thousands of stars, while [skills.sh's own documentation](https://www.skills.sh/docs) says it cannot guarantee every listed skill's quality or security. [Snyk's 2026 ToxicSkills study](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/) found security issues in 36.82% of 3,984 scanned skills, including critical issues in 13.4%. This makes third-party skill intake a software supply-chain workflow, not a copy-and-paste workflow.

## Principles adopted

- Minimal `AGENTS.md` plus progressively disclosed skills.
- Durable source precedence and explicit authority.
- Questionnaire answers with status, source, and date.
- Deterministic loop boundaries and reports.
- Issues as canonical work; Projects as views.
- Dry-run desired-state reconciliation before live writes.
- Independent verification and human-controlled release.
- Historical defects as executable challenges.
- Versioned harness migrations instead of silent template drift.
- Provider capability manifests that distinguish native support, prompt mediation, extensions, and unsupported boundaries.
- A thin Pi adapter with no third-party packages, no project-wide model preferences, and an explicit external sandbox boundary.
- Stable acceptance IDs, content-aware dirty baselines, narrow declared write sets, and revision/attempt/candidate-bound verifier verdicts.

## Pi adapter evidence

Pi's official documentation inspected on 2026-08-21 says it loads project `AGENTS.md`, `.agents/skills/`, `.pi/prompts/`, `.pi/extensions/`, and `.pi/settings.json` after project trust. It also states that packages and extensions can execute arbitrary code with full user access. The adapter therefore reuses native instruction and Agent Skills discovery, adds only a small local questionnaire extension, stores sessions under ignored `.harness/` state, and leaves model/provider choices personal.

Pi's official package catalog listed 5,372 entries on the research date. That is evidence of active experimentation, not evidence that the packages are mature, mutually compatible, or appropriate dependencies. Representative repositories were inspected for patterns only; no third-party Pi code was copied into this template.

## Pi loop-integrity patterns adopted

The v0.4 loop-integrity decision used pinned snapshots of [Pi Dynamic Workflows at `fad6ef3`](https://github.com/QuintinShaw/pi-dynamic-workflows/tree/fad6ef36990394621b08b245b16d355ccdfcc175), [Pi Goal/List/Loop Audit at `4418063`](https://github.com/DraconDev/pi-goal-list-loop-audit/tree/44180631f1f8c3a2499dee88561e3c7b8a77cbc9), [rpiv-mono at `68e40c5`](https://github.com/juicesharp/rpiv-mono/tree/68e40c5eeec71b8b299914d0205b7d2e67862236), [MinhDuyDEV Pi Harness at `b71a45f`](https://github.com/MinhDuyDEV/pi-harness/tree/b71a45f712913c93e0d5e4c8a9e27173ebceab19), and [Pi Subagent Tasks at `d1535c1`](https://github.com/harms-haus/pi-subagent-tasks/tree/d1535c1f2c1007507effd6d14757c07c8ae2fa45). The implemented tranche is deliberately narrower than those systems: acceptance-to-check mapping, stale-verdict rejection, implementer/verifier identity separation, and baseline-relative write-scope enforcement. Journaling, deterministic resume, retry taxonomy, failure memos, and runtime watchdogs remain future candidates.

This repository is an original reimplementation based on these general patterns and lessons from S3NTINEL, Kortex, Procurement Intelligence Lab, and Macro Technical Pulse. No third-party template code was copied.
