#!/usr/bin/env python3
"""Build, clean-install, and execute the product CLI in a disposable repository."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import venv


ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE)


def main() -> int:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    if project.get("dependencies") != []:
        raise RuntimeError("runtime dependency set differs from the reviewed empty set")
    with tempfile.TemporaryDirectory() as directory:
        boundary = Path(directory)
        dist = boundary / "dist"
        run("uv", "build", "--offline", "--out-dir", str(dist), cwd=ROOT)
        wheels = sorted(dist.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel, found {len(wheels)}")
        environment = boundary / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        executable_root = environment / ("Scripts" if sys.platform == "win32" else "bin")
        python = executable_root / ("python.exe" if sys.platform == "win32" else "python")
        cli = executable_root / (
            "agentic-application-assessor.exe"
            if sys.platform == "win32"
            else "agentic-application-assessor"
        )
        run("uv", "pip", "install", "--offline", "--python", str(python), str(wheels[0]))
        target = boundary / "target"
        target.mkdir()
        run("git", "init", "-b", "main", cwd=target)
        run("git", "config", "user.name", "Package Smoke", cwd=target)
        run("git", "config", "user.email", "smoke@example.invalid", cwd=target)
        (target / "README.md").write_text("# Package smoke target\n", encoding="utf-8")
        run("git", "add", ".", cwd=target)
        run("git", "commit", "-m", "fixture", cwd=target)
        context = boundary / "context.json"
        context.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "review": {
                        "status": "accepted",
                        "confirmed_on": "2026-08-24",
                        "source": "package smoke",
                    },
                    "application": {
                        "name": "Fixture",
                        "purpose": "Exercise the installed wheel.",
                        "stakeholders": ["maintainer"],
                    },
                }
            ),
            encoding="utf-8",
        )
        installed_version = run(str(cli), "--version").stdout.strip()
        rendered = run(
            str(cli),
            "assess",
            str(target),
            "--context",
            str(context),
            "--format",
            "json",
        ).stdout
        report = json.loads(rendered)
        if run("git", "status", "--porcelain=v1", cwd=target).stdout:
            raise RuntimeError("installed assessment changed the target repository")
    if installed_version != f"agentic-application-assessor {version}":
        raise RuntimeError(f"unexpected installed version: {installed_version}")
    if report["tool"]["version"] != version:
        raise RuntimeError("installed report version differs from package version")
    print(f"Agentic Application Assessor package smoke: ok ({version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
