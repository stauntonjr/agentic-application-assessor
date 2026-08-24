#!/usr/bin/env python3
"""Build and clean-install a Python wheel without resolving dependencies."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import tomllib
import venv
from pathlib import Path

try:
    from .common import repository_root
except ImportError:  # Direct script execution.
    from common import repository_root


def main() -> int:
    root = repository_root(Path(__file__).parent)
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    name = project["name"]
    expected_version = project.get("version")
    if not expected_version:
        raise ValueError("python package smoke requires project.version in pyproject.toml")

    with tempfile.TemporaryDirectory() as directory:
        boundary = Path(directory)
        dist = boundary / "dist"
        subprocess.run(["uv", "build", "--out-dir", str(dist)], cwd=root, check=True)
        wheels = sorted(dist.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel, found {len(wheels)}")
        environment = boundary / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheels[0])],
            check=True,
        )
        installed = subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.metadata as m,sys; print(m.version(sys.argv[1]))",
                name,
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
    if installed != expected_version:
        raise RuntimeError(f"installed version {installed} does not match {expected_version}")
    print(f"Python package smoke: ok ({name} {installed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
