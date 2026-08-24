from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest  # pyright: ignore[reportMissingImports]


@pytest.mark.integration
def test_cli_json_and_error_contract(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    (root / "README.md").write_text("# App\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True)
    context = tmp_path / "context.json"
    context.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "review": {"status": "accepted", "confirmed_on": "2026-08-24", "source": "owner"},
                "application": {
                    "name": "App",
                    "purpose": "Test the CLI.",
                    "stakeholders": ["maintainer"],
                },
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_application_assessor",
            "assess",
            str(root),
            "--context",
            str(context),
            "--format",
            "json",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert json.loads(result.stdout)["tool"]["name"] == "agentic-application-assessor"
    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_application_assessor",
            "assess",
            str(root / "missing"),
            "--context",
            str(context),
        ],
        check=False,
        text=True,
        stderr=subprocess.PIPE,
    )
    assert bad.returncode == 2
    assert bad.stderr.startswith("agentic-application-assessor:")
