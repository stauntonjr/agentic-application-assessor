#!/usr/bin/env python3
"""Validate and explicitly replay executable historical failure cases."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root, run, utc_now, write_json
except ImportError:  # Direct script execution.
    from common import load_json, repository_root, run, utc_now, write_json


CHALLENGE_ID = re.compile(r"^C[0-9]{3,}$")
SOURCE_ISSUE = re.compile(r"^https://github\.com/[^/]+/[^/]+/issues/[0-9]+$")


def challenge_paths(root: Path) -> list[Path]:
    challenge_root = root / "harness/challenges"
    if challenge_root.is_symlink():
        raise ValueError("harness/challenges must not be a symlink")
    paths = [
        path for path in challenge_root.glob("C*.json") if path.name != "CHALLENGE_TEMPLATE.json"
    ]
    symlinks = [path.name for path in paths if path.is_symlink()]
    if symlinks:
        raise ValueError(f"challenge manifests must not be symlinks: {', '.join(sorted(symlinks))}")
    return sorted(paths)


def validate_challenge(data: Any, path: Path) -> list[str]:
    if not isinstance(data, dict):
        return [f"{path.name}: challenge must be an object"]
    errors: list[str] = []
    required = (
        "id",
        "title",
        "escaped_defect",
        "affected_surfaces",
        "provenance",
        "promotion",
        "oracle",
        "known_bad",
        "expected_failure",
    )
    for key in required:
        if key not in data:
            errors.append(f"{path.name}: missing {key}")
    unexpected = sorted(set(data) - set(required))
    if unexpected:
        errors.append(f"{path.name}: unexpected keys: {', '.join(unexpected)}")
    identifier = data.get("id", "")
    if not isinstance(identifier, str) or not CHALLENGE_ID.fullmatch(identifier):
        errors.append(f"{path.name}: invalid challenge id {identifier}")
    if path.stem != identifier:
        errors.append(f"{path.name}: filename must match challenge id")
    if not isinstance(data.get("title"), str) or not data.get("title", "").strip():
        errors.append(f"{path.name}: title must be a non-empty string")
    escaped = data.get("escaped_defect")
    if not isinstance(escaped, dict):
        errors.append(f"{path.name}: escaped_defect must be an object")
    else:
        if set(escaped) != {"introduced_by", "description"}:
            errors.append(f"{path.name}: escaped_defect has invalid shape")
        for key in ("introduced_by", "description"):
            if not isinstance(escaped.get(key), str) or not escaped.get(key, "").strip():
                errors.append(f"{path.name}: escaped_defect.{key} is required")
    surfaces = data.get("affected_surfaces")
    if (
        not isinstance(surfaces, list)
        or not surfaces
        or not all(isinstance(item, str) and item.strip() for item in surfaces)
        or len(surfaces) != len(set(surfaces))
    ):
        errors.append(f"{path.name}: affected_surfaces must be a unique non-empty string list")
    for command_key in ("oracle", "known_bad"):
        command = data.get(command_key)
        argv = command.get("argv") if isinstance(command, dict) else None
        if (
            not isinstance(argv, list)
            or not argv
            or not all(isinstance(item, str) for item in argv)
        ):
            errors.append(f"{path.name}: {command_key}.argv must be a non-empty string list")
        success_exit_code = command.get("success_exit_code") if isinstance(command, dict) else None
        if not isinstance(success_exit_code, int) or isinstance(success_exit_code, bool):
            errors.append(f"{path.name}: {command_key}.success_exit_code must be an integer")
        if isinstance(command, dict) and set(command) != {"argv", "success_exit_code"}:
            errors.append(f"{path.name}: {command_key} has invalid shape")
    provenance = data.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(f"{path.name}: provenance must be an object")
    else:
        if set(provenance) != {
            "source_issue",
            "source_artifact",
            "sanitized",
            "contains_raw_transcript",
        }:
            errors.append(f"{path.name}: provenance has invalid shape")
        if provenance.get("sanitized") is not True:
            errors.append(f"{path.name}: provenance.sanitized must be true")
        if provenance.get("contains_raw_transcript") is not False:
            errors.append(f"{path.name}: provenance.contains_raw_transcript must be false")
        for key in ("source_issue", "source_artifact"):
            if not isinstance(provenance.get(key), str) or not provenance.get(key, "").strip():
                errors.append(f"{path.name}: provenance.{key} is required")
        if isinstance(provenance.get("source_issue"), str) and not SOURCE_ISSUE.fullmatch(
            provenance["source_issue"]
        ):
            errors.append(f"{path.name}: provenance.source_issue must be a GitHub Issue URL")
    promotion = data.get("promotion")
    if not isinstance(promotion, dict):
        errors.append(f"{path.name}: promotion must be an object")
    else:
        if set(promotion) != {"status", "reviewed_by", "reviewed_at", "decision"}:
            errors.append(f"{path.name}: promotion has invalid shape")
        status = promotion.get("status")
        if status not in {"candidate", "approved"}:
            errors.append(f"{path.name}: promotion.status must be candidate or approved")
        reviewed_by = promotion.get("reviewed_by")
        reviewed_at = promotion.get("reviewed_at")
        decision = promotion.get("decision")
        if status == "approved":
            if (
                not isinstance(reviewed_by, str)
                or not reviewed_by.startswith("human:")
                or not reviewed_by.removeprefix("human:").strip()
            ):
                errors.append(f"{path.name}: approved challenge requires human reviewed_by")
            if not isinstance(reviewed_at, str) or not reviewed_at.strip():
                errors.append(f"{path.name}: approved challenge requires reviewed_at")
            if not isinstance(decision, str) or not decision.strip():
                errors.append(f"{path.name}: approved challenge requires decision")
        elif any(item is not None for item in (reviewed_by, reviewed_at, decision)):
            errors.append(f"{path.name}: candidate challenge cannot claim review provenance")
    expected = data.get("expected_failure")
    if not isinstance(expected, dict):
        errors.append(f"{path.name}: expected_failure must be an object")
    else:
        if set(expected) != {"exit_code", "signature"}:
            errors.append(f"{path.name}: expected_failure has invalid shape")
        exit_code = expected.get("exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            errors.append(f"{path.name}: expected_failure.exit_code must be an integer")
        if (
            not isinstance(expected.get("signature"), str)
            or not expected.get("signature", "").strip()
        ):
            errors.append(f"{path.name}: expected_failure.signature is required")
    return errors


def validate_all(root: Path) -> tuple[list[tuple[Path, dict[str, Any]]], list[str]]:
    challenges: list[tuple[Path, dict[str, Any]]] = []
    errors: list[str] = []
    try:
        paths = challenge_paths(root)
    except ValueError as exc:
        return [], [str(exc)]
    for path in paths:
        try:
            data = load_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        errors.extend(validate_challenge(data, path))
        challenges.append((path, data))
    return challenges, errors


def replay(root: Path, challenge: dict[str, Any]) -> dict[str, Any]:
    oracle = run(challenge["oracle"]["argv"], cwd=root, check=False)
    known_bad = run(challenge["known_bad"]["argv"], cwd=root, check=False)
    expected = challenge["expected_failure"]
    signature = expected.get("signature", "")
    oracle_ok = oracle.returncode == challenge["oracle"].get("success_exit_code", 0)
    known_bad_output = known_bad.stdout + known_bad.stderr
    known_bad_ok = known_bad.returncode == expected.get("exit_code", 1) and (
        not signature or signature in known_bad_output
    )
    return {
        "id": challenge["id"],
        "oracle": {
            "ok": oracle_ok,
            "exit_code": oracle.returncode,
            "stdout": oracle.stdout[-4000:],
            "stderr": oracle.stderr[-4000:],
        },
        "known_bad": {
            "ok": known_bad_ok,
            "exit_code": known_bad.returncode,
            "stdout": known_bad.stdout[-4000:],
            "stderr": known_bad.stderr[-4000:],
        },
        "ok": oracle_ok and known_bad_ok,
    }


def promote_challenge(
    root: Path,
    identifier: str,
    *,
    reviewed_by: str,
    decision: str,
) -> Path:
    if not CHALLENGE_ID.fullmatch(identifier):
        raise ValueError(f"invalid challenge id: {identifier}")
    if not reviewed_by.startswith("human:") or not reviewed_by.removeprefix("human:").strip():
        raise ValueError("challenge promotion requires --by human:IDENTITY")
    if not decision.strip():
        raise ValueError("challenge promotion decision is required")
    path = root / "harness/challenges" / f"{identifier}.json"
    data = load_json(path)
    errors = validate_challenge(data, path)
    if errors:
        raise ValueError("; ".join(errors))
    if data["promotion"]["status"] != "candidate":
        raise ValueError(f"challenge {identifier} is not a candidate")
    data["promotion"] = {
        "status": "approved",
        "reviewed_by": reviewed_by,
        "reviewed_at": utc_now(),
        "decision": decision.strip(),
    }
    write_json(path, data)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--run", action="store_true", help="Execute validated challenge commands")
    parser.add_argument(
        "--include-candidates",
        action="store_true",
        help="Replay candidates without promoting them into the retained default corpus",
    )
    parser.add_argument("--promote", metavar="CHALLENGE_ID")
    parser.add_argument("--by")
    parser.add_argument("--decision")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    if args.promote:
        if args.run or args.include_candidates:
            parser.error("--promote cannot be combined with replay options")
        if not args.by or not args.decision:
            parser.error("--promote requires --by and --decision")
        try:
            path = promote_challenge(
                root,
                args.promote,
                reviewed_by=args.by,
                decision=args.decision,
            )
        except (OSError, ValueError) as exc:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
            return 1
        print(json.dumps({"ok": True, "promoted": str(path)}, indent=2))
        return 0
    challenges, errors = validate_all(root)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    if not args.run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "validated": [data["id"] for _, data in challenges],
                    "approved": [
                        data["id"]
                        for _, data in challenges
                        if data["promotion"]["status"] == "approved"
                    ],
                    "candidates": [
                        data["id"]
                        for _, data in challenges
                        if data["promotion"]["status"] == "candidate"
                    ],
                },
                indent=2,
            )
        )
        return 0
    selected = [
        data
        for _, data in challenges
        if args.include_candidates or data["promotion"]["status"] == "approved"
    ]
    results = [replay(root, data) for data in selected]
    payload = {
        "recorded_at": utc_now(),
        "results": results,
        "candidate_replay": args.include_candidates,
        "ok": all(item["ok"] for item in results),
    }
    output = root / ".harness/challenge-results" / f"{payload['recorded_at'].replace(':', '')}.json"
    write_json(output, payload)
    print(
        json.dumps({"ok": payload["ok"], "artifact": str(output), "count": len(results)}, indent=2)
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
