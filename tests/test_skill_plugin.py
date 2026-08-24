from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.harness_check import Result, validate_optional_skill_plugin
from tools.skill_plugin import (
    LICENSE_RELATIVE,
    MANIFEST_RELATIVE,
    MARKETPLACE_RELATIVE,
    PLUGIN_NAME,
    PROVENANCE_RELATIVE,
    SKILLS_RELATIVE,
    SOURCE_RELATIVE,
    check,
    sync,
)


ROOT = Path(__file__).resolve().parents[1]


class SkillPluginTests(unittest.TestCase):
    def copy_fixture(self) -> Path:
        temporary = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temporary)
        for relative in (SOURCE_RELATIVE, SKILLS_RELATIVE):
            shutil.copytree(ROOT / relative, temporary / relative)
        for relative in (MANIFEST_RELATIVE, MARKETPLACE_RELATIVE, PROVENANCE_RELATIVE):
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        shutil.copy2(ROOT / "LICENSE", temporary / "LICENSE")
        target_license = temporary / LICENSE_RELATIVE
        target_license.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / LICENSE_RELATIVE, target_license)
        return temporary

    def test_repository_plugin_mirror_is_current(self) -> None:
        self.assertEqual([], check(ROOT))

    def test_check_rejects_a_modified_packaged_skill(self) -> None:
        root = self.copy_fixture()
        packaged = root / SKILLS_RELATIVE / "loop-report/SKILL.md"
        packaged.write_text(packaged.read_text(encoding="utf-8") + "\nchanged\n")
        self.assertIn(
            "plugin mirror differs from generated skill: loop-report/SKILL.md",
            check(root),
        )

    def test_sync_restores_mirror_and_provenance(self) -> None:
        root = self.copy_fixture()
        canonical = root / SOURCE_RELATIVE / "loop-report/SKILL.md"
        canonical.write_text(canonical.read_text(encoding="utf-8") + "\nnew rule\n")
        self.assertTrue(check(root))
        sync(root)
        self.assertEqual([], check(root))
        self.assertEqual(
            canonical.read_bytes(),
            (root / SKILLS_RELATIVE / "loop-report/SKILL.md").read_bytes(),
        )
        provenance = json.loads((root / PROVENANCE_RELATIVE).read_text(encoding="utf-8"))
        self.assertEqual(PLUGIN_NAME, provenance["plugin"]["name"])

    def test_packaged_cross_skill_references_are_namespaced(self) -> None:
        packaged = (
            ROOT
            / SKILLS_RELATIVE
            / "execute-engineering-loop/agents/openai.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "$agentic-engineering-harness:execute-engineering-loop",
            packaged,
        )
        self.assertNotIn('"Use $execute-engineering-loop', packaged)

    def test_check_rejects_policy_in_the_skill_distribution(self) -> None:
        root = self.copy_fixture()
        policy = root / SKILLS_RELATIVE / "AGENTS.md"
        policy.write_text("project policy must stay outside the plugin\n", encoding="utf-8")
        errors = check(root)
        self.assertIn("plugin mirror has extra files: AGENTS.md", errors)

    def test_check_rejects_stale_provenance(self) -> None:
        root = self.copy_fixture()
        provenance_path = root / PROVENANCE_RELATIVE
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        provenance["plugin"]["version"] = "9.9.9"
        provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
        self.assertIn(
            "plugin provenance is stale or does not match canonical skills",
            check(root),
        )

    def test_check_rejects_a_mismatched_plugin_license(self) -> None:
        root = self.copy_fixture()
        (root / LICENSE_RELATIVE).write_text("different license\n", encoding="utf-8")
        self.assertIn(
            "plugin LICENSE must match the repository MIT license",
            check(root),
        )

    def test_check_rejects_an_invalid_plugin_version(self) -> None:
        root = self.copy_fixture()
        manifest_path = root / MANIFEST_RELATIVE
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = "version-one"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "strict SemVer"):
            check(root)

    def test_check_rejects_a_manifest_change_without_provenance_sync(self) -> None:
        root = self.copy_fixture()
        manifest_path = root / MANIFEST_RELATIVE
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["description"] = "A valid but not yet provenance-synchronized description."
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertIn(
            "plugin provenance is stale or does not match canonical skills",
            check(root),
        )

    def test_sync_refuses_a_symlinked_license_before_writing(self) -> None:
        root = self.copy_fixture()
        outside = root.parent / f"{root.name}-outside-license"
        self.addCleanup(outside.unlink, missing_ok=True)
        outside.write_text("outside remains unchanged\n", encoding="utf-8")
        plugin_license = root / LICENSE_RELATIVE
        plugin_license.unlink()
        plugin_license.symlink_to(outside)
        before = (root / SKILLS_RELATIVE / "loop-report/SKILL.md").read_bytes()
        with self.assertRaisesRegex(ValueError, "symlinked plugin path"):
            sync(root)
        self.assertEqual("outside remains unchanged\n", outside.read_text(encoding="utf-8"))
        self.assertEqual(
            before,
            (root / SKILLS_RELATIVE / "loop-report/SKILL.md").read_bytes(),
        )

    def test_harness_check_does_not_follow_a_marketplace_symlink(self) -> None:
        root = self.copy_fixture()
        outside = root.parent / f"{root.name}-outside-marketplace"
        self.addCleanup(outside.unlink, missing_ok=True)
        outside.write_text("not JSON and outside the repository\n", encoding="utf-8")
        marketplace = root / MARKETPLACE_RELATIVE
        marketplace.unlink()
        marketplace.symlink_to(outside)
        result = Result()
        validate_optional_skill_plugin(root, result)
        self.assertEqual(
            ["skill plugin marketplace must be an ordinary file"],
            result.errors,
        )


if __name__ == "__main__":
    unittest.main()
