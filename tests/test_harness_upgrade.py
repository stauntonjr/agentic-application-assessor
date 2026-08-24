import json
from pathlib import Path
import tempfile
import unittest

from tools.harness_upgrade import (
    apply_release_plan,
    build_plan,
    build_release_plan,
    create_lock,
    rollback_receipt,
    validate_lock,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_release(root: Path, version: str, payload: str, policy_text: str) -> None:
    write_json(
        root / "harness/version.json",
        {
            "current": version,
            "upstream_repository": "example/agentic-project-template",
        },
    )
    write_json(
        root / "harness/project.yaml",
        {"harness_version": version, "project": {"name": "Example"}},
    )
    write_json(
        root / "harness/ownership.json",
        {
            "schema_version": "1.0",
            "default_ownership": "project-owned",
            "rules": [
                {"pattern": "payload.txt", "ownership": "upstream-owned"},
                {"pattern": "harness/version.json", "ownership": "upstream-owned"},
                {"pattern": "harness/ownership.json", "ownership": "upstream-owned"},
                {"pattern": "policy.md", "ownership": "merge-required"},
                {"pattern": "harness/project.yaml", "ownership": "project-owned"},
            ],
        },
    )
    (root / "payload.txt").write_text(payload, encoding="utf-8")
    (root / "policy.md").write_text(policy_text, encoding="utf-8")
    lock = create_lock(
        root,
        repository="example/agentic-project-template",
        release=f"v{version}",
        commit=f"commit-{version}",
    )
    write_json(root / "harness.lock", lock)


class HarnessUpgradeTests(unittest.TestCase):
    def test_migration_plan_is_non_mutating_and_marks_manual_review(self) -> None:
        current = json.loads((ROOT / "harness/project.yaml").read_text(encoding="utf-8"))[
            "harness_version"
        ]
        manifest = {
            "schema_version": "1.0",
            "from_version": current,
            "to_version": "NEXT_VERSION",
            "operations": [
                {
                    "action": "manual",
                    "path": "AGENTS.md",
                    "reason": "Reconcile policy changes",
                    "ownership": "merge-required",
                }
            ],
        }
        self.assertEqual([], validate_manifest(manifest))
        plan = build_plan(ROOT, manifest)
        self.assertTrue(plan["ok"])
        self.assertTrue(plan["dry_run"])
        self.assertTrue(plan["operations"][0]["requires_explicit_review"])

    def test_migration_rejects_path_escape(self) -> None:
        manifest = {
            "schema_version": "1.0",
            "from_version": "0.1.0",
            "to_version": "0.2.0",
            "operations": [
                {
                    "action": "remove",
                    "path": "../outside",
                    "reason": "invalid",
                }
            ],
        }
        self.assertTrue(validate_manifest(manifest))

    def test_lock_records_provenance_checksums_and_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_release(root, "1.0.0", "old\n", "policy\n")
            lock = json.loads((root / "harness.lock").read_text(encoding="utf-8"))
            self.assertEqual([], validate_lock(lock))
            self.assertEqual("v1.0.0", lock["upstream"]["release"])
            self.assertEqual("upstream-owned", lock["files"]["payload.txt"]["ownership"])
            self.assertEqual("merge-required", lock["files"]["policy.md"]["ownership"])

    def test_lock_ignores_generated_dependency_and_build_trees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".venv/lib").mkdir(parents=True)
            (root / ".venv/lib/dependency.py").write_text("generated\n", encoding="utf-8")
            (root / "node_modules/package").mkdir(parents=True)
            (root / "node_modules/package/index.js").write_text("generated\n", encoding="utf-8")
            (root / "dist").mkdir()
            (root / "dist/artifact.whl").write_text("generated\n", encoding="utf-8")
            make_release(root, "1.0.0", "old\n", "policy\n")
            lock = json.loads((root / "harness.lock").read_text(encoding="utf-8"))
            self.assertNotIn(".venv/lib/dependency.py", lock["files"])
            self.assertNotIn("node_modules/package/index.js", lock["files"])
            self.assertNotIn("dist/artifact.whl", lock["files"])

    def test_three_way_plan_separates_safe_and_manual_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            source = base / "release"
            root.mkdir()
            source.mkdir()
            make_release(root, "1.0.0", "old\n", "old policy\n")
            make_release(source, "2.0.0", "new\n", "new policy\n")
            (root / "policy.md").write_text("project policy\n", encoding="utf-8")

            plan = build_release_plan(root, source)
            operations = {item["path"]: item for item in plan["operations"]}
            self.assertEqual("ready", operations["payload.txt"]["disposition"])
            self.assertEqual("manual", operations["policy.md"]["disposition"])
            self.assertEqual("manual", operations["harness/project.yaml"]["disposition"])

    def test_apply_requires_manual_resolutions_and_rollback_restores_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            source = base / "release"
            root.mkdir()
            source.mkdir()
            make_release(root, "1.0.0", "old\n", "same policy\n")
            make_release(source, "2.0.0", "new\n", "same policy\n")
            plan = build_release_plan(root, source)
            receipt_root = base / "receipt"

            with self.assertRaisesRegex(ValueError, "require resolutions"):
                apply_release_plan(root, source, plan, {}, receipt_root=receipt_root)

            receipt = apply_release_plan(
                root,
                source,
                plan,
                {"harness/project.yaml": "keep-local"},
                receipt_root=receipt_root,
            )
            self.assertEqual("new\n", (root / "payload.txt").read_text(encoding="utf-8"))
            project = json.loads((root / "harness/project.yaml").read_text(encoding="utf-8"))
            self.assertEqual("2.0.0", project["harness_version"])
            self.assertTrue(receipt.is_file())

            rollback_receipt(root, receipt)
            self.assertEqual("old\n", (root / "payload.txt").read_text(encoding="utf-8"))
            project = json.loads((root / "harness/project.yaml").read_text(encoding="utf-8"))
            self.assertEqual("1.0.0", project["harness_version"])

    def test_rollback_refuses_to_overwrite_later_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            source = base / "release"
            root.mkdir()
            source.mkdir()
            make_release(root, "1.0.0", "old\n", "same policy\n")
            make_release(source, "2.0.0", "new\n", "same policy\n")
            plan = build_release_plan(root, source)
            receipt = apply_release_plan(
                root,
                source,
                plan,
                {"harness/project.yaml": "keep-local"},
                receipt_root=base / "receipt",
            )
            (root / "payload.txt").write_text("later edit\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "later changes"):
                rollback_receipt(root, receipt)

    def test_apply_preflight_rejects_stale_plan_without_partial_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            source = base / "release"
            root.mkdir()
            source.mkdir()
            make_release(root, "1.0.0", "old\n", "same policy\n")
            make_release(source, "2.0.0", "new\n", "same policy\n")
            plan = build_release_plan(root, source)
            (root / "harness/version.json").write_text("changed after plan\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "plan is stale"):
                apply_release_plan(
                    root,
                    source,
                    plan,
                    {"harness/project.yaml": "keep-local"},
                    receipt_root=base / "receipt",
                )
            self.assertEqual("old\n", (root / "payload.txt").read_text(encoding="utf-8"))
            self.assertFalse((base / "receipt").exists())

    def test_plan_rejects_a_different_upstream_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            source = base / "release"
            root.mkdir()
            source.mkdir()
            make_release(root, "1.0.0", "old\n", "same policy\n")
            make_release(source, "2.0.0", "new\n", "same policy\n")
            lock = json.loads((source / "harness.lock").read_text(encoding="utf-8"))
            lock["upstream"]["repository"] = "attacker/different-template"
            write_json(source / "harness.lock", lock)

            with self.assertRaisesRegex(ValueError, "different upstream"):
                build_release_plan(root, source)


if __name__ == "__main__":
    unittest.main()
