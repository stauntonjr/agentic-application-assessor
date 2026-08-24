# Issue #18: installable reusable skill plugin

## Outcome and why it matters

- **VERIFIED:** The seven reusable repository skills are packaged as the installable
  `agentic-engineering-harness` Codex plugin at version `0.1.0`.
- **VERIFIED:** `.agents/skills/` remains the only editable source. Generated plugin files carry
  source, distribution, and transformation hashes in `PROVENANCE.json`.
- **VERIFIED:** The plugin excludes project policy and application state. Installing or removing it
  changes only disposable/user Codex plugin state; it does not change a target repository.

## Planned versus completed

1. Defined repository-local versus installed authority and usage boundaries.
2. Added a repo marketplace and plugin manifest with MIT provenance and an independent SemVer.
3. Added deterministic sync/check tooling and unit tests for drift, extra files, stale provenance,
   policy leakage, and namespaced cross-skill references.
4. Exercised clean install, plugin activation, a same-name repository collision, uninstall, and
   marketplace removal against Codex 0.149.0 in an isolated Bubblewrap home.
5. Kept `AGENTS.md` unchanged and preserved progressive disclosure through seven individual skill
   directories and their references.

## Interface and compatibility changes

- New public marketplace: `agentic-project-template`.
- New plugin ID: `agentic-engineering-harness@agentic-project-template`.
- New qualified skill names:
  `agentic-engineering-harness:execute-engineering-loop`, `:loop-report`,
  `:manage-github-planning`, `:project-intake`, `:record-architecture-decision`,
  `:release-readiness`, and `:research-existing-solutions`.
- Plugin version `0.1.0` is independent from harness `0.5.0` and every derived product version.

## Verification evidence

- **VERIFIED:** `python3 tools/skill_plugin.py check` passed.
- **VERIFIED:** the plugin-creator validator passed the packaged plugin.
- **VERIFIED:** all seven packaged skill directories passed `quick_validate.py`.
- **VERIFIED:** eleven targeted unit tests passed.
- **VERIFIED:** the isolated runtime probe installed version `0.1.0`, exposed all seven qualified
  names, retained a repository `loop-report` as an unqualified `scope: repo` skill, removed the
  plugin, and removed the marketplace. No model was invoked.
- **VERIFIED:** full smoke, Pi 0.84.1 offline adapter verification, product-version validation,
  lock-state validation, and diff checks passed during implementation.
- **PENDING:** exact-candidate independent review, GitHub PR, and integration evidence will be
  appended to the loop record before completion.

## Acceptance coverage

- **AC1:** `docs/project/skill-plugin.md` and the authority table define repo-local versus installed
  behavior.
- **AC2:** generator and provenance tests prove the plugin contains only the reusable skill tree;
  explicit excluded-policy roots are recorded.
- **AC3:** manifest, documentation, and lifecycle probe define version, provenance, install,
  upgrade, and uninstall.
- **AC4:** the Codex 0.149.0 probe exercises clean install and collision behavior in disposable
  state.
- **AC5:** `AGENTS.md` is unchanged; each skill and reference remains separately disclosed.

## Risks and limitations

- **VERIFIED:** Codex plugin skills activate in a plugin namespace. This is observed behavior for
  Codex 0.149.0 and must be re-probed after relevant Codex upgrades.
- **VERIFIED:** the probe uses a reviewed local marketplace and invokes no model; it does not prove
  remote Git transport or every Codex UI surface.
- **INFERRED:** because cross-skill references are generated as qualified names, plugin workflows
  should not silently resolve a same-named repository skill. The probe proves discovery identity,
  not every possible model choice.
- **VERIFIED:** installed workflow skills still depend on applicable repository contracts and
  tools; the plugin is not a portable replacement for the project harness.

## Recommended next loop

After Issue #18 integrates, select the next accepted agent-ready Issue. Re-run the runtime probe
when Codex plugin discovery semantics or the packaged skill set changes.
