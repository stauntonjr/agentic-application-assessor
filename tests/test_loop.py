import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.loop import (
    finish_run,
    load_run,
    make_write_set,
    new_attempt,
    parse_criteria,
    record_check,
    record_release_impact,
    record_verdict,
    recovery_status,
    resume_run,
    revise_run,
    set_state,
    start_run,
    waive_criterion,
)
from tools.project_intake import mark_adoption_state

ROOT = Path(__file__).resolve().parents[1]


def init_repository(root: Path, *, commit: bool = True) -> Path:
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=root, check=True)
    tracked = root / "artifact.txt"
    tracked.write_text("before\n", encoding="utf-8")
    if commit:
        subprocess.run(["git", "add", "--", "artifact.txt"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "baseline"], cwd=root, check=True, stdout=subprocess.PIPE
        )
    return tracked


def init_repository_with_submodule(base: Path) -> tuple[Path, Path]:
    child_source = base / "child-source"
    child_source.mkdir()
    child_file = init_repository(child_source)
    child_file.write_text("child baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "--", "artifact.txt"], cwd=child_source, check=True)
    subprocess.run(
        ["git", "commit", "-m", "child content"],
        cwd=child_source,
        check=True,
        stdout=subprocess.PIPE,
    )

    root = base / "parent"
    root.mkdir()
    init_repository(root)
    subprocess.run(
        [
            "git",
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(child_source),
            "deps/child",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-am", "add child"], cwd=root, check=True, stdout=subprocess.PIPE
    )
    return root, root / "deps/child/artifact.txt"


def add_embedded_repository(root: Path) -> Path:
    nested = root / "vendor/nested"
    nested.mkdir(parents=True)
    return init_repository(nested)


def start_test_run(
    root: Path,
    *,
    run_id: str = "test-run",
    write_paths: tuple[str, ...] = ("artifact.txt",),
    implementers: tuple[str, ...] = ("implementer-1",),
):
    record = start_run(
        root,
        "Change the artifact",
        "123",
        run_id,
        acceptance_criteria=parse_criteria(["AC1=Artifact contains the accepted value"]),
        declared_write_set=make_write_set(write_paths, []),
        implementers=list(implementers),
    )
    record_release_impact(
        root,
        run_id,
        level="none",
        reason="Test fixture does not publish a product",
    )
    return record


def approve_current(root: Path, run_id: str = "test-run") -> None:
    record_check(
        root,
        run_id,
        name="unit",
        command="python3 -m unittest",
        status="passed",
        evidence="targeted unit boundary",
        criteria=["AC1"],
    )
    record_verdict(
        root,
        run_id,
        reviewer="verifier-1",
        verdict="approve",
        criteria=["AC1"],
        evidence="Inspected the candidate and raw test result",
    )


class LoopTests(unittest.TestCase):
    def test_three_consecutive_failures_block_without_starting_a_fourth_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_test_run(root)

            self.assertEqual(2, new_attempt(root, "test-run", "first failure")["attempt_id"])
            self.assertEqual(3, new_attempt(root, "test-run", "second failure")["attempt_id"])
            with self.assertRaisesRegex(RuntimeError, "retry ceiling reached after 3"):
                new_attempt(root, "test-run", "third failure")

            _, record = load_run(root, "test-run")
            self.assertEqual("blocked", record["state"])
            self.assertEqual(3, record["attempt_id"])
            self.assertEqual(3, len(record["attempt_history"]))
            self.assertEqual(
                ["failed", "failed", "failed"],
                [item["outcome"] for item in record["attempt_history"]],
            )
            self.assertEqual(3, record["telemetry"]["retry_exhaustion"]["limit"])

    def test_retry_exhaustion_resumes_only_with_human_reviewed_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = init_repository(root)
            start_test_run(root)
            tracked.write_text("preserved partial work\n", encoding="utf-8")
            new_attempt(root, "test-run", "first failure")
            new_attempt(root, "test-run", "second failure")
            with self.assertRaises(RuntimeError):
                new_attempt(root, "test-run", "third failure")
            handoff = {
                "schema_version": "1.0",
                "summary": "Change the recovery approach",
                "failure_boundary": "Three attempts failed at the same deterministic check",
                "preserved_paths": ["artifact.txt"],
                "next_action": "Re-enter understand and inspect the preserved candidate",
            }

            with self.assertRaisesRegex(ValueError, "human:IDENTITY"):
                resume_run(root, "test-run", handoff=handoff, authorized_by="agent:planner")
            with self.assertRaisesRegex(ValueError, "reviewed resume"):
                revise_run(root, "test-run", reason="Bypass reviewed recovery")
            loop_contract = root / "harness/loops/engineering-loop.yaml"
            loop_contract.parent.mkdir(parents=True)
            loop_contract.write_bytes((ROOT / "harness/loops/engineering-loop.yaml").read_bytes())
            with self.assertRaisesRegex(ValueError, "cannot leave terminal state blocked"):
                set_state(root, "test-run", "understand")
            resumed = resume_run(
                root,
                "test-run",
                handoff=handoff,
                authorized_by="human:owner",
            )

            self.assertEqual(2, resumed["revision"])
            self.assertEqual(1, resumed["attempt_id"])
            self.assertEqual("understand", resumed["state"])
            self.assertEqual("preserved partial work\n", tracked.read_text(encoding="utf-8"))
            self.assertEqual("human:owner", resumed["agent_handoffs"][-1]["authorized_by"])

    def test_invalid_resume_handoff_fails_before_mutating_blocked_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_test_run(root)
            new_attempt(root, "test-run", "first failure")
            new_attempt(root, "test-run", "second failure")
            with self.assertRaises(RuntimeError):
                new_attempt(root, "test-run", "third failure")
            before = (root / ".harness/runs/test-run/run.json").read_bytes()

            with self.assertRaisesRegex(ValueError, "forbidden"):
                resume_run(
                    root,
                    "test-run",
                    handoff={
                        "schema_version": "1.0",
                        "summary": "Unsafe handoff",
                        "failure_boundary": "retry",
                        "preserved_paths": [],
                        "next_action": "continue",
                        "transcript": "raw model history",
                    },
                    authorized_by="human:owner",
                )

            self.assertEqual(before, (root / ".harness/runs/test-run/run.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "invalid declared preserved path"):
                resume_run(
                    root,
                    "test-run",
                    handoff={
                        "schema_version": "1.0",
                        "summary": "Escaping handoff",
                        "failure_boundary": "retry",
                        "preserved_paths": ["../outside"],
                        "next_action": "continue",
                    },
                    authorized_by="human:owner",
                )
            self.assertEqual(before, (root / ".harness/runs/test-run/run.json").read_bytes())

    def test_recovery_status_detects_branch_stale_against_integration_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            subprocess.run(["git", "switch", "-c", "feature"], cwd=root, check=True)
            start_test_run(root)
            subprocess.run(["git", "branch", "integration", "main"], cwd=root, check=True)
            subprocess.run(["git", "switch", "integration"], cwd=root, check=True)
            (root / "integration.txt").write_text("advanced\n", encoding="utf-8")
            subprocess.run(["git", "add", "integration.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "advance integration"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
            )
            subprocess.run(["git", "switch", "feature"], cwd=root, check=True)

            status = recovery_status(root, "test-run", "integration")

            self.assertTrue(status["branch_stale"])
            self.assertEqual([], status["scope_violations"])

    def test_context_incomplete_zero_gap_adoption_cannot_report_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            project = {
                "project": {"lifecycle": "new", "status": "active"},
                "open_questions": ["Resolve intent.outcomes"],
            }
            intake = {"missing_essential_fields": ["intent.outcomes"]}
            dispositions = {
                "copied": [],
                "upstream_collisions": [],
                "adoption_deferred": [],
                "merge_required_existing": [],
                "merge_required_missing": [],
            }
            mark_adoption_state(project, intake, dispositions)
            project_path = root / "harness/project.yaml"
            project_path.parent.mkdir()
            project_path.write_text(json.dumps(project), encoding="utf-8")
            start_test_run(root)
            approve_current(root)

            self.assertEqual("complete", intake["adoption"]["reconciliation_status"])
            self.assertEqual("provisional", intake["context_readiness"])
            with self.assertRaisesRegex(ValueError, "harness project is provisional"):
                finish_run(root, "test-run", "reported")

    def test_provisional_adoption_cannot_report_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            project_path = root / "harness/project.yaml"
            project_path.parent.mkdir()
            project_path.write_text(
                json.dumps({"project": {"lifecycle": "adopt", "status": "provisional"}}),
                encoding="utf-8",
            )
            start_test_run(root)
            approve_current(root)

            with self.assertRaisesRegex(ValueError, "harness project is provisional"):
                finish_run(root, "test-run", "reported")

    def test_report_uses_real_git_boundary_and_acceptance_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = init_repository(root)
            record = start_test_run(root)
            tracked.write_text("after\n", encoding="utf-8")
            approve_current(root)

            report_path, evidence_path, finished = finish_run(root, record["run_id"], "reported")

            report = report_path.read_text(encoding="utf-8")
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertIn("Acceptance evidence matrix", report)
            self.assertIn("artifact.txt", report)
            self.assertIn("targeted unit boundary", report)
            self.assertIn("approve by verifier-1", report)
            self.assertIn("Recommended product release impact: none", report)
            self.assertEqual("none", evidence["release_impact"]["level"])
            self.assertEqual([], evidence["boundary"]["scope"]["violations"])
            self.assertEqual("reported", finished["state"])

    def test_cli_records_criterion_linked_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            started = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/loop.py"),
                    "--root",
                    str(root),
                    "start",
                    "--run-id",
                    "cli-run",
                    "--objective",
                    "Exercise CLI parsing",
                    "--criterion",
                    "AC1=CLI records evidence",
                    "--write-path",
                    "artifact.txt",
                    "--implementer",
                    "implementer-1",
                ],
                cwd=ROOT,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )
            self.assertEqual("cli-run", started.stdout.strip())
            recorded = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/loop.py"),
                    "--root",
                    str(root),
                    "record-check",
                    "--run",
                    "cli-run",
                    "--name",
                    "smoke",
                    "--command",
                    "python3 -m unittest",
                    "--status",
                    "passed",
                    "--evidence",
                    "parser boundary",
                    "--criterion",
                    "AC1",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, recorded.returncode, recorded.stdout + recorded.stderr)
            run = json.loads((root / ".harness/runs/cli-run/run.json").read_text(encoding="utf-8"))
            self.assertEqual(["AC1"], run["checks"][0]["criterion_ids"])

    def test_unborn_report_uses_baseline_relative_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                ["git", "init", "-b", "main"], cwd=root, check=True, stdout=subprocess.PIPE
            )
            record = start_run(
                root,
                "Create the initial project",
                None,
                "unborn-run",
                acceptance_criteria=parse_criteria(["AC1=New file exists"]),
                declared_write_set=make_write_set(["new.txt"], []),
                implementers=["implementer-1"],
            )
            (root / "new.txt").write_text("untracked\n", encoding="utf-8")
            record_check(
                root,
                record["run_id"],
                name="exists",
                command="test -f new.txt",
                status="passed",
                evidence="new.txt exists",
                criteria=["AC1"],
            )
            record_release_impact(
                root,
                record["run_id"],
                level="minor",
                reason="The initial public file is a new pre-1.0 capability",
                public_contract_changes=["new.txt"],
            )
            record_verdict(
                root,
                record["run_id"],
                reviewer="verifier-1",
                verdict="approve",
                criteria=["AC1"],
                evidence="Inspected new.txt",
            )

            report_path, _, _ = finish_run(root, record["run_id"], "reported")
            report = report_path.read_text(encoding="utf-8")

            self.assertIn("baseline-relative changed paths", report)
            self.assertNotIn("tracked change entries", report)

    def test_stale_verdict_is_rejected_after_candidate_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = init_repository(root)
            start_test_run(root)
            tracked.write_text("reviewed\n", encoding="utf-8")
            approve_current(root)
            tracked.write_text("changed after review\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "verifier verdict is stale"):
                finish_run(root, "test-run", "reported")

    def test_release_impact_change_invalidates_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_test_run(root)
            approve_current(root)
            record_release_impact(
                root,
                "test-run",
                level="patch",
                reason="Changed after independent review",
                public_contract_changes=["artifact behavior"],
            )

            with self.assertRaisesRegex(ValueError, "verifier verdict is stale"):
                finish_run(root, "test-run", "reported")

    def test_staged_index_change_invalidates_verdict_when_status_and_worktree_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = init_repository(root)
            start_test_run(root)
            tracked.write_text("INDEX-A\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", "artifact.txt"], cwd=root, check=True)
            tracked.write_text("WORKTREE\n", encoding="utf-8")
            approve_current(root)
            status_before = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout

            tracked.write_text("INDEX-C\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", "artifact.txt"], cwd=root, check=True)
            tracked.write_text("WORKTREE\n", encoding="utf-8")
            status_after = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout

            self.assertEqual(status_before, status_after)
            with self.assertRaisesRegex(ValueError, "verifier verdict is stale"):
                finish_run(root, "test-run", "reported")

    def test_hidden_index_paths_cannot_escape_declared_scope(self) -> None:
        for flag in ("--assume-unchanged", "--skip-worktree"):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                init_repository(root)
                hidden = root / "hidden.txt"
                hidden.write_text("hidden baseline\n", encoding="utf-8")
                subprocess.run(["git", "add", "--", "hidden.txt"], cwd=root, check=True)
                subprocess.run(
                    ["git", "commit", "-m", "add hidden path"],
                    cwd=root,
                    check=True,
                    stdout=subprocess.PIPE,
                )
                subprocess.run(["git", "update-index", flag, "hidden.txt"], cwd=root, check=True)
                start_test_run(root, write_paths=("artifact.txt",))
                hidden.write_text(f"changed under {flag}\n", encoding="utf-8")
                approve_current(root)

                ordinary_status = subprocess.run(
                    ["git", "status", "--short"],
                    cwd=root,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                ).stdout
                self.assertNotIn("hidden.txt", ordinary_status)
                with self.assertRaisesRegex(
                    ValueError, "writes outside declared scope: hidden.txt"
                ):
                    finish_run(root, "test-run", "reported")

    def test_assume_unchanged_content_change_invalidates_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            hidden = root / "hidden.txt"
            hidden.write_text("hidden baseline\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", "hidden.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "add hidden path"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "update-index", "--assume-unchanged", "hidden.txt"],
                cwd=root,
                check=True,
            )
            start_test_run(root, write_paths=("hidden.txt",))
            hidden.write_text("reviewed hidden content\n", encoding="utf-8")
            approve_current(root)
            hidden.write_text("changed after review\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "verifier verdict is stale"):
                finish_run(root, "test-run", "reported")

    def test_dirty_submodule_change_invalidates_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, child_file = init_repository_with_submodule(Path(directory))
            child_file.write_text("dirty baseline\n", encoding="utf-8")
            record = start_run(
                root,
                "Change the nested repository",
                "123",
                "submodule-run",
                acceptance_criteria=parse_criteria(["AC1=Nested change is verified"]),
                declared_write_set=make_write_set(["deps/child"], []),
                implementers=["implementer-1"],
            )
            child_file.write_text("reviewed nested content\n", encoding="utf-8")
            record_check(
                root,
                record["run_id"],
                name="nested",
                command="git -C deps/child diff --check",
                status="passed",
                evidence="Nested candidate inspected",
                criteria=["AC1"],
            )
            record_verdict(
                root,
                record["run_id"],
                reviewer="verifier-1",
                verdict="approve",
                criteria=["AC1"],
                evidence="Reviewed nested candidate",
            )
            child_file.write_text("changed after review\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "verifier verdict is stale"):
                finish_run(root, record["run_id"], "reported")

    def test_baseline_dirty_submodule_change_is_a_scope_delta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, child_file = init_repository_with_submodule(Path(directory))
            child_file.write_text("dirty baseline\n", encoding="utf-8")
            start_test_run(root, write_paths=("artifact.txt",))
            child_file.write_text("changed during run\n", encoding="utf-8")
            approve_current(root)

            with self.assertRaisesRegex(ValueError, "writes outside declared scope: deps/child"):
                finish_run(root, "test-run", "reported")

    def test_untracked_embedded_repository_change_invalidates_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            nested_file = add_embedded_repository(root)
            record = start_run(
                root,
                "Change an embedded repository",
                "123",
                "embedded-run",
                acceptance_criteria=parse_criteria(["AC1=Embedded change is verified"]),
                declared_write_set=make_write_set(["vendor/nested"], []),
                implementers=["implementer-1"],
            )
            nested_file.write_text("reviewed nested content\n", encoding="utf-8")
            record_check(
                root,
                record["run_id"],
                name="nested",
                command="git -C vendor/nested diff --check",
                status="passed",
                evidence="Embedded candidate inspected",
                criteria=["AC1"],
            )
            record_verdict(
                root,
                record["run_id"],
                reviewer="verifier-1",
                verdict="approve",
                criteria=["AC1"],
                evidence="Reviewed embedded candidate",
            )
            nested_file.write_text("changed after review\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "verifier verdict is stale"):
                finish_run(root, record["run_id"], "reported")

    def test_baseline_embedded_repository_change_is_a_scope_delta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            nested_file = add_embedded_repository(root)
            start_test_run(root, write_paths=("artifact.txt",))
            nested_file.write_text("changed during run\n", encoding="utf-8")
            approve_current(root)

            with self.assertRaisesRegex(ValueError, "writes outside declared scope: vendor/nested"):
                finish_run(root, "test-run", "reported")

    def test_submodule_ignore_all_cannot_hide_scope_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, child_file = init_repository_with_submodule(Path(directory))
            subprocess.run(
                ["git", "config", "-f", ".gitmodules", "submodule.deps/child.ignore", "all"],
                cwd=root,
                check=True,
            )
            subprocess.run(["git", "add", "--", ".gitmodules"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "ignore child status"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
            )
            start_test_run(root, write_paths=("artifact.txt",))
            child_file.write_text("hidden by configuration\n", encoding="utf-8")
            approve_current(root)

            ordinary_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout
            self.assertNotIn("deps/child", ordinary_status)
            with self.assertRaisesRegex(ValueError, "writes outside declared scope: deps/child"):
                finish_run(root, "test-run", "reported")

    def test_preexisting_dirty_path_is_subtracted_from_run_delta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = init_repository(root)
            tracked.write_text("pre-existing user work\n", encoding="utf-8")
            start_test_run(root, write_paths=("output.txt",))
            (root / "output.txt").write_text("task output\n", encoding="utf-8")
            approve_current(root)

            _, evidence_path, _ = finish_run(root, "test-run", "reported")
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            changed = [item["path"] for item in evidence["boundary"]["scope"]["delta"]]
            self.assertEqual(["output.txt"], changed)
            self.assertEqual([], evidence["boundary"]["scope"]["violations"])

    def test_untracked_write_outside_declared_scope_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = init_repository(root)
            start_test_run(root)
            tracked.write_text("accepted\n", encoding="utf-8")
            (root / "escape.txt").write_text("undeclared\n", encoding="utf-8")
            approve_current(root)

            with self.assertRaisesRegex(ValueError, "writes outside declared scope: escape.txt"):
                finish_run(root, "test-run", "reported")

    def test_untracked_symlink_to_directory_is_fingerprinted_without_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "outside-target"
            target.mkdir()
            (target / "outside.txt").write_text("outside\n", encoding="utf-8")
            root = base / "repository"
            root.mkdir()
            init_repository(root)
            (root / "linked-directory").symlink_to(target, target_is_directory=True)

            record = start_run(
                root,
                "Preserve an existing symlink",
                "123",
                "symlink-run",
                acceptance_criteria=parse_criteria(["AC1=Symlink baseline is captured"]),
                declared_write_set=[],
                implementers=["implementer-1"],
            )

            entry = next(
                item for item in record["baseline"]["entries"] if item["path"] == "linked-directory"
            )
            self.assertEqual("symlink", entry["kind"])
            self.assertNotIn("outside.txt", json.dumps(entry))

    def test_committed_write_outside_declared_scope_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = init_repository(root)
            start_test_run(root)
            tracked.write_text("accepted\n", encoding="utf-8")
            (root / "escape.txt").write_text("undeclared\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", "artifact.txt", "escape.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "candidate"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
            )
            approve_current(root)

            with self.assertRaisesRegex(ValueError, "writes outside declared scope: escape.txt"):
                finish_run(root, "test-run", "reported")

    def test_approval_without_criterion_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_test_run(root)

            with self.assertRaisesRegex(
                ValueError, "lacks passed check evidence for criteria: AC1"
            ):
                record_verdict(
                    root,
                    "test-run",
                    reviewer="verifier-1",
                    verdict="approve",
                    criteria=["AC1"],
                    evidence="Unsupported approval",
                )

    def test_implementer_cannot_record_independent_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_test_run(root)
            record_check(
                root,
                "test-run",
                name="unit",
                command="python3 -m unittest",
                status="passed",
                evidence="targeted unit boundary",
                criteria=["AC1"],
            )

            with self.assertRaisesRegex(ValueError, "recorded as an implementer"):
                record_verdict(
                    root,
                    "test-run",
                    reviewer="implementer-1",
                    verdict="approve",
                    criteria=["AC1"],
                    evidence="Self approval",
                )

    def test_run_requires_an_implementer_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            with self.assertRaisesRegex(ValueError, "implementer identity"):
                start_run(
                    root,
                    "Unowned change",
                    None,
                    "unowned-run",
                    acceptance_criteria=parse_criteria(["AC1=Change is complete"]),
                    declared_write_set=[],
                )

    def test_criterion_waiver_requires_human_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_test_run(root)
            with self.assertRaisesRegex(ValueError, "human:IDENTITY"):
                waive_criterion(
                    root,
                    "test-run",
                    "AC1",
                    waived_by="implementer-1",
                    reason="Agent attempted waiver",
                )

    def test_human_waiver_can_satisfy_a_criterion_without_a_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_test_run(root)
            waive_criterion(
                root,
                "test-run",
                "AC1",
                waived_by="human:owner",
                reason="Owner accepted this boundary as out of scope",
            )
            record_verdict(
                root,
                "test-run",
                reviewer="verifier-1",
                verdict="approve",
                criteria=[],
                evidence="Confirmed the explicit owner waiver and unchanged candidate",
            )
            _, _, finished = finish_run(root, "test-run", "reported")
            self.assertEqual("reported", finished["state"])

    def test_reported_completion_requires_current_release_impact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_run(
                root,
                "Change the artifact",
                "123",
                "impact-run",
                acceptance_criteria=parse_criteria(["AC1=Artifact is accepted"]),
                declared_write_set=make_write_set(["artifact.txt"], []),
                implementers=["implementer-1"],
            )
            record_check(
                root,
                "impact-run",
                name="unit",
                command="python3 -m unittest",
                status="passed",
                evidence="targeted boundary",
                criteria=["AC1"],
            )
            record_verdict(
                root,
                "impact-run",
                reviewer="verifier-1",
                verdict="approve",
                criteria=["AC1"],
                evidence="Reviewed the unchanged fixture",
            )
            with self.assertRaisesRegex(ValueError, "product release impact is not assessed"):
                finish_run(root, "impact-run", "reported")

    def test_revision_invalidates_prior_checks_and_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = init_repository(root)
            start_test_run(root)
            tracked.write_text("reviewed\n", encoding="utf-8")
            approve_current(root)
            revise_run(root, "test-run", reason="Acceptance wording changed")

            with self.assertRaisesRegex(ValueError, "current revision and attempt"):
                finish_run(root, "test-run", "reported")

    def test_revision_invalidates_prior_human_waiver(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_test_run(root)
            waive_criterion(
                root,
                "test-run",
                "AC1",
                waived_by="human:owner",
                reason="Waived only for revision one",
            )
            revise_run(
                root, "test-run", reason="Objective contract changed", objective="New objective"
            )

            with self.assertRaisesRegex(ValueError, "criteria lack current passed checks: AC1"):
                finish_run(root, "test-run", "reported")

    def test_blocked_run_can_report_incomplete_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repository(root)
            start_test_run(root)
            report_path, _, finished = finish_run(root, "test-run", "blocked")
            self.assertTrue(report_path.is_file())
            self.assertEqual("blocked", finished["state"])


if __name__ == "__main__":
    unittest.main()
