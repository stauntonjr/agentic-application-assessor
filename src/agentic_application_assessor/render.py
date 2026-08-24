"""Deterministic JSON and Markdown renderers."""

from __future__ import annotations

import json

from .model import Report


def render_json(report: Report) -> str:
    return json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n"


def render_markdown(report: Report) -> str:
    payload = report.as_dict()
    target = payload["target"]
    lines = [
        "# Application assessment",
        "",
        f"- Tool: `{payload['tool']['name']} {payload['tool']['version']}`",
        f"- Report schema: `{payload['schema_version']}`",
        f"- Target: `{target['name']}` at `{target['revision']}`",
        f"- Branch: `{target['branch']}`",
        f"- Dirty outer worktree: `{'yes' if target['dirty'] else 'no'}`",
        f"- State identity: `{target['state_id']}`",
        "",
        "## Executive findings",
        "",
    ]
    for claim in payload["claims"]:
        lines.append(
            f"- **{claim['id']}** [{claim['origin']}; {claim['status']}]: {claim['statement']}"
        )
    lines.extend(["", "## Evidence coverage", "", "| Kind | Count |", "|---|---:|"])
    lines.extend(f"| {kind} | {count} |" for kind, count in payload["coverage"].items())
    lines.extend(["", "## Contradictions", ""])
    if payload["contradictions"]:
        lines.extend(
            f"- **{item['id']}** [{item['origin']}] `{item['source']}`: {item['statement']}"
            for item in payload["contradictions"]
        )
    else:
        lines.append("- None detected at the inspected boundary.")
    lines.extend(["", "## Unknowns and limits", ""])
    lines.extend(
        f"- **{item['id']}** [{item['origin']}] `{item['source']}`: {item['statement']}"
        for item in payload["unknowns"]
    )
    lines.extend(["", "## Evidence index", ""])
    for item in payload["evidence"]:
        digest = f"; sha256 `{item['sha256']}`" if item["sha256"] else ""
        lines.append(
            f"- `{item['id']}` [{item['origin']}] `{item['source']}`: {item['value']}{digest}"
        )
    lines.extend(
        [
            "",
            "This report does not claim runtime coverage, security approval, compliance, release readiness, or intended architecture beyond accepted declarations.",
            "",
        ]
    )
    return "\n".join(lines)
