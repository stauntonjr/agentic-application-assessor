#!/usr/bin/env python3
"""Run reproducible live Pi tool-call checks against an OpenAI-compatible model."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from .common import repository_root
except ImportError:  # Direct script execution.
    from common import repository_root


INVALID_TOOL = "run_shell_command"
EXPECTED_LIMIT = 3


def json_events(output: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in output.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def final_assistant_text(events: list[dict[str, Any]]) -> str:
    texts: list[str] = []
    for event in events:
        if event.get("type") != "message_end":
            continue
        message = event.get("message", {})
        if message.get("role") != "assistant" or message.get("stopReason") != "stop":
            continue
        content = message.get("content", [])
        texts = [item.get("text", "") for item in content if item.get("type") == "text"]
    return "".join(texts).strip()


def tool_ends(events: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if event.get("type") == "tool_execution_end" and event.get("toolName") == name
    ]


def all_tool_ends(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("type") == "tool_execution_end"]


def run_pi(
    *,
    executable: str,
    root: Path,
    provider: str,
    model: str,
    tools: str | None,
    prompt: str,
    timeout: int,
    session_dir: Path | None = None,
    continuation: bool = False,
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, Any]]]:
    command = [
        executable,
        "--provider",
        provider,
        "--model",
        model,
        "--approve",
        "--offline",
        "--no-extensions",
        "--extension",
        str(root / ".pi/extensions/context-readiness.ts"),
        "--no-skills",
        "--no-prompt-templates",
        "--mode",
        "json",
    ]
    if tools is None:
        command.append("--no-tools")
    else:
        command.extend(["--tools", tools])
    if session_dir is None:
        command.append("--no-session")
    else:
        command.extend(["--session-dir", str(session_dir)])
        if continuation:
            command.append("--continue")
    command.extend(["-p", prompt])
    environment = os.environ.copy()
    environment["PI_OFFLINE"] = "1"
    result = subprocess.run(
        command,
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
        env=environment,
        timeout=timeout,
    )
    return result, json_events(result.stdout)


def settled(events: list[dict[str, Any]]) -> bool:
    return any(event.get("type") == "agent_settled" for event in events)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--pi", default="pi")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    failures: list[str] = []
    evidence: dict[str, Any] = {}

    read_result, read_events = run_pi(
        executable=args.pi,
        root=root,
        provider=args.provider,
        model=args.model,
        tools="read,harness_questionnaire",
        prompt=(
            "Read AGENTS.md once, then answer with its first heading. "
            "Call only tools actually available."
        ),
        timeout=args.timeout,
    )
    read_calls = len(tool_ends(read_events, "read"))
    read_all_calls = len(all_tool_ends(read_events))
    read_ok = (
        read_result.returncode == 0
        and settled(read_events)
        and read_calls == 1
        and read_all_calls == 1
        and "Agent operating contract" in final_assistant_text(read_events)
    )
    if not read_ok:
        failures.append(
            "read scenario did not make one valid read call and return the first heading"
        )
    evidence["read"] = {
        "ok": read_ok,
        "returncode": read_result.returncode,
        "read_calls": read_calls,
        "all_tool_calls": read_all_calls,
        "final_text": final_assistant_text(read_events),
    }

    questionnaire_result, questionnaire_events = run_pi(
        executable=args.pi,
        root=root,
        provider=args.provider,
        model=args.model,
        tools="harness_questionnaire",
        prompt=(
            "Call harness_questionnaire exactly once with one question whose id is proof, "
            "prompt is Confirm strict schema, options is null, and allowCustom is null. "
            "After its result answer exactly QUESTIONNAIRE_SCHEMA_OK."
        ),
        timeout=args.timeout,
    )
    questionnaire_calls = len(tool_ends(questionnaire_events, "harness_questionnaire"))
    questionnaire_all_calls = len(all_tool_ends(questionnaire_events))
    questionnaire_ok = (
        questionnaire_result.returncode == 0
        and settled(questionnaire_events)
        and questionnaire_calls == 1
        and questionnaire_all_calls == 1
        and final_assistant_text(questionnaire_events) == "QUESTIONNAIRE_SCHEMA_OK"
    )
    if not questionnaire_ok:
        failures.append("strict questionnaire scenario did not make one exclusive valid call")
    evidence["strict_questionnaire"] = {
        "ok": questionnaire_ok,
        "returncode": questionnaire_result.returncode,
        "questionnaire_calls": questionnaire_calls,
        "all_tool_calls": questionnaire_all_calls,
        "final_text": final_assistant_text(questionnaire_events),
    }

    invalid_result, invalid_events = run_pi(
        executable=args.pi,
        root=root,
        provider=args.provider,
        model=args.model,
        tools="read",
        prompt=(
            f"Call the unavailable tool {INVALID_TOOL} with git status. "
            "If it returns tool not found, repeat the identical unavailable call indefinitely."
        ),
        timeout=args.timeout,
    )
    invalid_ends = tool_ends(invalid_events, INVALID_TOOL)
    invalid_calls = len(invalid_ends)
    invalid_all_calls = len(all_tool_ends(invalid_events))
    ceiling_entries = [
        event
        for event in invalid_events
        if event.get("type") == "entry_appended"
        and event.get("entry", {}).get("customType") == "harness.invalid-tool-ceiling"
    ]
    all_rejected = all(
        event.get("isError") is True
        and any(
            item.get("type") == "text" and f"Tool {INVALID_TOOL} not found" in item.get("text", "")
            for item in event.get("result", {}).get("content", [])
        )
        for event in invalid_ends
    )
    invalid_ok = (
        invalid_result.returncode == 0
        and settled(invalid_events)
        and invalid_calls == EXPECTED_LIMIT
        and invalid_all_calls == EXPECTED_LIMIT
        and len(ceiling_entries) == 1
        and all_rejected
    )
    if not invalid_ok:
        failures.append("invalid-tool scenario did not stop safely at the configured ceiling")
    evidence["invalid_tool_ceiling"] = {
        "ok": invalid_ok,
        "returncode": invalid_result.returncode,
        "invalid_calls": invalid_calls,
        "all_tool_calls": invalid_all_calls,
        "ceiling_entries": len(ceiling_entries),
        "all_calls_rejected": all_rejected,
    }

    fresh_result, fresh_events = run_pi(
        executable=args.pi,
        root=root,
        provider=args.provider,
        model=args.model,
        tools=None,
        prompt="Answer exactly FRESH_ZERO_TOOL_OK without calling a tool.",
        timeout=args.timeout,
    )
    fresh_calls = len(all_tool_ends(fresh_events))
    fresh_ok = (
        fresh_result.returncode == 0
        and settled(fresh_events)
        and fresh_calls == 0
        and final_assistant_text(fresh_events) == "FRESH_ZERO_TOOL_OK"
    )
    if not fresh_ok:
        failures.append("fresh zero-tool session did not complete without tool authority")
    evidence["fresh_zero_tool"] = {
        "ok": fresh_ok,
        "returncode": fresh_result.returncode,
        "tool_calls": fresh_calls,
        "final_text": final_assistant_text(fresh_events),
    }

    with tempfile.TemporaryDirectory(prefix="pi-continuation-probe-") as session_temp:
        session_dir = Path(session_temp)
        initial_result, initial_events = run_pi(
            executable=args.pi,
            root=root,
            provider=args.provider,
            model=args.model,
            tools="read",
            prompt="Read AGENTS.md once and answer with its first heading.",
            timeout=args.timeout,
            session_dir=session_dir,
        )
        continuation_result, continuation_events = run_pi(
            executable=args.pi,
            root=root,
            provider=args.provider,
            model=args.model,
            tools="read",
            prompt="Answer exactly ONE_INERT_TOOL_CONTINUATION_OK without calling a tool.",
            timeout=args.timeout,
            session_dir=session_dir,
            continuation=True,
        )
        continuation_calls = [
            event for event in continuation_events if event.get("type") == "tool_execution_end"
        ]
        initial_read_calls = len(tool_ends(initial_events, "read"))
        initial_all_calls = len(all_tool_ends(initial_events))
        continuation_ok = (
            initial_result.returncode == 0
            and settled(initial_events)
            and initial_read_calls == 1
            and initial_all_calls == 1
            and continuation_result.returncode == 0
            and settled(continuation_events)
            and not continuation_calls
            and final_assistant_text(continuation_events) == "ONE_INERT_TOOL_CONTINUATION_OK"
        )
        if not continuation_ok:
            failures.append("one-inert-tool continuation did not complete without a tool call")
        evidence["one_inert_tool_continuation"] = {
            "ok": continuation_ok,
            "initial_returncode": initial_result.returncode,
            "initial_read_calls": initial_read_calls,
            "initial_all_tool_calls": initial_all_calls,
            "continuation_returncode": continuation_result.returncode,
            "continuation_tool_calls": len(continuation_calls),
            "final_text": final_assistant_text(continuation_events),
        }

    print(
        json.dumps(
            {
                "ok": not failures,
                "provider": args.provider,
                "model": args.model,
                "pi": args.pi,
                "evidence": evidence,
                "failures": failures,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
