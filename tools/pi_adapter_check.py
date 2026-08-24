#!/usr/bin/env python3
"""Validate Pi project resources without invoking a model or installing packages."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root
except ImportError:  # Direct script execution.
    from common import load_json, repository_root


REQUIRED_COMMANDS = {
    "harness-adapter": "extension",
    "harness-intake": "prompt",
    "harness-loop": "prompt",
    "harness-report": "prompt",
    "harness-research": "prompt",
    "skill:execute-engineering-loop": "skill",
    "skill:loop-report": "skill",
    "skill:project-intake": "skill",
    "skill:research-existing-solutions": "skill",
}


def strict_schema_errors(schema: Any, path: str = "parameters") -> list[str]:
    if not isinstance(schema, dict):
        return [f"{path} is not a schema object"]
    errors: list[str] = []
    if schema.get("type") == "object":
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            errors.append(f"{path} object has no properties mapping")
        else:
            if schema.get("additionalProperties") is not False:
                errors.append(f"{path} object is not closed")
            required = schema.get("required")
            if not isinstance(required, list) or set(required) != set(properties):
                errors.append(f"{path} does not require every property")
            for name, child in properties.items():
                errors.extend(strict_schema_errors(child, f"{path}.{name}"))
    for keyword in ("anyOf", "oneOf", "allOf"):
        variants = schema.get(keyword, [])
        if isinstance(variants, list):
            for index, child in enumerate(variants):
                errors.extend(strict_schema_errors(child, f"{path}.{keyword}[{index}]"))
    items = schema.get("items")
    if isinstance(items, dict):
        errors.extend(strict_schema_errors(items, f"{path}.items"))
    return errors


def registration_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tool = payload.get("tool")
    if not isinstance(tool, dict) or tool.get("name") != "harness_questionnaire":
        return ["Pi extension did not register harness_questionnaire"]
    if tool.get("constrainedSampling") != {"type": "json_schema", "strict": "prefer"}:
        errors.append("questionnaire does not prefer JSON-schema constrained sampling")
    errors.extend(strict_schema_errors(tool.get("parameters")))
    events = payload.get("events")
    if not isinstance(events, list) or "tool_execution_start" not in events:
        errors.append("Pi extension did not register a per-call tool guard")
    if isinstance(events, list) and "turn_end" in events:
        errors.append("Pi extension retains a turn-end invalid-tool guard")

    expected = {
        "three_unknown": {"processed": 3, "aborts": 1, "entries": 1},
        "four_unknown": {"processed": 3, "aborts": 1, "entries": 1},
        "mixed_reset": {"processed": 4, "aborts": 0, "entries": 0},
        "mixed_then_three": {"processed": 5, "aborts": 1, "entries": 1},
    }
    observed = payload.get("guard")
    if observed != expected:
        errors.append(f"invalid-tool guard scenarios differ: {observed!r}")
    if payload.get("audit_entry") != {
        "type": "harness.invalid-tool-ceiling",
        "data": {"limit": 3, "observed": 3, "toolNames": ["first", "second", "third"]},
    }:
        errors.append("invalid-tool audit entry does not preserve the complete streak")
    return errors


def capture_extension_contract(root: Path, executable: str) -> dict[str, Any]:
    pi_path = Path(executable)
    package_root = pi_path.resolve().parent.parent
    node = pi_path.parent / "node"
    if not node.is_file():
        found = shutil.which("node")
        if not found:
            raise OSError("node executable not found for Pi extension contract probe")
        node = Path(found)
    script = r"""
const { createJiti } = require("jiti");
(async () => {
  const loaded = createJiti(process.cwd() + "/pi-extension-probe.js")(process.argv[1]);
  const factory = loaded.default;
  let tool;
  const handlers = {};
  let entries = [];
  const pi = {
    registerCommand() {},
    registerTool(value) { tool = value; },
    on(name, handler) { handlers[name] = handler; },
    getActiveTools() { return ["read", "harness_questionnaire"]; },
    appendEntry(type, data) { entries.push({ type, data }); },
  };
  factory(pi);
  async function drive(names) {
    let aborts = 0;
    let processed = 0;
    entries = [];
    await Promise.resolve(handlers.agent_start({}));
    const ctx = { abort() { aborts += 1; }, ui: { notify() {} } };
    for (const toolName of names) {
      await Promise.resolve(handlers.tool_execution_start({ toolName }, ctx));
      processed += 1;
      if (aborts > 0) break;
    }
    return { processed, aborts, entries: entries.length };
  }
  const guard = {
    three_unknown: await drive(["missing", "missing", "missing"]),
    four_unknown: await drive(["missing", "missing", "missing", "missing"]),
    mixed_reset: await drive(["missing", "read", "missing", "missing"]),
    mixed_then_three: await drive(["missing", "read", "missing", "missing", "missing"]),
  };
  await drive(["first", "second", "third"]);
  const auditEntry = entries[entries.length - 1];
  process.stdout.write(JSON.stringify({
    tool: {
      name: tool && tool.name,
      constrainedSampling: tool && tool.constrainedSampling,
      parameters: tool && tool.parameters,
    },
    events: Object.keys(handlers).sort(),
    guard,
    audit_entry: auditEntry,
  }));
})().catch((error) => { console.error(error); process.exit(1); });
"""
    environment = os.environ.copy()
    environment["NODE_PATH"] = str(package_root / "node_modules")
    result = subprocess.run(
        [str(node), "-e", script, str(root / ".pi/extensions/context-readiness.ts")],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
        env=environment,
        timeout=15,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "Pi extension contract probe failed")
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise TypeError("Pi extension contract probe returned a non-object")
    return payload


def command_errors(payload: dict[str, Any]) -> list[str]:
    commands = payload.get("data", {}).get("commands", [])
    observed = {item.get("name"): item.get("source") for item in commands}
    errors: list[str] = []
    for name, source in sorted(REQUIRED_COMMANDS.items()):
        if observed.get(name) != source:
            errors.append(f"missing {source} command: {name}")
    return errors


def run_check(root: Path, executable: str) -> dict[str, Any]:
    manifest = load_json(root / "harness/adapters/pi.json")
    tested_versions = manifest.get("runtime", {}).get("tested_versions", [])
    version_result = subprocess.run(
        [executable, "--version"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
        timeout=10,
    )
    version = version_result.stdout.strip()
    errors: list[str] = []
    registration = capture_extension_contract(root, executable)
    errors.extend(registration_errors(registration))
    if version_result.returncode != 0:
        errors.append(version_result.stderr.strip() or "pi --version failed")
    elif version not in tested_versions:
        errors.append(f"Pi {version} is not in tested_versions: {tested_versions}")

    response: dict[str, Any] | None = None
    extension_errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pi-adapter-check-") as config_dir:
        environment = os.environ.copy()
        environment["PI_CODING_AGENT_DIR"] = config_dir
        environment["PI_OFFLINE"] = "1"
        rpc = subprocess.run(
            [executable, "--approve", "--mode", "rpc", "--no-session"],
            cwd=root,
            check=False,
            text=True,
            input=json.dumps({"type": "get_commands"}) + "\n",
            capture_output=True,
            env=environment,
            timeout=15,
        )
    if rpc.returncode != 0:
        errors.append(rpc.stderr.strip() or f"Pi RPC exited {rpc.returncode}")
    for line in rpc.stdout.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("type") == "extension_error":
            extension_errors.append(item.get("error", json.dumps(item, sort_keys=True)))
        if item.get("type") == "response" and item.get("command") == "get_commands":
            response = item
    errors.extend(f"extension error: {message}" for message in extension_errors)
    if response is None:
        errors.append("Pi RPC did not return get_commands")
        commands: list[dict[str, Any]] = []
    else:
        if not response.get("success"):
            errors.append(f"get_commands failed: {response.get('error', 'unknown error')}")
        errors.extend(command_errors(response))
        commands = response.get("data", {}).get("commands", [])

    return {
        "ok": not errors,
        "pi": executable,
        "version": version,
        "tested_versions": tested_versions,
        "offline": True,
        "model_invoked": False,
        "extension_contract": {
            "registered_tool": registration.get("tool", {}).get("name"),
            "event_handlers": registration.get("events", []),
            "guard_scenarios": registration.get("guard", {}),
        },
        "required_commands": sorted(REQUIRED_COMMANDS),
        "observed_project_commands": sorted(
            item.get("name", "")
            for item in commands
            if item.get("sourceInfo", {}).get("scope") == "project"
        ),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--pi", dest="executable")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    executable = args.executable or shutil.which("pi")
    if not executable:
        print(json.dumps({"ok": False, "errors": ["pi executable not found"]}, indent=2))
        return 1
    try:
        result = run_check(root, executable)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result = {"ok": False, "errors": [str(exc)]}
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
