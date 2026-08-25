"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .assess import assess
from .errors import AssessmentError
from .questionnaire import (
    generate_questionnaire,
    reconcile_questionnaire,
    render_questionnaire_json,
)
from .render import render_json, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-application-assessor",
        description="Compile a deterministic, read-only application assessment.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    assess_command = commands.add_parser(
        "assess", help="Assess one exact local Git repository root"
    )
    assess_command.add_argument("target", type=Path)
    assess_command.add_argument("--context", required=True, type=Path)
    assess_command.add_argument(
        "--auditor-report",
        type=Path,
        help="Import one Agentic Repo Auditor 0.1.0/schema-1.2 JSON report",
    )
    assess_command.add_argument("--format", choices=("json", "markdown"), default="markdown")
    questionnaire = commands.add_parser(
        "questionnaire", help="Generate a deterministic gap-only context questionnaire"
    )
    questionnaire.add_argument("target", type=Path)
    questionnaire.add_argument("--context", type=Path, help="Accepted context to treat as settled")
    reconcile = commands.add_parser(
        "reconcile", help="Reconcile questionnaire answers into draft or accepted context"
    )
    reconcile.add_argument("target", type=Path)
    reconcile.add_argument("--questionnaire", required=True, type=Path)
    reconcile.add_argument("--answers", required=True, type=Path)
    reconcile.add_argument(
        "--context", type=Path, help="Exact accepted context bound by questionnaire"
    )
    reconcile.add_argument("--accept-by", help="Owner identity explicitly accepting the context")
    reconcile.add_argument("--accepted-on", help="Owner acceptance date in YYYY-MM-DD form")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "assess":
            report = assess(args.target, args.context, args.auditor_report)
            output = render_json(report) if args.format == "json" else render_markdown(report)
        elif args.command == "questionnaire":
            output = render_questionnaire_json(generate_questionnaire(args.target, args.context))
        else:
            output = render_questionnaire_json(
                reconcile_questionnaire(
                    args.target,
                    args.questionnaire,
                    args.answers,
                    args.context,
                    accept_by=args.accept_by,
                    accepted_on=args.accepted_on,
                )
            )
    except AssessmentError as exc:
        print(f"agentic-application-assessor: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(output)
    return 0
