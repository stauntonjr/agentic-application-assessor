import json
from pathlib import Path
import tempfile
import unittest

from tools.run_quality import quality_commands


def write_project(root: Path, *, required: list[str], commands: dict[str, str]) -> None:
    (root / "harness").mkdir()
    project = {
        "template_mode": False,
        "engineering": {
            "command_contract": {"bootstrap": "not-applicable: dependency-free", **commands},
            "quality": {"required_checks": required},
        },
    }
    (root / "harness/project.yaml").write_text(json.dumps(project), encoding="utf-8")


class RunQualityTests(unittest.TestCase):
    def test_required_commands_are_dispatched_in_stable_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(
                root,
                required=["unit", "format_check", "lint"],
                commands={
                    "unit": "python3 -m unittest",
                    "format_check": "ruff format --check .",
                    "lint": "ruff check .",
                },
            )
            commands = quality_commands(root)
            self.assertEqual(["format_check", "lint", "unit"], [item[0] for item in commands])

    def test_required_not_applicable_capability_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(
                root,
                required=["typecheck"],
                commands={"typecheck": "not-applicable: untyped prototype"},
            )
            with self.assertRaisesRegex(ValueError, "marked not applicable: typecheck"):
                quality_commands(root)

    def test_successful_noop_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(root, required=["unit"], commands={"unit": "true"})
            with self.assertRaisesRegex(ValueError, "successful no-op"):
                quality_commands(root)


if __name__ == "__main__":
    unittest.main()
