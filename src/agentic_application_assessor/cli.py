"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .assess import assess
from .errors import AssessmentError
from .render import render_json, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-application-assessor",
        description="Compile a deterministic, read-only application assessment.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("assess", help="Assess one exact local Git repository root")
    command.add_argument("target", type=Path)
    command.add_argument("--context", required=True, type=Path)
    command.add_argument("--format", choices=("json", "markdown"), default="markdown")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = assess(args.target, args.context)
    except AssessmentError as exc:
        print(f"agentic-application-assessor: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render_json(report) if args.format == "json" else render_markdown(report))
    return 0
