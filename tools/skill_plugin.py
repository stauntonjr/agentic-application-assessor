#!/usr/bin/env python3
"""Build and verify the installable Codex skill plugin from canonical skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root, write_json
except ImportError:  # Direct script execution.
    from common import load_json, repository_root, write_json


PLUGIN_NAME = "agentic-engineering-harness"
SOURCE_RELATIVE = Path(".agents/skills")
PLUGIN_RELATIVE = Path("plugins") / PLUGIN_NAME
SKILLS_RELATIVE = PLUGIN_RELATIVE / "skills"
MANIFEST_RELATIVE = PLUGIN_RELATIVE / ".codex-plugin/plugin.json"
PROVENANCE_RELATIVE = PLUGIN_RELATIVE / "PROVENANCE.json"
LICENSE_RELATIVE = PLUGIN_RELATIVE / "LICENSE"
MARKETPLACE_RELATIVE = Path(".agents/plugins/marketplace.json")
EXCLUDED_POLICY = (
    "AGENTS.md",
    ".codex/",
    ".github/",
    ".pi/",
    "docs/",
    "harness/",
)
PROBE_BINARY = "/tmp/agentic-harness-codex-probe"
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular_files(root: Path) -> dict[str, Path]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"expected an ordinary directory: {root}")
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"refusing symlink in skill tree: {relative}")
        if path.is_file():
            files[relative] = path
    return files


def plugin_manifest(root: Path) -> dict[str, Any]:
    manifest = load_json(root / MANIFEST_RELATIVE)
    if not isinstance(manifest, dict):
        raise ValueError("plugin manifest must be an object")
    errors: list[str] = []
    if manifest.get("name") != PLUGIN_NAME:
        errors.append(f"plugin manifest name must be {PLUGIN_NAME}")
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("plugin manifest version must be strict SemVer")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        errors.append("plugin manifest description is required")
    author = manifest.get("author")
    if (
        not isinstance(author, dict)
        or not isinstance(author.get("name"), str)
        or not author["name"].strip()
    ):
        errors.append("plugin manifest author.name is required")
    if manifest.get("repository") != "https://github.com/stauntonjr/agentic-project-template":
        errors.append("plugin manifest repository is invalid")
    if manifest.get("license") != "MIT":
        errors.append("plugin manifest license must be MIT")
    if manifest.get("skills") != "./skills/":
        errors.append("plugin manifest must expose ./skills/")
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        errors.append("plugin manifest interface is required")
    else:
        prompts = interface.get("defaultPrompt")
        if (
            not isinstance(prompts, list)
            or not 1 <= len(prompts) <= 3
            or not all(isinstance(item, str) and 1 <= len(item) <= 128 for item in prompts)
        ):
            errors.append("plugin defaultPrompt must contain one to three strings of 1-128 chars")
    if errors:
        raise ValueError("; ".join(errors))
    return manifest


def distribution_bytes(path: Path, skill_names: list[str]) -> tuple[bytes, str]:
    source = path.read_bytes()
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"skill distribution supports UTF-8 text only: {path}") from exc
    transformed = text
    for name in sorted(skill_names, key=len, reverse=True):
        transformed = re.sub(
            rf"\${re.escape(name)}(?![a-z0-9-])",
            f"${PLUGIN_NAME}:{name}",
            transformed,
        )
    encoded = transformed.encode("utf-8")
    return encoded, "namespace-skill-references" if encoded != source else "identity"


def expected_provenance(root: Path) -> dict[str, Any]:
    manifest = plugin_manifest(root)
    source = regular_files(root / SOURCE_RELATIVE)
    skill_names = sorted(path.name for path in (root / SOURCE_RELATIVE).iterdir() if path.is_dir())
    files: dict[str, Any] = {}
    for relative, path in source.items():
        distributed, transformation = distribution_bytes(path, skill_names)
        files[relative] = {
            "source_sha256": sha256(path),
            "distribution_sha256": hashlib.sha256(distributed).hexdigest(),
            "transformation": transformation,
        }
    return {
        "schema_version": "1.0",
        "plugin": {"name": PLUGIN_NAME, "version": manifest["version"]},
        "manifest": {
            "path": MANIFEST_RELATIVE.as_posix(),
            "sha256": sha256(root / MANIFEST_RELATIVE),
        },
        "source": {
            "repository": "https://github.com/stauntonjr/agentic-project-template",
            "root": SOURCE_RELATIVE.as_posix(),
            "authority": "canonical-editable-source",
        },
        "distribution": {
            "root": SKILLS_RELATIVE.as_posix(),
            "authority": "generated-mirror-do-not-edit",
        },
        "license": {"source": "LICENSE", "sha256": sha256(root / "LICENSE")},
        "excluded_project_policy": list(EXCLUDED_POLICY),
        "files": files,
    }


def validate_marketplace(root: Path) -> list[str]:
    errors: list[str] = []
    marketplace = load_json(root / MARKETPLACE_RELATIVE)
    if not isinstance(marketplace, dict):
        return ["marketplace must be an object"]
    if marketplace.get("name") != "agentic-project-template":
        errors.append("marketplace name must be agentic-project-template")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        return errors + ["marketplace plugins must be an array"]
    matches = [
        item
        for item in plugins
        if isinstance(item, dict) and item.get("name") == PLUGIN_NAME
    ]
    if len(matches) != 1:
        errors.append("marketplace must contain exactly one plugin entry")
        return errors
    entry = matches[0]
    if entry.get("source") != {
        "source": "local",
        "path": f"./plugins/{PLUGIN_NAME}",
    }:
        errors.append("marketplace plugin source must use the repository-local plugin path")
    if entry.get("policy") != {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }:
        errors.append("marketplace plugin policy must be explicit and installable")
    if entry.get("category") != "Developer Tools":
        errors.append("marketplace plugin category must be Developer Tools")
    return errors


def check(root: Path) -> list[str]:
    errors = validate_marketplace(root)
    expected = expected_provenance(root)
    source = regular_files(root / SOURCE_RELATIVE)
    packaged = regular_files(root / SKILLS_RELATIVE)
    skill_names = sorted(path.name for path in (root / SOURCE_RELATIVE).iterdir() if path.is_dir())
    if set(source) != set(packaged):
        missing = sorted(set(source) - set(packaged))
        extra = sorted(set(packaged) - set(source))
        if missing:
            errors.append("plugin mirror missing: " + ", ".join(missing))
        if extra:
            errors.append("plugin mirror has extra files: " + ", ".join(extra))
    for relative in sorted(set(source) & set(packaged)):
        expected_bytes, _ = distribution_bytes(source[relative], skill_names)
        if expected_bytes != packaged[relative].read_bytes():
            errors.append(f"plugin mirror differs from generated skill: {relative}")
    license_path = root / LICENSE_RELATIVE
    if (
        not license_path.is_file()
        or license_path.is_symlink()
        or license_path.read_bytes() != (root / "LICENSE").read_bytes()
    ):
        errors.append("plugin LICENSE must match the repository MIT license")
    provenance_path = root / PROVENANCE_RELATIVE
    if not provenance_path.is_file() or provenance_path.is_symlink():
        errors.append(f"missing provenance: {PROVENANCE_RELATIVE.as_posix()}")
    else:
        actual = load_json(provenance_path)
        if actual != expected:
            errors.append("plugin provenance is stale or does not match canonical skills")
    return errors


def sync(root: Path) -> None:
    source_root = root / SOURCE_RELATIVE
    target_root = root / SKILLS_RELATIVE
    plugin_root = root / PLUGIN_RELATIVE
    provenance_path = root / PROVENANCE_RELATIVE
    license_path = root / LICENSE_RELATIVE
    if (
        plugin_root.is_symlink()
        or target_root.is_symlink()
        or provenance_path.is_symlink()
        or license_path.is_symlink()
    ):
        raise ValueError("refusing to replace a symlinked plugin path")
    if not (root / "LICENSE").is_file() or (root / "LICENSE").is_symlink():
        raise ValueError("repository LICENSE must be an ordinary file")
    expected = expected_provenance(root)
    plugin_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="skill-plugin-", dir=plugin_root) as temporary:
        staged = Path(temporary) / "skills"
        shutil.copytree(source_root, staged, symlinks=False)
        source_files = regular_files(source_root)
        skill_names = sorted(path.name for path in source_root.iterdir() if path.is_dir())
        for relative, source_path in source_files.items():
            distributed, _ = distribution_bytes(source_path, skill_names)
            (staged / relative).write_bytes(distributed)
        regular_files(staged)
        if target_root.exists():
            if not target_root.is_dir():
                raise ValueError(f"plugin skills target is not a directory: {target_root}")
            shutil.rmtree(target_root)
        os.replace(staged, target_root)
    write_json(root / PROVENANCE_RELATIVE, expected)
    shutil.copy2(root / "LICENSE", root / LICENSE_RELATIVE)


def _run_json(command: list[str], *, timeout: int = 30) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"command failed ({completed.returncode}): {detail}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("command did not return JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("command JSON response must be an object")
    return payload


def _app_server_results(
    command: list[str], requests: list[tuple[int, str, dict[str, Any]]]
) -> dict[int, dict[str, Any]]:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        raise RuntimeError("failed to open Codex app-server pipes")

    def send(payload: dict[str, Any]) -> None:
        process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        process.stdin.flush()

    messages: queue.Queue[dict[str, Any] | Exception] = queue.Queue()

    def read_messages() -> None:
        try:
            for line in process.stdout:
                messages.put(json.loads(line))
        except Exception as exc:  # Propagate reader failures to the caller.
            messages.put(exc)
        finally:
            messages.put(RuntimeError("Codex app-server stdout closed"))

    reader = threading.Thread(target=read_messages, daemon=True)
    reader.start()

    def receive(request_id: int, timeout: int = 45) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                payload = messages.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if isinstance(payload, Exception):
                raise RuntimeError("failed to read Codex app-server output") from payload
            if not isinstance(payload, dict):
                raise RuntimeError("Codex app-server message must be an object")
            if payload.get("id") == request_id:
                if "error" in payload:
                    raise RuntimeError(f"Codex app-server error: {payload['error']}")
                result = payload.get("result", {})
                if not isinstance(result, dict):
                    raise RuntimeError("Codex app-server result must be an object")
                return result
        process.kill()
        detail = process.stderr.read().strip()
        raise RuntimeError(f"timed out waiting for Codex app-server: {detail}")

    results: dict[int, dict[str, Any]] = {}
    try:
        send(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "skill-plugin-probe", "version": "1.0"},
                    "capabilities": {"experimentalApi": True},
                },
            }
        )
        receive(1)
        send({"method": "initialized"})
        for request_id, method, params in requests:
            send({"id": request_id, "method": method, "params": params})
            results[request_id] = receive(request_id)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    return results


def runtime_probe(root: Path, codex: Path) -> dict[str, Any]:
    """Exercise local install, namespaced discovery, collision, and uninstall."""
    if shutil.which("bwrap") is None:
        raise RuntimeError("runtime probe requires Bubblewrap (bwrap)")
    codex = codex.resolve(strict=True)
    user_home = Path.home()
    source_names = sorted(path.name for path in (root / SOURCE_RELATIVE).iterdir() if path.is_dir())
    expected_plugin_names = [f"{PLUGIN_NAME}:{name}" for name in source_names]
    with tempfile.TemporaryDirectory(prefix="skill-plugin-runtime-", dir="/tmp") as temporary:
        probe_root = Path(temporary)
        codex_home = probe_root / "codex-home"
        agents_home = probe_root / "agents-home"
        clean = probe_root / "clean"
        collision = probe_root / "collision"
        for path in (codex_home, agents_home, clean, collision):
            path.mkdir()
        local_skill = collision / ".agents/skills/loop-report"
        local_skill.mkdir(parents=True)
        local_skill.joinpath("SKILL.md").write_text(
            "---\n"
            "name: loop-report\n"
            "description: Repository collision marker proving repo-local and plugin skills "
            "remain distinct.\n"
            "---\n\n"
            "# Repository collision marker\n",
            encoding="utf-8",
        )
        prefix = [
            "bwrap",
            "--bind",
            "/",
            "/",
            "--bind",
            str(codex_home),
            str(user_home / ".codex"),
            "--bind",
            str(agents_home),
            str(user_home / ".agents"),
            "--ro-bind",
            str(codex),
            PROBE_BINARY,
            "--",
            PROBE_BINARY,
        ]
        marketplace_add = _run_json(
            prefix + ["plugin", "marketplace", "add", str(root), "--json"]
        )
        installed = _run_json(
            prefix + ["plugin", "add", f"{PLUGIN_NAME}@agentic-project-template", "--json"]
        )
        marketplace_path = root / MARKETPLACE_RELATIVE
        api = _app_server_results(
            prefix + ["app-server", "--stdio"],
            [
                (
                    2,
                    "plugin/read",
                    {"pluginName": PLUGIN_NAME, "marketplacePath": str(marketplace_path)},
                ),
                (
                    3,
                    "skills/list",
                    {"cwds": [str(clean), str(collision)], "forceReload": True},
                ),
            ],
        )
        plugin = api[2].get("plugin", {})
        if not isinstance(plugin, dict):
            raise RuntimeError("Codex plugin/read response is malformed")
        skill_records = plugin.get("skills", [])
        if not isinstance(skill_records, list):
            raise RuntimeError("Codex plugin/read skills must be an array")
        actual_plugin_names = sorted(
            item.get("name") for item in skill_records if isinstance(item, dict)
        )
        if actual_plugin_names != expected_plugin_names:
            raise RuntimeError(
                "installed plugin skill namespace mismatch: "
                f"expected {expected_plugin_names}, got {actual_plugin_names}"
            )
        if any(
            not isinstance(item.get("interface"), dict)
            or f"${PLUGIN_NAME}:" not in str(item["interface"].get("defaultPrompt", ""))
            for item in skill_records
            if isinstance(item, dict)
        ):
            raise RuntimeError("installed plugin exposed an unqualified skill starter prompt")
        entries = api[3].get("data", [])
        if not isinstance(entries, list):
            raise RuntimeError("Codex skills/list data must be an array")
        by_cwd = {item.get("cwd"): item for item in entries if isinstance(item, dict)}
        clean_skills = by_cwd.get(str(clean), {}).get("skills", [])
        collision_skills = by_cwd.get(str(collision), {}).get("skills", [])
        if not isinstance(clean_skills, list) or not isinstance(collision_skills, list):
            raise RuntimeError("Codex skills/list entry skills must be arrays")
        clean_plugin_names = sorted(
            item.get("name")
            for item in clean_skills
            if str(item.get("name", "")).startswith(f"{PLUGIN_NAME}:")
        )
        collision_plugin_names = sorted(
            item.get("name")
            for item in collision_skills
            if str(item.get("name", "")).startswith(f"{PLUGIN_NAME}:")
        )
        if clean_plugin_names != expected_plugin_names:
            raise RuntimeError("activated plugin skills were not exposed in the clean repository")
        if collision_plugin_names != expected_plugin_names:
            raise RuntimeError("activated plugin skills were not preserved beside the collision")
        if any(item.get("name") in source_names for item in clean_skills):
            raise RuntimeError("plugin exposed an unnamespaced skill in the clean repository")
        local_matches = [
            item
            for item in collision_skills
            if item.get("name") == "loop-report" and item.get("scope") == "repo"
        ]
        if len(local_matches) != 1 or "collision marker" not in local_matches[0].get(
            "description", ""
        ):
            raise RuntimeError("repository-local collision skill was not preserved")
        removed = _run_json(
            prefix + ["plugin", "remove", f"{PLUGIN_NAME}@agentic-project-template", "--json"]
        )
        after_remove = _run_json(prefix + ["plugin", "list", "--json"])
        if after_remove.get("installed"):
            raise RuntimeError("plugin remained installed after removal")
        marketplace_removed = _run_json(
            prefix
            + ["plugin", "marketplace", "remove", "agentic-project-template", "--json"]
        )
        return {
            "ok": True,
            "codex": subprocess.run(
                prefix + ["--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip(),
            "marketplace": marketplace_add.get("marketplaceName"),
            "plugin": installed.get("pluginId"),
            "version": installed.get("version"),
            "plugin_skill_count": len(actual_plugin_names),
            "plugin_skill_names": actual_plugin_names,
            "collision": {
                "repository_name": local_matches[0]["name"],
                "repository_scope": local_matches[0]["scope"],
                "plugin_name": f"{PLUGIN_NAME}:loop-report",
                "behavior": "separate-namespaces",
            },
            "uninstalled": removed.get("pluginId") == installed.get("pluginId"),
            "marketplace_removed": marketplace_removed.get("marketplaceName")
            == marketplace_add.get("marketplaceName"),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check")
    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--yes", action="store_true")
    probe_parser = subparsers.add_parser("probe")
    probe_parser.add_argument("--codex", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    try:
        if args.command == "sync":
            if not args.yes:
                raise ValueError("sync requires --yes because it replaces the generated mirror")
            sync(root)
        if args.command == "probe":
            errors = check(root)
            if errors:
                raise ValueError("; ".join(errors))
            print(json.dumps(runtime_probe(root, args.codex), indent=2))
            return 0
        errors = check(root)
    except (
        OSError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        errors = [str(exc)]
    payload = {
        "ok": not errors,
        "plugin": PLUGIN_NAME,
        "root": str(root),
        "errors": errors,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
