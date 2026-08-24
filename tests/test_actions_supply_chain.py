from pathlib import Path
import tempfile
import unittest

from harness.runtime.actions_supply_chain import check_workflows
from tools.check_actions_supply_chain import check_workflows as compatibility_check_workflows


ROOT = Path(__file__).resolve().parents[1]


class ActionsSupplyChainTests(unittest.TestCase):
    def test_historical_tool_module_reexports_the_runtime_implementation(self) -> None:
        self.assertIs(check_workflows, compatibility_check_workflows)

    def test_repository_workflows_are_immutable_and_least_privilege(self) -> None:
        self.assertEqual([], check_workflows(ROOT))

    def test_mutable_action_and_missing_permissions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "unsafe.yml").write_text(
                "name: unsafe\non: push\njobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            errors = check_workflows(root)
            self.assertTrue(
                any("missing explicit top-level permissions" in item for item in errors)
            )
            self.assertTrue(any("full 40-character commit SHA" in item for item in errors))

    def test_mutable_reusable_workflow_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "unsafe.yml").write_text(
                "name: unsafe\non: workflow_dispatch\npermissions: {}\n"
                "jobs:\n  call:\n    uses: example/repo/.github/workflows/test.yml@main\n",
                encoding="utf-8",
            )
            errors = check_workflows(root)
            self.assertTrue(any("full 40-character commit SHA" in item for item in errors))

    def test_unreviewed_write_permissions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "unsafe.yml").write_text(
                "name: unsafe\non: workflow_dispatch\npermissions:\n"
                "  contents: write\n  actions: write\njobs: {}\n",
                encoding="utf-8",
            )
            errors = check_workflows(root)
            self.assertTrue(any("actions, contents" in item for item in errors))

    def test_yaml_equivalent_quoted_and_spaced_keys_cannot_bypass_policy(self) -> None:
        variants = (
            'permissions:\n  "contents": write\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps: []\n',
            'permissions:\n  contents: "write"\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps: []\n',
            "permissions:\n  contents: 'write'\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps: []\n",
            'permissions: {}\njobs:\n  call:\n    "uses": owner/repo/.github/workflows/test.yml@main\n',
            "permissions: {}\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses : owner/action@main\n",
        )
        for workflow in variants:
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                workflows = root / ".github/workflows"
                workflows.mkdir(parents=True)
                (workflows / "unsafe.yml").write_text(workflow, encoding="utf-8")
                errors = check_workflows(root)
                self.assertTrue(errors)

    def test_docker_action_requires_immutable_image_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "unsafe.yml").write_text(
                "permissions: {}\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n"
                "      - uses: docker://alpine:latest\n",
                encoding="utf-8",
            )
            errors = check_workflows(root)
            self.assertTrue(any("sha256 image digest" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
