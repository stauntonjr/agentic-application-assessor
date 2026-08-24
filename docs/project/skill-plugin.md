# Installable skill plugin

## Purpose and authority boundary

`agentic-engineering-harness` distributes the seven reusable workflow skills to Codex users who
want the harness methods available across repositories. It is a convenience distribution, not a
second policy authority.

| Surface | Authority | Contents |
|---|---|---|
| `.agents/skills/` | Canonical editable source | Reusable skill instructions, UI metadata, and references |
| `plugins/agentic-engineering-harness/skills/` | Generated distribution | Namespace-adjusted mirror of the canonical skills |
| `plugins/agentic-engineering-harness/PROVENANCE.json` | Generated verification record | Plugin version plus source, distribution, and transformation hashes |
| `plugins/agentic-engineering-harness/LICENSE` | Packaged legal notice | Exact copy of the repository MIT license |
| Project repository | Project authority | `AGENTS.md`, project contract, roles, loop state, ADRs, planning, code, and evidence |
| User Codex configuration | Installation preference only | Enabled plugin and marketplace coordinates |

The plugin deliberately excludes `AGENTS.md`, `.codex/`, `.github/`, `.pi/`, `docs/`, and
`harness/`. Installing it therefore cannot move public project policy into private user state. The
skills still expect the repository they operate on to provide applicable project contracts and
tools. If required repository context is absent, the agent must gather it or state that the
workflow cannot proceed; an installed skill must not invent substitute policy.

## Build and verification

Edit only the canonical `.agents/skills/` tree. Then regenerate and check the distribution:

```bash
make plugin-sync
make plugin-check
python3 /home/jrs/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/agentic-engineering-harness
```

`tools/skill_plugin.py sync --yes` copies every canonical skill file, rewrites explicit
cross-skill references into the plugin namespace, and replaces the generated mirror. The
provenance file binds the manifest, each source hash, distribution hash, transformation, and
packaged MIT license. `check` rejects missing, extra, modified, stale, or symlinked content.
`tools/harness_check.py` enforces this contract when the optional marketplace/plugin pair is
present, while adopted applications that do not carry the distribution are unaffected.

## Install

From the public Git repository:

```bash
codex plugin marketplace add stauntonjr/agentic-project-template --ref main
codex plugin add agentic-engineering-harness@agentic-project-template
```

From a reviewed local checkout during development:

```bash
codex plugin marketplace add /path/to/agentic-project-template
codex plugin add agentic-engineering-harness@agentic-project-template
```

Start a new Codex thread after installation. Select the **Agentic Engineering Harness** plugin or
invoke one of its qualified skills, for example:

```text
$agentic-engineering-harness:project-intake
$agentic-engineering-harness:research-existing-solutions
$agentic-engineering-harness:execute-engineering-loop
$agentic-engineering-harness:loop-report
```

## Repository-local collision behavior

Codex 0.149.0 was exercised in an empty Bubblewrap home. The installed plugin exposed seven
qualified names such as `agentic-engineering-harness:loop-report`. A disposable repository with
its own `loop-report` skill simultaneously exposed that skill as `loop-report` with `scope: repo`.
Both remained available in separate namespaces.

Use the unqualified repository skill when the project carries its own canonical copy. Use the
qualified plugin skill when intentionally selecting the installed distribution. The generator
also qualifies internal cross-skill calls, preventing a plugin workflow from silently switching
to a same-named repository skill. This behavior is runtime evidence for Codex 0.149.0, not a
timeless compatibility guarantee; re-run the probe when upgrading Codex:

```bash
python3 tools/skill_plugin.py probe --codex /absolute/path/to/codex
```

The probe requires Bubblewrap. It uses disposable directories bound over `~/.codex` and
`~/.agents`, installs the local marketplace and plugin, reads the plugin through Codex app-server,
tests the collision, uninstalls the plugin, removes the marketplace, and never invokes a model.

## Version, upgrade, and uninstall

The plugin has its own SemVer stream in `.codex-plugin/plugin.json`; it does not inherit the
harness or an application's product version. Before 1.0:

- patch: compatible instruction, documentation, or packaging corrections;
- minor: new skills or materially expanded workflow behavior;
- major: incompatible names, removal, or authority/installation contract changes.

Every published plugin change updates the manifest version, regenerates provenance, records the
change in `CHANGELOG.md`, and passes the isolated lifecycle probe. For a Git marketplace update:

```bash
codex plugin marketplace upgrade agentic-project-template
codex plugin add agentic-engineering-harness@agentic-project-template
```

During same-version local development, use the plugin-creator cachebuster helper instead of
hand-editing marketplace state, then reinstall and start a new thread.

Uninstall the plugin first. Remove the marketplace only when no other installed plugin depends on
it:

```bash
codex plugin remove agentic-engineering-harness@agentic-project-template
codex plugin marketplace remove agentic-project-template
```

Uninstalling changes only user installation state. It does not remove repository-local skills,
project policy, evidence, or application files.
