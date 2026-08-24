import copy
from pathlib import Path
from subprocess import CompletedProcess
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.common import load_json, write_json
from tools.github_planning import (
    bootstrap_project,
    create_project_view,
    diff_state,
    has_drift,
    project_bootstrap_plan,
    field_mismatches,
    flatten_pages,
    graphql_data,
    parse_json_values,
    read_live,
    read_project,
    validate_contract,
    validate_live_fields,
    validate_live_labels,
    validate_live_milestones,
)


ROOT = Path(__file__).resolve().parents[1]


class GitHubPlanningTests(unittest.TestCase):
    def test_contract_is_valid(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        self.assertEqual([], validate_contract(config))

    def test_diff_is_non_destructive_and_precise(self) -> None:
        config = {
            "labels": [{"name": "type:feature", "color": "ffffff", "description": "feature"}],
            "milestones": [{"title": "M0", "description": "zero"}],
            "fields": [{"name": "Status", "data_type": "SINGLE_SELECT"}],
            "project": {"views": []},
        }
        live = {
            "labels": [{"name": "type:feature", "color": "000000", "description": "old"}],
            "milestones": [],
            "fields": [{"name": "Status"}],
            "project_audited": True,
        }
        diff = diff_state(config, live)
        self.assertEqual(1, len(diff["labels"]["update"]))
        self.assertEqual([{"title": "M0", "description": "zero"}], diff["milestones"]["create"])
        self.assertEqual([], diff["project"]["missing_fields"])
        self.assertTrue(has_drift(diff))
        self.assertNotIn("delete", diff["labels"])

    def test_field_options_are_audited(self) -> None:
        desired = [
            {
                "name": "Status",
                "data_type": "SINGLE_SELECT",
                "options": ["Todo", "In Progress", "Done"],
            }
        ]
        live = [
            {
                "name": "Status",
                "type": "ProjectV2SingleSelectField",
                "options": [{"name": "Todo"}, {"name": "Done"}],
            }
        ]
        self.assertEqual("Status", field_mismatches(desired, live)[0]["name"])

    def test_unaudited_project_fields_warn_without_false_drift(self) -> None:
        config = {
            "labels": [],
            "milestones": [],
            "fields": [{"name": "Status", "data_type": "SINGLE_SELECT"}],
            "project": {"views": []},
        }
        diff = diff_state(
            config,
            {
                "labels": [],
                "milestones": [],
                "fields": [],
                "project_audited": False,
            },
        )
        self.assertEqual([], diff["project"]["missing_fields"])
        self.assertEqual([], diff["project"]["mismatched_fields"])
        self.assertFalse(has_drift(diff))
        self.assertIn("not audited", diff["warnings"][0])

    def test_project_bootstrap_is_dry_run_and_uses_canonical_copy(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        config["repository"] = "example/example-agent-project"
        config["project"]["topology"] = "dedicated"
        config["project"]["owner"] = "example"
        config["project"]["number"] = None
        config["project"]["title"] = "Example Agent Project Roadmap"
        plan = project_bootstrap_plan(config)
        self.assertTrue(plan["ok"])
        self.assertTrue(plan["dry_run"])
        self.assertEqual("copy", plan["actions"][0]["action"])
        self.assertEqual("stauntonjr", plan["actions"][0]["source_owner"])
        self.assertEqual(13, plan["actions"][0]["source_number"])
        self.assertTrue(any(item["action"] == "ensure-field" for item in plan["actions"]))
        self.assertTrue(any(item["action"] == "ensure-view" for item in plan["actions"]))

    def test_contract_rejects_shared_project_without_number_and_duplicate_views(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        config["project"]["number"] = None
        config["project"]["views"].append(dict(config["project"]["views"][0]))
        errors = validate_contract(config)
        self.assertIn("shared project topology requires a project number", errors)
        self.assertIn("project views contain duplicate names", errors)

    def test_contract_rejects_malformed_nested_values_without_crashing(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        config["project"]["canonical_source"] = []
        config["project"]["views"] = {"name": "not-a-list"}
        config["labels"][0]["name"] = ["not", "hashable"]
        errors = validate_contract(config)
        self.assertIn("project canonical_source must be an object", errors)
        self.assertIn("project views must be a list", errors)
        self.assertIn("every labels entry requires name", errors)
        for root in ([], None, "planning"):
            with self.subTest(root=root):
                self.assertEqual(
                    ["planning contract must be an object"],
                    validate_contract(root),
                )
        for path in ("topology", "view-layout", "bootstrap-method", "field-type"):
            config = load_json(ROOT / ".github/planning.json")
            if path == "topology":
                config["project"]["topology"] = []
            elif path == "view-layout":
                config["project"]["views"][0]["layout"] = []
            elif path == "bootstrap-method":
                config["project"]["bootstrap"]["method"] = []
            else:
                config["fields"][0]["data_type"] = []
            with self.subTest(unhashable=path):
                self.assertTrue(validate_contract(config))

    def test_contract_rejects_every_mutation_bearing_value_before_live_work(self) -> None:
        base = load_json(ROOT / ".github/planning.json")

        cases = []
        config = copy.deepcopy(base)
        config["fields"][0].pop("data_type")
        cases.append(("missing field type", config, "invalid data_type"))
        config = copy.deepcopy(base)
        config["fields"][0]["data_type"] = "UNKNOWN"
        cases.append(("invalid field type", config, "invalid data_type"))
        config = copy.deepcopy(base)
        config["fields"][0]["data_type"] = "ITERATION"
        cases.append(("unsupported CLI field type", config, "invalid data_type"))
        config = copy.deepcopy(base)
        config["fields"][0]["options"] = ["Todo", "Todo"]
        cases.append(("duplicate options", config, "duplicate options"))
        config = copy.deepcopy(base)
        config["fields"][0]["options"] = ["Todo", 1]
        cases.append(("non-string option", config, "invalid options"))
        config = copy.deepcopy(base)
        config["labels"][0].pop("color")
        cases.append(("missing label color", config, "six-digit hex color"))
        config = copy.deepcopy(base)
        config["labels"][0]["color"] = "not-hex"
        cases.append(("invalid label color", config, "six-digit hex color"))
        config = copy.deepcopy(base)
        config["labels"][0]["description"] = 1
        cases.append(("invalid label description", config, "description must be a string"))
        config = copy.deepcopy(base)
        config["milestones"][0]["description"] = None
        cases.append(("invalid milestone description", config, "description must be a string"))
        config = copy.deepcopy(base)
        config["repository"] = "stauntonjr /repo"
        cases.append(("whitespace repository", config, "without whitespace"))
        config = copy.deepcopy(base)
        config["project"]["owner"] = " stauntonjr"
        cases.append(("whitespace owner", config, "valid login"))
        config = copy.deepcopy(base)
        config["project"]["allow_unmanaged_views"] = "yes"
        cases.append(("invalid unmanaged policy", config, "must be boolean"))
        config = copy.deepcopy(base)
        config["project"]["views"][0]["name"] = "   "
        cases.append(("whitespace view name", config, "every project view requires name"))
        config = copy.deepcopy(base)
        config["fields"][0]["name"] = "   "
        cases.append(("whitespace field name", config, "every fields entry requires name"))

        for name, config, expected in cases:
            with self.subTest(name=name):
                self.assertTrue(
                    any(expected in error for error in validate_contract(config)),
                    validate_contract(config),
                )

    def test_offline_cli_rejects_invalid_write_contract_without_gh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = load_json(ROOT / ".github/planning.json")
            config["labels"][0]["color"] = "invalid"
            write_json(root / ".github/planning.json", config)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/github_planning.py"),
                    "--root",
                    str(root),
                    "audit",
                    "--offline",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        self.assertEqual(1, result.returncode)
        self.assertIn("six-digit hex color", result.stdout)

    def test_project_view_and_repository_drift_is_reported_without_deletion(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        live = {
            "labels": [],
            "milestones": [],
            "fields": [],
            "project_audited": True,
            "project": {
                "title": config["project"]["title"],
                "views": [
                    {
                        "name": "Roadmap",
                        "layout": "TABLE_LAYOUT",
                        "filter": "wrong",
                    },
                    {"name": "Personal", "layout": "TABLE_LAYOUT", "filter": None},
                ],
                "repositories": [],
            },
        }
        diff = diff_state(config, live)
        self.assertEqual("Roadmap", diff["project"]["mismatched_views"][0]["name"])
        self.assertEqual(3, len(diff["project"]["missing_views"]))
        self.assertEqual("Personal", diff["project"]["unmanaged_views"][0]["name"])
        self.assertTrue(diff["project"]["repository_link_missing"])
        self.assertNotIn("delete", diff["project"])
        self.assertTrue(has_drift(diff))

    def test_disallowed_unmanaged_view_is_drift_but_not_a_delete_plan(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        config["project"]["allow_unmanaged_views"] = False
        live = {
            "labels": [],
            "milestones": [],
            "fields": [],
            "project_audited": True,
            "project": {
                "title": config["project"]["title"],
                "views": [{"name": "Personal", "layout": "TABLE_LAYOUT", "filter": None}],
                "repositories": [{"nameWithOwner": config["repository"]}],
            },
        }
        diff = diff_state(config, live)
        self.assertEqual("Personal", diff["project"]["disallowed_unmanaged_views"][0]["name"])
        self.assertNotIn("delete", diff["project"])
        self.assertTrue(has_drift(diff))

    def test_paginated_json_parser_accepts_zero_single_and_multiple_values(self) -> None:
        self.assertEqual([], parse_json_values("[]\n", command="gh api empty"))
        single = parse_json_values('[{"name":"one"}]\n', command="gh api single")
        self.assertEqual([{"name": "one"}], flatten_pages(single))
        multiple = parse_json_values(
            '[{"name":"one"}]\n[{"name":"two"}]\n',
            command="gh api multiple",
        )
        self.assertEqual([{"name": "one"}, {"name": "two"}], flatten_pages(multiple))

    def test_paginated_json_parser_rejects_empty_or_malformed_output(self) -> None:
        for output in ("", '[{"name":]'):
            with self.subTest(output=output):
                with self.assertRaisesRegex(RuntimeError, "gh api labels"):
                    parse_json_values(output, command="gh api labels")

    def test_page_flattener_rejects_non_object_and_mixed_shapes(self) -> None:
        for payload in ({}, None, [1], [{"name": "one"}, []], [[{"name": "one"}], [1]]):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(RuntimeError, "unexpected|JSON array"):
                    flatten_pages(payload, collection="GitHub labels")

    def test_live_label_and_milestone_mutation_fields_are_fail_closed(self) -> None:
        valid_label = {"name": "type:feature", "color": "A1b2C3", "description": None}
        valid_milestone = {"number": 1, "title": "M0", "description": "zero"}
        self.assertEqual([valid_label], validate_live_labels([valid_label]))
        self.assertEqual([valid_milestone], validate_live_milestones([valid_milestone]))

        invalid_labels = [
            {"name": "type:feature", "color": 123456, "description": "feature"},
            {"name": "type:feature", "color": "not-hex", "description": "feature"},
            {"name": "type:feature", "color": "ffffff", "description": 1},
        ]
        for label in invalid_labels:
            with self.subTest(label=label):
                with self.assertRaisesRegex(RuntimeError, "labels entry 0"):
                    validate_live_labels([label])

        invalid_milestones = [
            {"title": "M0", "description": "zero"},
            {"number": "../../issues/1", "title": "M0", "description": "zero"},
            {"number": True, "title": "M0", "description": "zero"},
            {"number": 1, "title": "M0", "description": 1},
        ]
        for milestone in invalid_milestones:
            with self.subTest(milestone=milestone):
                with self.assertRaisesRegex(RuntimeError, "milestones entry 0"):
                    validate_live_milestones([milestone])

    def test_graphql_errors_are_rejected_even_when_data_is_present(self) -> None:
        payload = {"errors": [{"message": "partial failure"}], "data": {"user": {}}}
        with self.assertRaisesRegex(RuntimeError, "GraphQL errors"):
            graphql_data(payload, operation="Project example/1")
        self.assertEqual({"user": {}}, graphql_data({"errors": [], "data": {"user": {}}}, operation="Project example/1"))

    def test_duplicate_managed_live_field_and_view_cannot_report_convergence(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        fields = [
            {
                "name": item["name"],
                "type": "ProjectV2SingleSelectField",
                "options": [{"name": option} for option in item["options"]],
            }
            for item in config["fields"]
        ]
        fields.append(
            {
                "name": "Status",
                "type": "ProjectV2Field",
                "options": [],
            }
        )
        views = [dict(view) for view in config["project"]["views"]]
        views.append({"name": "Roadmap", "layout": "TABLE_LAYOUT", "filter": "wrong"})
        live = {
            "labels": [dict(item) for item in config["labels"]],
            "milestones": [
                {"number": index, **item}
                for index, item in enumerate(config["milestones"], start=1)
            ],
            "fields": fields,
            "project_audited": True,
            "project": {
                "title": config["project"]["title"],
                "views": views,
                "repositories": [{"nameWithOwner": config["repository"]}],
            },
        }
        diff = diff_state(config, live)
        self.assertIn("contains 2 entries", diff["project"]["mismatched_fields"][0]["reasons"][0])
        self.assertIn("contains 2 entries", diff["project"]["mismatched_views"][0]["reasons"][0])
        self.assertTrue(has_drift(diff))

    def test_duplicate_managed_label_and_milestone_are_explicit_drift(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        labels = [dict(item) for item in config["labels"]]
        labels.append(dict(config["labels"][0]))
        milestones = [
            {"number": index, **item}
            for index, item in enumerate(config["milestones"], start=1)
        ]
        milestones.append({"number": 99, **config["milestones"][0]})
        diff = diff_state(
            config,
            {
                "labels": labels,
                "milestones": milestones,
                "fields": [],
                "project_audited": False,
            },
        )
        self.assertEqual("type:feature", diff["labels"]["identity_conflicts"][0]["name"])
        self.assertEqual(
            "M0 Harness and discovery",
            diff["milestones"]["identity_conflicts"][0]["name"],
        )
        self.assertTrue(has_drift(diff))

    def test_live_audit_uses_paginate_without_unsupported_slurp(self) -> None:
        config = {
            "repository": "stauntonjr/example",
            "project": {"number": None, "owner": "stauntonjr"},
        }
        command_results = [
            CompletedProcess([], 0, "stauntonjr\n", ""),
            CompletedProcess([], 0, "stauntonjr/example\n", ""),
        ]
        with (
            patch("tools.github_planning.run", side_effect=command_results),
            patch("tools.github_planning.gh_json", side_effect=[[], []]) as github_json,
        ):
            live = read_live(ROOT, config)

        self.assertEqual("stauntonjr/example", live["repository"])
        for call in github_json.call_args_list:
            self.assertIn("--paginate", call.args)
            self.assertNotIn("--slurp", call.args)

    def test_read_project_uses_owner_specific_graphql_and_returns_views(self) -> None:
        summary = {"owner": {"login": "example", "type": "User"}}
        payload = {
            "data": {
                "user": {
                    "projectV2": {
                        "id": "PVT_example",
                        "number": 7,
                        "title": "Example",
                        "views": {
                            "nodes": [
                                {
                                    "id": "PVTV_example",
                                    "number": 1,
                                    "name": "Roadmap",
                                    "layout": "ROADMAP_LAYOUT",
                                    "filter": "is:issue",
                                }
                            ],
                            "pageInfo": {"hasNextPage": False},
                        },
                        "repositories": {
                            "nodes": [{"nameWithOwner": "example/repo"}],
                            "pageInfo": {"hasNextPage": False},
                        },
                    }
                }
            }
        }
        with patch("tools.github_planning.gh_json", side_effect=[summary, payload]) as github_json:
            project = read_project(ROOT, owner="example", number=7)
        self.assertEqual("Roadmap", project["views"][0]["name"])
        self.assertEqual("example/repo", project["repositories"][0]["nameWithOwner"])
        query_arg = next(
            arg
            for arg in github_json.call_args_list[1].args
            if isinstance(arg, str) and arg.startswith("query=")
        )
        self.assertIn("user(login: $owner)", query_arg)
        self.assertNotIn("OWNER_KIND", query_arg)

    def test_read_project_rejects_malformed_identity_and_connection_nodes(self) -> None:
        summary = {"owner": {"login": "example", "type": "User"}}

        def payload() -> dict:
            return {
                "data": {
                    "user": {
                        "projectV2": {
                            "id": "PVT_example",
                            "number": 1,
                            "title": "Example",
                            "views": {
                                "nodes": [
                                    {
                                        "id": "PVTV_example",
                                        "number": 1,
                                        "name": "Roadmap",
                                        "layout": "ROADMAP_LAYOUT",
                                        "filter": "is:issue",
                                    }
                                ],
                                "pageInfo": {"hasNextPage": False},
                            },
                            "repositories": {
                                "nodes": [{"nameWithOwner": "example/repo"}],
                                "pageInfo": {"hasNextPage": False},
                            },
                        }
                    }
                }
            }

        mutations = []
        value = payload()
        value["data"]["user"]["projectV2"]["id"] = "   "
        mutations.append(("empty project ID", summary, value))
        value = payload()
        value["data"]["user"]["projectV2"]["number"] = True
        mutations.append(("boolean project number", summary, value))
        value = payload()
        value["data"]["user"]["projectV2"]["repositories"]["nodes"] = [None]
        mutations.append(("null repository node", summary, value))
        value = payload()
        value["data"]["user"]["projectV2"]["repositories"]["nodes"] = [
            {"nameWithOwner": 1}
        ]
        mutations.append(("non-string repository identity", summary, value))
        mutations.append(("invalid owner object", {"owner": []}, payload()))

        for name, owner_summary, project_payload in mutations:
            with self.subTest(name=name), patch(
                "tools.github_planning.gh_json",
                side_effect=[owner_summary, project_payload],
            ):
                with self.assertRaises((RuntimeError, ValueError)):
                    read_project(ROOT, owner="example", number=1)

    def test_live_field_shape_validation_rejects_malformed_entries(self) -> None:
        for fields in (
            None,
            [None],
            [{"name": "", "type": "ProjectV2Field"}],
            [{"name": "Area", "type": "ProjectV2SingleSelectField", "options": [None]}],
        ):
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(RuntimeError, "field-list"):
                    validate_live_fields(fields)

    def test_create_project_view_uses_variables_and_sets_filter(self) -> None:
        created = {
            "data": {
                "createProjectV2View": {"projectV2View": {"id": "PVTV_example"}}
            }
        }
        updated = {
            "data": {
                "updateProjectV2View": {"projectV2View": {"id": "PVTV_example"}}
            }
        }
        with patch("tools.github_planning.gh_json", side_effect=[created, updated]) as github_json:
            view_id = create_project_view(
                ROOT,
                project_id="PVT_example",
                view={"name": "Active", "layout": "TABLE_LAYOUT", "filter": "status:Todo"},
            )
        self.assertEqual("PVTV_example", view_id)
        flattened_args = [arg for call in github_json.call_args_list for arg in call.args]
        self.assertIn("name=Active", flattened_args)
        self.assertIn("filter=status:Todo", flattened_args)

    def test_project_view_creation_rejects_invalid_input_and_returned_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            create_project_view(
                ROOT,
                project_id="   ",
                view={"name": "Active", "layout": "TABLE_LAYOUT", "filter": ""},
            )
        for returned_id in (1, "   "):
            with self.subTest(returned_id=returned_id), patch(
                "tools.github_planning.gh_json",
                return_value={
                    "data": {
                        "createProjectV2View": {
                            "projectV2View": {"id": returned_id}
                        }
                    }
                },
            ):
                with self.assertRaisesRegex(RuntimeError, "invalid Project view"):
                    create_project_view(
                        ROOT,
                        project_id="PVT_example",
                        view={"name": "Active", "layout": "TABLE_LAYOUT", "filter": ""},
                    )

    def test_existing_project_bootstrap_is_idempotent_when_state_matches(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        fields = [
            {
                "id": f"PVTSSF_{index}",
                "name": item["name"],
                "type": "ProjectV2SingleSelectField",
                "options": [
                    {"id": f"option-{index}-{option_index}", "name": option}
                    for option_index, option in enumerate(item.get("options", []), start=1)
                ],
            }
            for index, item in enumerate(config["fields"], start=1)
        ]
        project = {
            "id": "PVT_example",
            "number": 13,
            "title": config["project"]["title"],
            "views": [
                {"id": str(index), **view}
                for index, view in enumerate(config["project"]["views"], start=1)
            ],
            "repositories": [{"nameWithOwner": config["repository"]}],
        }
        with (
            patch(
                "tools.github_planning.run",
                return_value=CompletedProcess([], 0, config["repository"] + "\n", ""),
            ) as command,
            patch(
                "tools.github_planning.gh_json",
                side_effect=[{"fields": fields}, {"fields": fields}],
            ),
            patch("tools.github_planning.read_project", side_effect=[project, project]),
        ):
            result = bootstrap_project(ROOT, config)
        self.assertTrue(result["ok"])
        self.assertEqual([], result["operations"])
        self.assertEqual(1, command.call_count)

    def test_bootstrap_never_persists_an_invalid_created_project_number(self) -> None:
        for invalid_number in (True, 0, "14"):
            config = load_json(ROOT / ".github/planning.json")
            config["repository"] = "example/disposable"
            config["project"]["topology"] = "dedicated"
            config["project"]["owner"] = "example"
            config["project"]["number"] = None
            config["project"]["title"] = "Disposable"
            with (
                self.subTest(invalid_number=invalid_number),
                patch(
                    "tools.github_planning.run",
                    return_value=CompletedProcess([], 0, "example/disposable\n", ""),
                ),
                patch("tools.github_planning.gh_json", return_value={"number": invalid_number}),
                patch("tools.github_planning.read_project") as project_read,
                patch("tools.github_planning.write_json") as planning_write,
            ):
                with self.assertRaisesRegex(RuntimeError, "valid number"):
                    bootstrap_project(ROOT, config)
                project_read.assert_not_called()
                planning_write.assert_not_called()
                self.assertIsNone(config["project"]["number"])


if __name__ == "__main__":
    unittest.main()
