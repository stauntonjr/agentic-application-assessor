import json
from pathlib import Path
import tempfile
import unittest

from tools.product_version import product_version_status, resolve_source


class ProductVersionTests(unittest.TestCase):
    def test_resolves_json_compatible_project_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "harness").mkdir()
            project = {
                "template_mode": False,
                "engineering": {
                    "versioning": {
                        "strategy": "semver",
                        "current": "1.2.3",
                        "source": "harness/project.yaml:engineering.versioning.current",
                        "tag_prefix": "v",
                    }
                },
            }
            (root / "harness/project.yaml").write_text(json.dumps(project), encoding="utf-8")
            status = product_version_status(root, "v1.2.3")
            self.assertTrue(status["ok"])
            self.assertEqual("1.2.3", status["resolved"])

    def test_tag_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "harness").mkdir()
            (root / "VERSION").write_text("2.0.0\n", encoding="utf-8")
            project = {
                "template_mode": False,
                "engineering": {
                    "versioning": {
                        "strategy": "semver",
                        "current": "2.0.0",
                        "source": "VERSION",
                        "tag_prefix": "v",
                    }
                },
            }
            (root / "harness/project.yaml").write_text(json.dumps(project), encoding="utf-8")
            status = product_version_status(root, "v1.9.0")
            self.assertFalse(status["ok"])
            self.assertIn("must equal v2.0.0", status["errors"][0])

    def test_source_cannot_escape_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "stay inside"):
                resolve_source(root, "../VERSION")


if __name__ == "__main__":
    unittest.main()
