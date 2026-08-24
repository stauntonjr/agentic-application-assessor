#!/usr/bin/env python3
"""Execute the selected project's profile-driven quality command contract."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root
except ImportError:  # Direct script execution.
    from common import load_json, repository_root


CHECK_ORDER = (
    "format_check",
    "lint",
    "typecheck",
    "unit",
    "integration",
    "package_smoke",
)
NOOP_EXECUTABLES = {":", "true", "/bin/true", "/usr/bin/true"}


def command_argv(command: Any, capability: str) -> list[str]:
    if not isinstance(command, str) or not command.strip() or command == "TBD":
        raise ValueError(f"required quality capability is unresolved: {capability}")
    if command.startswith("not-applicable:"):
        raise ValueError(f"required quality capability is marked not applicable: {capability}")
    argv = shlex.split(command)
    if not argv:
        raise ValueError(f"required quality capability has an empty command: {capability}")
    if argv[0] in NOOP_EXECUTABLES or (argv[0] == "exit" and argv[1:] == ["0"]):
        raise ValueError(f"quality capability is a successful no-op: {capability}")
    return argv


def quality_commands(root: Path, *, bootstrap: bool = True) -> list[tuple[str, list[str]]]:
    project = load_json(root / "harness/project.yaml")
    if project.get("template_mode"):
        return []
    engineering = project["engineering"]
    contract = engineering["command_contract"]
    required = engineering["quality"]["required_checks"]
    unknown = sorted(set(required) - set(CHECK_ORDER))
    if unknown:
        raise ValueError(f"unknown required quality capabilities: {', '.join(unknown)}")
    commands: list[tuple[str, list[str]]] = []
    bootstrap_command = contract.get("bootstrap")
    if (
        bootstrap
        and isinstance(bootstrap_command, str)
        and bootstrap_command != "TBD"
        and not bootstrap_command.startswith("not-applicable:")
    ):
        commands.append(("bootstrap", command_argv(bootstrap_command, "bootstrap")))
    for capability in CHECK_ORDER:
        if capability in required:
            commands.append((capability, command_argv(contract.get(capability), capability)))
    return commands


def run_quality(root: Path, *, bootstrap: bool = True, dry_run: bool = False) -> None:
    commands = quality_commands(root, bootstrap=bootstrap)
    if not commands:
        print("project quality: not configured while template intake is provisional")
        return
    for capability, argv in commands:
        print(f"project quality [{capability}]: {shlex.join(argv)}", flush=True)
        if not dry_run:
            subprocess.run(argv, cwd=root, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--no-bootstrap", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    try:
        run_quality(root, bootstrap=not args.no_bootstrap, dry_run=args.dry_run)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"project quality: failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
