from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.common import load_json, write_json
from tools.harness_check import Result, check, validate_planning
from tools.project_intake import normalize_answer, render


ROOT = Path(__file__).resolve().parents[1]


def active_generic_copy(directory: str) -> Path:
    target = Path(directory) / "active"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", ".harness", ".venv", ".coverage", "__pycache__"),
    )
    base = load_json(target / "harness/project.yaml")
    base["template_mode"] = True
    base["project"]["profile"] = "generic"
    base["engineering"]["quality"]["required_checks"] = ["format_check", "lint", "unit"]
    raw = load_json(target / "harness/fixtures/intake.answers.json")
    answers = {
        key: normalize_answer(value, source="test", recorded_at="2026-08-22T00:00:00Z")
        for key, value in raw.items()
    }
    project, planning, missing = render(
        base,
        load_json(target / ".github/planning.json"),
        answers,
        profile_root=target / "harness/profiles",
    )
    if missing:
        raise AssertionError(f"active fixture has unresolved fields: {missing}")
    write_json(target / "harness/project.yaml", project)
    write_json(target / ".github/planning.json", planning)
    return target


class HarnessCheckTests(unittest.TestCase):
    def test_adopted_validator_ignores_incompatible_application_supply_chain_module(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            tools = target / "tools"
            tools.mkdir(parents=True)
            application_module = tools / "check_actions_supply_chain.py"
            original = b"APPLICATION_OWNED = True\n"
            application_module.write_bytes(original)
            shadow_module = tools / "harness.py"
            shadow_module.write_bytes(b"raise AssertionError('application harness imported')\n")
            shutil.copy2(ROOT / "tools/github_planning.py", tools / "github_planning.py")
            readme = target / "README.md"
            readme.write_bytes(b"application readme\n")
            application_source = target / "src/application.py"
            application_source.parent.mkdir()
            application_source.write_bytes(b"VALUE = 'application'\n")
            before = {
                path.relative_to(target): path.read_bytes()
                for path in (
                    application_module,
                    shadow_module,
                    tools / "github_planning.py",
                    readme,
                    application_source,
                )
            }

            environment = os.environ.copy()
            for key in tuple(environment):
                if key.startswith("COV_CORE_"):
                    environment.pop(key)
            adopted = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/project_intake.py"),
                    "--answers",
                    str(ROOT / "harness/fixtures/intake.answers.json"),
                    "--target",
                    str(target),
                    "--mode",
                    "adopt",
                    "--apply",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )
            self.assertEqual(0, adopted.returncode, adopted.stdout + adopted.stderr)
            self.assertEqual(
                before,
                {relative: (target / relative).read_bytes() for relative in before},
            )
            self.assertTrue((target / "harness/runtime/actions_supply_chain.py").is_file())

            validated = subprocess.run(
                [sys.executable, str(target / "tools/harness_check.py"), "--json"],
                cwd=target,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )

            self.assertEqual(1, validated.returncode, validated.stdout + validated.stderr)
            self.assertEqual("", validated.stderr)
            payload = json.loads(validated.stdout)
            self.assertFalse(payload["ok"])
            self.assertIn(
                "harness project is provisional; resolve adoption gaps and essential intake context before activation",
                payload["errors"],
            )
            self.assertNotIn("Traceback", validated.stdout)
            self.assertIn(
                "`tools/check_actions_supply_chain.py`",
                (target / "docs/project/adoption-gaps.md").read_text(encoding="utf-8"),
            )

    def test_provisional_adoption_fails_with_a_precise_activation_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = active_generic_copy(directory)
            project = load_json(target / "harness/project.yaml")
            project["project"]["lifecycle"] = "adopt"
            project["project"]["status"] = "provisional"
            write_json(target / "harness/project.yaml", project)

            result = check(target)

            self.assertFalse(result.ok)
            self.assertIn(
                "harness project is provisional; resolve adoption gaps and essential intake context before activation",
                result.errors,
            )

    def test_project_owned_planning_loader_is_supported_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            planning = root / ".github/planning.json"
            planning.parent.mkdir(parents=True)
            planning.write_text('{"projects": []}\n', encoding="utf-8")

            result = Result()
            with (
                patch("tools.harness_check.validate_planning_contract", None),
                patch(
                    "tools.harness_check.load_project_planning_contract",
                    side_effect=lambda path: {"loaded": path.name},
                ),
            ):
                validate_planning(root, result)
            self.assertTrue(result.ok)
            self.assertIn("project-owned validator", result.warnings[0])

            rejected = Result()
            with (
                patch("tools.harness_check.validate_planning_contract", None),
                patch(
                    "tools.harness_check.load_project_planning_contract",
                    side_effect=ValueError("invalid application topology"),
                ),
            ):
                validate_planning(root, rejected)
            self.assertFalse(rejected.ok)
            self.assertIn("invalid application topology", rejected.errors[0])

    def test_template_is_valid(self) -> None:
        result = check(ROOT)
        self.assertTrue(result.ok, result.errors)
        self.assertIn("7 skills", result.checked)
        self.assertIn("2 provider adapters", result.checked)
        self.assertIn("Pi adapter", result.checked)

    def test_recovery_fixture_rejects_raw_transcript_retention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "invalid-recovery"
            shutil.copytree(
                ROOT,
                target,
                ignore=shutil.ignore_patterns(
                    ".git", ".harness", ".venv", ".coverage", "__pycache__"
                ),
            )
            fixture = load_json(target / "harness/recovery/R001.json")
            fixture["source"]["contains_raw_transcript"] = True
            write_json(target / "harness/recovery/R001.json", fixture)

            result = check(target)

            self.assertFalse(result.ok)
            self.assertTrue(
                any(
                    "source.contains_raw_transcript must be false" in error
                    for error in result.errors
                )
            )

    def test_planning_topology_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "invalid-planning"
            shutil.copytree(
                ROOT,
                target,
                ignore=shutil.ignore_patterns(
                    ".git", ".harness", ".venv", ".coverage", "__pycache__"
                ),
            )
            planning = load_json(target / ".github/planning.json")
            planning["project"]["topology"] = "shared"
            planning["project"]["number"] = None
            write_json(target / ".github/planning.json", planning)
            result = check(target)
            self.assertFalse(result.ok)
            self.assertTrue(
                any(
                    "shared project topology requires a project number" in error
                    for error in result.errors
                )
            )

    def test_pi_adapter_remains_thin_and_provider_neutral(self) -> None:
        settings = json.loads((ROOT / ".pi/settings.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "harness/adapters/pi.json").read_text(encoding="utf-8"))

        self.assertNotIn("packages", settings)
        self.assertNotIn("defaultModel", settings)
        self.assertEqual(["extensions/context-readiness.ts"], settings["extensions"])
        self.assertEqual("experimental", manifest["status"])
        self.assertEqual(
            "not supplied by Pi core adapter", manifest["capabilities"]["role_delegation"]
        )
        self.assertEqual(
            ".agents/skills",
            next(item for item in manifest["mappings"] if item["contract"] == "skills")[
                "canonical"
            ],
        )

    def test_active_contract_rejects_empty_exception_noop_and_symlink_lock(self) -> None:
        mutations = ("empty-exception", "noop", "symlink-lock")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                target = active_generic_copy(directory)
                project = load_json(target / "harness/project.yaml")
                if mutation == "empty-exception":
                    project["engineering"]["quality"]["dependency_lock"] = "not-applicable:"
                elif mutation == "noop":
                    project["engineering"]["command_contract"]["unit"] = "true"
                else:
                    lock = target / "locks/dependency.lock"
                    lock.parent.mkdir()
                    lock.symlink_to("/etc/hosts")
                    project["engineering"]["quality"]["dependency_lock"] = "locks/dependency.lock"
                write_json(target / "harness/project.yaml", project)
                result = check(target)
                self.assertFalse(result.ok)
                if mutation == "empty-exception":
                    self.assertTrue(any("requires a reason" in item for item in result.errors))
                elif mutation == "noop":
                    self.assertTrue(any("successful no-op" in item for item in result.errors))
                else:
                    self.assertTrue(any("symlink" in item for item in result.errors))


if __name__ == "__main__":
    unittest.main()
