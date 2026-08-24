import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.common import load_json
from tools.project_intake import (
    adoption_output_paths,
    adoption_quality_evidence,
    copy_missing_for_adoption,
    copy_template,
    mark_adoption_state,
    normalize_answer,
    not_evaluated_quality,
    render,
)

ROOT = Path(__file__).resolve().parents[1]


def subprocess_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith("COV_CORE_"):
            environment.pop(key)
    return environment


def template_project() -> dict:
    project = load_json(ROOT / "harness/project.yaml")
    project["template_mode"] = True
    project["project"]["profile"] = "generic"
    project["engineering"]["command_contract"] = {
        "primary_check": "make smoke",
        "bootstrap": "TBD",
        "format_check": "TBD",
        "lint": "TBD",
        "typecheck": "TBD",
        "unit": "python3 -m unittest discover -s tests -v",
        "integration": "TBD",
        "package_smoke": "TBD",
    }
    project["engineering"]["quality"] = {
        "dependency_lock": "required-if-dependencies",
        "coverage_policy": "ratchet-or-explicit-exception",
        "required_checks": ["format_check", "lint", "unit"],
        "property_testing": "profile-selected",
    }
    project["engineering"]["versioning"].update(
        {"strategy": "TBD", "current": "TBD", "public_contract": [], "source": "TBD"}
    )
    return project


class ProjectIntakeTests(unittest.TestCase):
    def test_adoption_with_missing_context_stays_provisional_without_file_gaps(self) -> None:
        project = template_project()
        project["open_questions"] = ["Resolve intent.outcomes"]
        intake = {"missing_essential_fields": ["intent.outcomes"]}
        dispositions = {
            "copied": [],
            "upstream_collisions": [],
            "adoption_deferred": [],
            "merge_required_existing": [],
            "merge_required_missing": [],
        }

        unresolved = mark_adoption_state(project, intake, dispositions)

        self.assertEqual(0, unresolved)
        self.assertEqual("adopt", project["project"]["lifecycle"])
        self.assertEqual("provisional", project["project"]["status"])
        self.assertEqual("provisional", intake["context_readiness"])
        self.assertEqual("provisional", intake["adoption"]["status"])
        self.assertEqual("complete", intake["adoption"]["reconciliation_status"])

    def test_adoption_becomes_active_only_when_context_and_file_gaps_are_resolved(self) -> None:
        project = template_project()
        project["open_questions"] = []
        intake = {"missing_essential_fields": []}
        dispositions = {
            "copied": [],
            "upstream_collisions": [],
            "adoption_deferred": [],
            "merge_required_existing": [],
            "merge_required_missing": [],
        }

        mark_adoption_state(project, intake, dispositions)

        self.assertEqual("active", project["project"]["status"])
        self.assertEqual("sufficient", intake["context_readiness"])
        self.assertEqual("active", intake["adoption"]["status"])
        self.assertEqual("complete", intake["adoption"]["reconciliation_status"])

    def test_unevaluated_quality_keeps_zero_gap_adoption_provisional(self) -> None:
        project = template_project()
        project["open_questions"] = []
        intake = {"missing_essential_fields": []}
        dispositions = {
            "copied": ["tools/loop.py"],
            "upstream_collisions": [],
            "adoption_deferred": [],
            "merge_required_existing": [],
            "merge_required_missing": [],
        }

        mark_adoption_state(
            project,
            intake,
            dispositions,
            not_evaluated_quality(),
        )

        self.assertEqual("provisional", project["project"]["status"])
        self.assertEqual("sufficient", intake["context_readiness"])
        self.assertEqual(0, intake["adoption"]["gap_count"])
        self.assertEqual("provisional", intake["adoption"]["reconciliation_status"])
        self.assertEqual("not-evaluated", intake["adoption"]["quality"]["status"])
        self.assertIn("authoritative quality command", project["open_questions"][-1])

    def test_failing_baseline_is_indeterminate_not_an_adoption_regression(self) -> None:
        evidence = adoption_quality_evidence(
            "make check",
            ["tools/loop.py"],
            {"exit_code": 1, "output": "existing failure", "error": None},
            {"exit_code": 1, "output": "tools/loop.py", "error": None},
        )

        self.assertEqual("indeterminate", evidence["status"])
        self.assertEqual(1, evidence["baseline_exit_code"])
        self.assertEqual(1, evidence["adopted_exit_code"])
        self.assertIn("did not pass before", evidence["diagnostic"])

    def test_procurement_quality_fixture_pins_the_conformance_boundary(self) -> None:
        fixture = load_json(ROOT / "harness/fixtures/procurement-quality-discovery.json")

        self.assertEqual("make check", fixture["application"]["authoritative_check"])
        self.assertEqual("0.16.3", fixture["tool"]["version"])
        self.assertEqual(26, fixture["before"]["lint_error_count"])
        self.assertEqual(
            {
                "harness/runtime/actions_supply_chain.py",
                "tools/common.py",
                "tools/evaluate_harness.py",
                "tools/harness_check.py",
                "tools/harness_upgrade.py",
                "tools/loop.py",
                "tools/pi_adapter_check.py",
                "tools/pi_tool_probe.py",
                "tools/product_version.py",
                "tools/project_intake.py",
                "tools/python_package_smoke.py",
                "tools/run_quality.py",
            },
            set(fixture["before"]["lint_incompatible_paths"]),
        )
        self.assertTrue(
            all(value is False for value in fixture["boundary"].values() if isinstance(value, bool))
        )

    def test_python_profile_overrides_template_placeholders(self) -> None:
        answers = {
            "project.profile": normalize_answer(
                "python-data", source="test", recorded_at="2026-08-22T00:00:00Z"
            )
        }
        project, _, _ = render(
            template_project(),
            load_json(ROOT / ".github/planning.json"),
            answers,
            profile_root=ROOT / "harness/profiles",
        )
        self.assertEqual("uv run pytest", project["engineering"]["test_commands"][0])
        self.assertEqual("uv.lock", project["engineering"]["quality"]["dependency_lock"])
        self.assertEqual("hypothesis", project["engineering"]["quality"]["property_testing"])
        self.assertIn("pytest", project["engineering"]["command_contract"]["unit"])

    def test_no_version_strategy_does_not_require_artificial_version_fields(self) -> None:
        raw = load_json(ROOT / "harness/fixtures/intake.answers.json")
        raw["engineering.versioning.strategy"] = "none"
        for field in (
            "engineering.versioning.current",
            "engineering.versioning.public_contract",
            "engineering.versioning.source",
        ):
            raw.pop(field)
        answers = {
            key: normalize_answer(value, source="test", recorded_at="2026-08-22T00:00:00Z")
            for key, value in raw.items()
        }
        project, _, missing = render(
            template_project(),
            load_json(ROOT / ".github/planning.json"),
            answers,
            profile_root=ROOT / "harness/profiles",
        )
        self.assertEqual([], missing)
        self.assertFalse(project["template_mode"])
        self.assertEqual("none", project["engineering"]["versioning"]["strategy"])
        self.assertEqual("not-applicable", project["engineering"]["versioning"]["current"])
        self.assertEqual("not-applicable", project["engineering"]["versioning"]["source"])

    def test_profile_id_cannot_escape_profile_directory(self) -> None:
        answers = {
            "project.profile": normalize_answer(
                "../../outside", source="test", recorded_at="2026-08-22T00:00:00Z"
            )
        }
        with self.assertRaisesRegex(ValueError, "invalid project profile ID"):
            render(
                template_project(),
                load_json(ROOT / ".github/planning.json"),
                answers,
                profile_root=ROOT / "harness/profiles",
            )

    def test_unknown_profile_cannot_report_context_ready(self) -> None:
        answers = {
            "project.profile": normalize_answer(
                "missing-profile", source="test", recorded_at="2026-08-22T00:00:00Z"
            )
        }
        with self.assertRaisesRegex(ValueError, "unknown project profile"):
            render(
                template_project(),
                load_json(ROOT / ".github/planning.json"),
                answers,
                profile_root=ROOT / "harness/profiles",
            )

    def test_copy_excludes_generated_dependency_trees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            target = Path(directory) / "target"
            source.mkdir()
            (source / "keep.txt").write_text("source\n", encoding="utf-8")
            (source / ".venv/lib").mkdir(parents=True)
            (source / ".venv/lib/dependency.py").write_text("generated\n", encoding="utf-8")
            (source / "node_modules/package").mkdir(parents=True)
            (source / "node_modules/package/index.js").write_text("generated\n", encoding="utf-8")
            copy_template(source, target)
            self.assertTrue((target / "keep.txt").is_file())
            self.assertFalse((target / ".venv").exists())
            self.assertFalse((target / "node_modules").exists())

    def test_unresolved_command_capability_keeps_intake_provisional(self) -> None:
        raw = load_json(ROOT / "harness/fixtures/intake.answers.json")
        raw.pop("engineering.command_contract.typecheck")
        answers = {
            key: normalize_answer(value, source="test", recorded_at="2026-08-22T00:00:00Z")
            for key, value in raw.items()
        }
        project, _, missing = render(
            template_project(),
            load_json(ROOT / ".github/planning.json"),
            answers,
            profile_root=ROOT / "harness/profiles",
        )
        self.assertTrue(project["template_mode"])
        self.assertIn("engineering.command_contract.typecheck", missing)

    def test_fixture_resolves_essential_context(self) -> None:
        raw = load_json(ROOT / "harness/fixtures/intake.answers.json")
        answers = {
            key: normalize_answer(value, source="test", recorded_at="2026-08-21T00:00:00Z")
            for key, value in raw.items()
        }
        project, planning, missing = render(
            template_project(),
            load_json(ROOT / ".github/planning.json"),
            answers,
            profile_root=ROOT / "harness/profiles",
        )
        self.assertEqual([], missing)
        self.assertFalse(project["template_mode"])
        self.assertEqual("Example Agent Project", project["project"]["name"])
        self.assertEqual("semver", project["engineering"]["versioning"]["strategy"])
        self.assertEqual("0.1.0", project["engineering"]["versioning"]["current"])
        self.assertEqual(
            ["CLI", "configuration schema"],
            project["engineering"]["versioning"]["public_contract"],
        )
        self.assertEqual("make smoke", project["engineering"]["command_contract"]["primary_check"])
        self.assertEqual("example/example-agent-project", planning["repository"])
        self.assertEqual("example", planning["project"]["owner"])
        self.assertEqual("dedicated", planning["project"]["topology"])
        self.assertIsNone(planning["project"]["number"])
        self.assertEqual("copy", planning["project"]["bootstrap"]["method"])
        self.assertEqual("stauntonjr", planning["project"]["bootstrap"]["source_owner"])
        self.assertEqual(13, planning["project"]["bootstrap"]["source_number"])

    def test_cli_creates_a_valid_derived_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "derived"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/project_intake.py"),
                    "--answers",
                    str(ROOT / "harness/fixtures/intake.answers.json"),
                    "--target",
                    str(target),
                    "--apply",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            if not load_json(ROOT / "harness/project.yaml").get("template_mode", False):
                self.assertEqual(2, result.returncode)
                self.assertIn("cross-repository intake", result.stderr)
                return
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            result = subprocess.run(
                [sys.executable, str(target / "tools/harness_check.py"), "--json"],
                cwd=target,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue((target / "harness/intake.json").is_file())
            self.assertTrue((target / ".pi/settings.json").is_file())
            self.assertTrue((target / "harness/adapters/pi.json").is_file())

    def test_python_fixture_creates_executable_profile_contract(self) -> None:
        if not load_json(ROOT / "harness/project.yaml").get("template_mode", False):
            self.skipTest("cross-repository bootstrap is template-only")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "python-derived"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/project_intake.py"),
                    "--answers",
                    str(ROOT / "harness/fixtures/python-data.answers.json"),
                    "--target",
                    str(target),
                    "--apply",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            contract = load_json(target / "harness/project.yaml")
            self.assertFalse(contract["template_mode"])
            self.assertEqual("python-data", contract["project"]["profile"])
            dry_run = subprocess.run(
                [sys.executable, str(target / "tools/run_quality.py"), "--dry-run"],
                cwd=target,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            self.assertEqual(0, dry_run.returncode, dry_run.stdout + dry_run.stderr)
            self.assertIn("project quality [typecheck]", dry_run.stdout)
            self.assertIn("project quality [unit]", dry_run.stdout)

    def test_adopt_preserves_existing_files_and_reports_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            target.mkdir()
            (target / "README.md").write_text("existing readme\n", encoding="utf-8")
            (target / "AGENTS.md").write_text("# Existing rules\n", encoding="utf-8")
            existing_loop = target / "tools/loop.py"
            existing_loop.parent.mkdir()
            existing_loop.write_text("# application loop\n", encoding="utf-8")
            generated = {
                "harness/intake.json": "existing intake\n",
                ".github/planning.json": "existing planning\n",
                "docs/project/charter.md": "existing charter\n",
                "docs/project/adoption-gaps.md": "existing adoption report\n",
            }
            for relative, content in generated.items():
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/project_intake.py"),
                    "--answers",
                    str(ROOT / "harness/fixtures/intake.answers.json"),
                    "--target",
                    str(target),
                    "--mode",
                    "adopt",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            self.assertEqual(0, dry_run.returncode, dry_run.stdout + dry_run.stderr)
            dry_payload = json.loads(dry_run.stdout.split("\n", 1)[1])
            self.assertEqual("adopt", dry_payload["project"]["project"]["lifecycle"])
            self.assertEqual("provisional", dry_payload["project"]["project"]["status"])
            self.assertEqual("provisional", dry_payload["intake"]["adoption"]["status"])
            self.assertEqual("sufficient", dry_payload["intake"]["context_readiness"])
            self.assertEqual(
                "provisional", dry_payload["intake"]["adoption"]["reconciliation_status"]
            )
            self.assertGreater(dry_payload["intake"]["adoption"]["gap_count"], 0)
            self.assertTrue(all(dry_payload["intake"]["adoption"]["dispositions"].values()))
            self.assertFalse((target / "harness/project.yaml").exists())
            result = subprocess.run(
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
                env=subprocess_environment(),
            )
            if not load_json(ROOT / "harness/project.yaml").get("template_mode", False):
                self.assertEqual(2, result.returncode)
                self.assertIn("cross-repository intake", result.stderr)
                return
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual("existing readme\n", (target / "README.md").read_text())
            self.assertEqual("# Existing rules\n", (target / "AGENTS.md").read_text())
            self.assertEqual("# application loop\n", existing_loop.read_text())
            self.assertTrue((target / "harness/project.yaml").is_file())
            contract = load_json(target / "harness/project.yaml")
            self.assertFalse(contract["template_mode"])
            self.assertEqual("adopt", contract["project"]["lifecycle"])
            self.assertEqual("provisional", contract["project"]["status"])
            intake = load_json(target / "harness/intake.harness-proposed.json")
            self.assertEqual("provisional", intake["adoption"]["status"])
            self.assertEqual("sufficient", intake["context_readiness"])
            self.assertEqual("provisional", intake["adoption"]["reconciliation_status"])
            self.assertGreater(intake["adoption"]["gap_count"], 0)
            self.assertTrue(all(intake["adoption"]["dispositions"].values()))
            self.assertIn("context readiness: sufficient", result.stdout)
            self.assertIn("harness reconciliation: provisional", result.stdout)
            self.assertIn("harness activation: provisional", result.stdout)
            self.assertTrue((target / ".pi/extensions/context-readiness.ts").is_file())
            self.assertFalse((target / "LICENSE").exists())
            self.assertFalse((target / "CHANGELOG.md").exists())
            self.assertFalse((target / ".github/workflows/harness.yml").exists())
            for relative, content in generated.items():
                self.assertEqual(content, (target / relative).read_text())
            self.assertTrue((target / "harness/intake.harness-proposed.json").is_file())
            self.assertTrue((target / ".github/planning.harness-proposed.json").is_file())
            self.assertTrue((target / "docs/project/charter.harness-proposed.md").is_file())
            gaps = (target / "docs/project/adoption-gaps.harness-proposed.md").read_text()
            self.assertIn("README.md", gaps)
            self.assertIn("AGENTS.md", gaps)
            self.assertIn("Missing merge-required paths", gaps)
            self.assertIn("LICENSE", gaps)
            self.assertIn(".github/workflows/harness.yml", gaps)

    def test_adoption_check_records_an_incompatible_copied_path(self) -> None:
        if not load_json(ROOT / "harness/project.yaml").get("template_mode", False):
            self.skipTest("cross-repository adoption is template-only")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            target.mkdir()
            checker = target / "app_quality.py"
            checker.write_text(
                "from pathlib import Path\n"
                "path = Path('tools/pi_tool_probe.py')\n"
                "if path.exists():\n"
                "    print(path.as_posix())\n"
                "    raise SystemExit(1)\n",
                encoding="utf-8",
            )
            readme = target / "README.md"
            readme.write_bytes(b"application readme\x00bytes\n")
            command = f"{sys.executable} app_quality.py"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/project_intake.py"),
                    "--answers",
                    str(ROOT / "harness/fixtures/intake.answers.json"),
                    "--target",
                    str(target),
                    "--mode",
                    "adopt",
                    "--adoption-check",
                    command,
                    "--apply",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
                env=subprocess_environment(),
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(b"application readme\x00bytes\n", readme.read_bytes())
            intake = load_json(target / "harness/intake.json")
            quality = intake["adoption"]["quality"]
            self.assertEqual("incompatible", quality["status"])
            self.assertEqual(command, quality["command"])
            self.assertEqual(0, quality["baseline_exit_code"])
            self.assertEqual(1, quality["adopted_exit_code"])
            self.assertEqual(["tools/pi_tool_probe.py"], quality["incompatible_paths"])
            self.assertEqual("provisional", intake["adoption"]["status"])
            report = (target / "docs/project/adoption-gaps.md").read_text(encoding="utf-8")
            self.assertIn(f"Exact application command: `{command}`", report)
            self.assertIn("Status: `incompatible`", report)
            self.assertIn("`tools/pi_tool_probe.py`", report)
            self.assertIn("application quality compatibility: incompatible", result.stdout)

    def test_adoption_check_is_rejected_outside_existing_repository_adoption(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/project_intake.py"),
                "--answers",
                str(ROOT / "harness/fixtures/intake.answers.json"),
                "--mode",
                "new",
                "--adoption-check",
                "make check",
            ],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            env=subprocess_environment(),
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("supported only when adopting an existing repository", result.stderr)

    def test_adoption_copies_only_upstream_owned_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            target.mkdir()
            (target / "tools").mkdir()
            existing_tool = target / "tools/github_planning.py"
            existing_tool.write_bytes(b"application planning\x00bytes\n")

            dispositions = copy_missing_for_adoption(ROOT, target)

            self.assertEqual(b"application planning\x00bytes\n", existing_tool.read_bytes())
            self.assertIn("tools/github_planning.py", dispositions["merge_required_existing"])
            self.assertIn("tests/test_github_planning.py", dispositions["adoption_deferred"])
            self.assertIn("tests/test_loop.py", dispositions["adoption_deferred"])
            self.assertIn("LICENSE", dispositions["merge_required_missing"])
            self.assertIn(".github/workflows/harness.yml", dispositions["merge_required_missing"])
            self.assertTrue((target / "tools/loop.py").is_file())
            self.assertTrue((target / "harness/loops/engineering-loop.yaml").is_file())
            self.assertTrue((target / "harness.lock").is_file())
            self.assertFalse((target / "LICENSE").exists())
            self.assertFalse((target / ".github/workflows/harness.yml").exists())

    def test_adoption_refuses_symlink_escape_before_copying_anything(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            outside = Path(directory) / "outside"
            target.mkdir()
            outside.mkdir()
            (target / "tools").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "through symlink"):
                copy_missing_for_adoption(ROOT, target)

            self.assertEqual([], list(outside.iterdir()))
            self.assertFalse((target / ".agents").exists())

    def test_adoption_refuses_symlink_root_before_copying_anything(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "outside"
            outside.mkdir()
            target = Path(directory) / "existing"
            target.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symlink target repository"):
                copy_missing_for_adoption(ROOT, target)

            self.assertEqual([], list(outside.iterdir()))

    def test_adoption_cli_refuses_symlink_root_before_copying_anything(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "outside"
            outside.mkdir()
            target = Path(directory) / "existing"
            target.symlink_to(outside, target_is_directory=True)

            result = subprocess.run(
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
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("symlink target repository", result.stderr)
            self.assertEqual([], list(outside.iterdir()))

    def test_new_project_cli_refuses_symlinked_parent_before_copying_anything(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "outside"
            outside.mkdir()
            parent = Path(directory) / "parent"
            parent.symlink_to(outside, target_is_directory=True)
            target = parent / "new-project"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/project_intake.py"),
                    "--answers",
                    str(ROOT / "harness/fixtures/intake.answers.json"),
                    "--target",
                    str(target),
                    "--mode",
                    "new",
                    "--apply",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("symlink target repository", result.stderr)
            self.assertEqual([], list(outside.iterdir()))

    def test_adoption_refuses_non_directory_ancestor_before_copying_anything(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            target.mkdir()
            (target / "tools").write_text("application file\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "non-directory ancestor"):
                copy_missing_for_adoption(ROOT, target)

            self.assertEqual("application file\n", (target / "tools").read_text())
            self.assertEqual(["tools"], sorted(path.name for path in target.iterdir()))

    def test_adoption_preserves_generated_artifacts_and_refuses_second_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            originals = {
                "harness/intake.json": b"application intake\x00bytes\n",
                ".github/planning.json": b"application planning\x00bytes\n",
                "docs/project/charter.md": b"application charter\x00bytes\n",
                "docs/project/adoption-gaps.md": b"application report\x00bytes\n",
            }
            for relative, content in originals.items():
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)

            outputs = adoption_output_paths(target)

            self.assertEqual(
                target / "harness/intake.harness-proposed.json",
                outputs["intake"],
            )
            self.assertEqual(
                target / ".github/planning.harness-proposed.json",
                outputs["planning"],
            )
            self.assertEqual(
                target / "docs/project/charter.harness-proposed.md",
                outputs["charter"],
            )
            self.assertEqual(
                target / "docs/project/adoption-gaps.harness-proposed.md",
                outputs["adoption_report"],
            )
            for relative, content in originals.items():
                self.assertEqual(content, (target / relative).read_bytes())

            outputs["planning"].write_text("existing proposal\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                adoption_output_paths(target)


if __name__ == "__main__":
    unittest.main()
