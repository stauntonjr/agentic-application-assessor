#!/usr/bin/env python3
"""Validate reusable harness scenarios and emit isolated forward-test prompts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root
except ImportError:  # Direct script execution.
    from common import load_json, repository_root


SCENARIO_ID = re.compile(r"^E[0-9]{3,}-[a-z0-9-]+$")


def validate_scenarios(root: Path, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        return ["scenarios must be a list"]
    seen: set[str] = set()
    for scenario in scenarios:
        identifier = scenario.get("id", "")
        if not SCENARIO_ID.fullmatch(identifier):
            errors.append(f"invalid scenario id: {identifier}")
        if identifier in seen:
            errors.append(f"duplicate scenario id: {identifier}")
        seen.add(identifier)
        for key in ("prompt", "required_behaviors", "forbidden_behaviors"):
            if not scenario.get(key):
                errors.append(f"{identifier}: missing {key}")
        skill = scenario.get("expected_primary_skill")
        if skill is not None and not (root / ".agents/skills" / skill / "SKILL.md").is_file():
            errors.append(f"{identifier}: unknown expected skill {skill}")
    return errors


def forward_prompts(root: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": scenario["id"],
            "prompt": scenario["prompt"],
            "skill_path": (
                str(root / ".agents/skills" / scenario["expected_primary_skill"])
                if scenario.get("expected_primary_skill")
                else None
            ),
            "score_after_run": {
                "required_behaviors": scenario["required_behaviors"],
                "forbidden_behaviors": scenario["forbidden_behaviors"],
            },
        }
        for scenario in payload["scenarios"]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--emit-prompts", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    try:
        payload = load_json(root / "harness/evals/scenarios.json")
        errors = validate_scenarios(root, payload)
    except (ValueError, OSError) as exc:
        errors = [str(exc)]
        payload = {"scenarios": []}
    result = {
        "ok": not errors,
        "scenario_count": len(payload.get("scenarios", [])),
        "errors": errors,
        "note": "This validator does not claim model behavior; use emitted prompts in isolated agent runs.",
    }
    if args.emit_prompts and not errors:
        result["forward_test_prompts"] = forward_prompts(root, payload)
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
