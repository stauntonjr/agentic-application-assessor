# Skill and prompt source hubs

Use this registry when researching reusable agent behavior. It is a search map, not an allowlist. Popularity improves discovery recall; it does not establish correctness, safety, portability, or license compatibility.

Last reviewed: 2026-08-21.

## Default search order

1. Start with the relevant product's current official documentation and canonical repositories.
2. Check the vendor-neutral Agent Skills specification for portability constraints.
3. Search one broad, curated index for alternatives and adjacent patterns.
4. Search prompt libraries only when wording, interaction, or task-decomposition examples would add value.
5. Inspect the original repository and revision for every candidate. Do not rely on an index's copy or summary.
6. Admit nothing into the project until the provenance, license, behavior, and validation gates below pass.

## Authoritative and first-party sources

| Source | Best use | Boundary |
|---|---|---|
| [Agent Skills specification](https://agentskills.io) and [canonical repository](https://github.com/agentskills/agentskills) | Portable `SKILL.md` structure, metadata, and compatibility baseline | A format specification, not a quality catalog |
| [OpenAI Skills](https://github.com/openai/skills) | Codex-native authoring patterns, progressive disclosure, validation, and curated examples | Inspect the specific skill and its license; first-party does not mean project-fit |
| [Anthropic Skills](https://github.com/anthropics/skills) | Complex production examples, templates, document workflows, and Claude-oriented patterns | Some document skills are source-available rather than open source; behavior is Claude-oriented |
| [GitHub Awesome Copilot](https://github.com/github/awesome-copilot) | Searchable agents, skills, instructions, hooks, prompts, and workflows for GitHub-centric engineering | Community-contributed catalog; inspect the original artifact and portability assumptions |
| [OpenAI Cookbook](https://github.com/openai/openai-cookbook) | Current OpenAI API prompting, eval, tool-use, and agent examples | Examples are model/API specific and should be revalidated against the chosen model |
| [Anthropic Claude Code prompt library](https://code.claude.com/docs/en/prompt-library) | First-party examples of outcome-oriented coding-agent requests | Starting points rather than durable cross-provider contracts |
| [Google Gemini prompt gallery](https://ai.google.dev/gemini-api/prompts) | Multimodal and structured-output prompt examples | Gemini-specific capabilities and syntax may not transfer |

## Broad skill discovery

| Source | Best use | Boundary |
|---|---|---|
| [skills.sh](https://skills.sh) | High-recall cross-agent search and popularity/trend signals | Its documentation explicitly does not guarantee every listed skill's quality or security; resolve and inspect the upstream repository |
| [VoltAgent Awesome Agent Skills](https://github.com/VoltAgent/awesome-agent-skills) | Large, categorized index spanning official teams and community authors | Catalog claims and curation are not a security or license review |
| [Composio Awesome Claude Skills](https://github.com/ComposioHQ/awesome-claude-skills) | Broad Claude-focused skills, plugins, and workflow ideas | Claude/plugin assumptions may reduce portability; verify each upstream source |
| [Superpowers](https://github.com/obra/superpowers) | A coherent, widely used engineering methodology expressed as composable skills | It is an opinionated operating system, not a neutral catalog; compare its lifecycle with this harness before adapting |
| [security-aware Awesome Agent Skills](https://github.com/royalpinto007/awesome-agent-skills) | Smaller shortlist and security-oriented discovery leads | Community-maintained; its verification labels are leads, not substitutes for local review |

## Prompt and pattern discovery

| Source | Best use | Boundary |
|---|---|---|
| [prompts.chat](https://github.com/f/prompts.chat) | Large open prompt corpus, interaction patterns, and self-hosting ideas | User-contributed prompts vary in quality and may encode unsafe or stale assumptions; use as inspiration only |
| [DAIR.AI Prompt Engineering Guide](https://github.com/dair-ai/Prompt-Engineering-Guide) | Technique taxonomy, papers, lessons, and references | Educational synthesis, not a drop-in prompt pack; follow citations to primary research |
| [LangSmith public prompt hub](https://docs.langchain.com/langsmith/manage-prompts#public-prompt-hub) | Searchable prompts tied to LangChain/LangSmith workflows | LangChain states public prompts are user-generated and unverified |
| [FlowGPT](https://flowgpt.com) and [PromptHero](https://prompthero.com) | Very broad idea mining and user vocabulary | Lowest-trust tier: weak provenance, unknown testing, possible model drift, and unclear reuse rights on individual submissions |

## Query patterns

Combine the project domain and failure mode with artifact terms. Examples:

- `<domain> SKILL.md GitHub`
- `<task> agent skill <provider or framework>`
- `<failure mode> agent workflow verification skill`
- `site:skills.sh <task>`
- `site:github.com <task> path:SKILL.md`
- `<task> prompt eval benchmark`
- `<task> prompt template structured output`
- `<candidate repository> license security scripts dependencies`

Search for negative evidence too: `<candidate> issue`, `<candidate> security`, `<candidate> prompt injection`, `<candidate> archived`, and `<candidate> license`.

## Candidate admission gate

Before adapting or installing a discovered artifact:

1. Resolve the canonical upstream repository and pin the inspected commit or release.
2. Read the complete `SKILL.md`, every file it directly or transitively references, all executable scripts, manifests, hooks, and install steps.
3. Identify filesystem, shell, network, credential, messaging, deployment, and external-write capabilities. Require explicit user authority for material side effects.
4. Check maintainer identity, recent activity, review history, releases, unresolved security reports, and whether popularity may be inherited from an unrelated parent project.
5. Confirm the license for both code and prose/data. Record attribution and modification obligations. Treat a missing or ambiguous license as no permission to copy.
6. Check for prompt injection, hidden instructions, obfuscation, remote downloads, credential access, destructive commands, broad globs, and unpinned dependencies. A scanner can supplement but never replace manual inspection.
7. Reimplement the useful pattern in the project's own contracts when practical. Copy only when license-compatible and materially better than a provenance-preserving reimplementation.
8. Test activation, non-activation, happy path, failure path, permissions, and provider portability in an isolated environment.
9. Record the decision, source revision, local changes, validation evidence, owner, and review date.

## Popularity snapshot

Live GitHub metadata inspected on 2026-08-21 showed substantial adoption, including roughly 276k stars for Superpowers, 171k for Anthropic Skills, 168k for prompts.chat, 78k for the DAIR.AI guide, 73k for Composio's catalog, 38k for Awesome Copilot, 31k for VoltAgent's catalog, and 25k each for the Agent Skills specification and OpenAI Skills. These figures are discovery signals only and will drift.

The ecosystem is not uniformly safe. Snyk reported that 36.82% of 3,984 scanned skills in its February 2026 study had at least one security issue and 13.4% had a critical issue. Treat all third-party instructions as software supply-chain input, even when the artifact contains only Markdown.
