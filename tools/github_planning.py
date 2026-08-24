#!/usr/bin/env python3
"""Audit and safely reconcile GitHub planning desired state."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root, run, write_json
except ImportError:  # Direct script execution.
    from common import load_json, repository_root, run, write_json


LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
HEX_COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")
FIELD_TYPES = {"SINGLE_SELECT", "TEXT", "NUMBER", "DATE"}


def valid_login(value: Any) -> bool:
    return isinstance(value, str) and LOGIN.fullmatch(value) is not None


def positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_repository(value: Any) -> bool:
    if not isinstance(value, str) or value.count("/") != 1:
        return False
    owner, name = value.split("/", 1)
    return valid_login(owner) and REPOSITORY_NAME.fullmatch(name) is not None


def validate_contract(config: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(config, dict):
        return ["planning contract must be an object"]
    if config.get("schema_version") != "1.0":
        errors.append("planning schema_version must be 1.0")
    repository = config.get("repository")
    if not isinstance(repository, str) or repository.count("/") != 1:
        errors.append("repository must be OWNER/REPOSITORY")
    elif not valid_repository(repository):
        errors.append("repository must be OWNER/REPOSITORY without whitespace")
    project = config.get("project")
    if not isinstance(project, dict):
        errors.append("project must be an object")
    else:
        for key in ("topology", "owner", "number", "title", "canonical_source", "views"):
            if key not in project:
                errors.append(f"project missing {key}")
        topology = project.get("topology")
        if not isinstance(topology, str) or topology not in {"shared", "dedicated"}:
            errors.append("project topology must be shared or dedicated")
        if not valid_login(project.get("owner")):
            errors.append("project owner must be a valid login")
        if not isinstance(project.get("title"), str) or not project.get("title").strip():
            errors.append("project title must be non-empty")
        number = project.get("number")
        if number is not None and not positive_integer(number):
            errors.append("project number must be null or a positive integer")
        if project.get("topology") == "shared" and number is None:
            errors.append("shared project topology requires a project number")
        canonical = project.get("canonical_source")
        if not isinstance(canonical, dict):
            errors.append("project canonical_source must be an object")
        elif (
            not valid_login(canonical.get("owner"))
            or not positive_integer(canonical.get("number"))
        ):
            errors.append("project canonical_source requires owner and number")
        views = project.get("views")
        if not isinstance(views, list):
            errors.append("project views must be a list")
        else:
            names = [view.get("name") for view in views if isinstance(view, dict)]
            if len(names) != len(views) or any(
                not isinstance(name, str) or not name.strip() for name in names
            ):
                errors.append("every project view requires name")
            elif len(names) != len(set(names)):
                errors.append("project views contain duplicate names")
            for view in views:
                if isinstance(view, dict):
                    layout = view.get("layout")
                    if not isinstance(layout, str) or layout not in {
                        "TABLE_LAYOUT",
                        "BOARD_LAYOUT",
                        "ROADMAP_LAYOUT",
                    }:
                        errors.append(f"invalid layout for Project view {view.get('name')}")
                    if not isinstance(view.get("filter", ""), str):
                        errors.append(f"invalid filter for Project view {view.get('name')}")
        if not isinstance(project.get("allow_unmanaged_views"), bool):
            errors.append("project allow_unmanaged_views must be boolean")
        bootstrap = project.get("bootstrap")
        if not isinstance(bootstrap, dict):
            errors.append("project bootstrap must be an object")
        else:
            method = bootstrap.get("method")
            if not isinstance(method, str) or method not in {"create", "copy"}:
                errors.append("project bootstrap method must be create or copy")
            if not isinstance(bootstrap.get("link_repository", True), bool):
                errors.append("project bootstrap link_repository must be boolean")
            if method == "copy":
                canonical_owner = canonical.get("owner") if isinstance(canonical, dict) else None
                canonical_number = (
                    canonical.get("number") if isinstance(canonical, dict) else None
                )
                if (
                    bootstrap.get("source_owner") != canonical_owner
                    or bootstrap.get("source_number") != canonical_number
                ):
                    errors.append("copy bootstrap source must match project canonical_source")
    for collection, key in (("labels", "name"), ("milestones", "title"), ("fields", "name")):
        items = config.get(collection)
        if not isinstance(items, list):
            errors.append(f"{collection} must be a list")
            continue
        values = [item.get(key) for item in items if isinstance(item, dict)]
        valid_values = len(values) == len(items) and all(
            isinstance(value, str) and bool(value.strip()) for value in values
        )
        if not valid_values:
            errors.append(f"every {collection} entry requires {key}")
        elif len(values) != len(set(values)):
            errors.append(f"{collection} contains duplicate {key} values")
        for item in items:
            if not isinstance(item, dict):
                continue
            if collection == "labels":
                if not isinstance(item.get("color"), str) or not HEX_COLOR.fullmatch(
                    item.get("color", "")
                ):
                    errors.append(f"label {item.get('name')} requires a six-digit hex color")
                if not isinstance(item.get("description"), str):
                    errors.append(f"label {item.get('name')} description must be a string")
            elif collection == "milestones":
                if not isinstance(item.get("description"), str):
                    errors.append(f"milestone {item.get('title')} description must be a string")
            else:
                data_type = item.get("data_type")
                if not isinstance(data_type, str) or data_type not in FIELD_TYPES:
                    errors.append(f"field {item.get('name')} has invalid data_type")
                options = item.get("options")
                if data_type == "SINGLE_SELECT":
                    if not isinstance(options, list) or not options:
                        errors.append(
                            f"single-select field {item.get('name')} requires options"
                        )
                    elif not all(
                        isinstance(option, str)
                        and bool(option.strip())
                        and "," not in option
                        for option in options
                    ):
                        errors.append(
                            f"single-select field {item.get('name')} has invalid options"
                        )
                    elif len(options) != len(set(options)):
                        errors.append(
                            f"single-select field {item.get('name')} has duplicate options"
                        )
                elif options not in (None, []):
                    errors.append(
                        f"non-single-select field {item.get('name')} must not define options"
                    )
    return errors


def flatten_pages(value: Any, *, collection: str = "paginated response") -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RuntimeError(f"{collection} must be a JSON array")
    if not value:
        return []
    if all(isinstance(item, dict) for item in value):
        return value
    if all(isinstance(page, list) for page in value):
        flattened = [item for page in value for item in page]
        if all(isinstance(item, dict) for item in flattened):
            return flattened
    raise RuntimeError(f"{collection} contains an unexpected JSON shape")


def group_live_identities(
    items: Any,
    *,
    key: str,
    collection: str,
    managed_names: set[str],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    conflicts: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return groups, [{"reason": f"live {collection} must be a list"}]
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key]:
            conflicts.append(
                {"reason": f"live {collection} entry {index} has no valid {key}", "current": item}
            )
            continue
        groups.setdefault(item[key], []).append(item)
    for name, matches in groups.items():
        if name in managed_names and len(matches) > 1:
            conflicts.append(
                {
                    "name": name,
                    "reason": f"live {collection} contains {len(matches)} entries named {name}",
                    "current": matches,
                }
            )
    return groups, conflicts


def validate_live_fields(fields: Any) -> list[dict[str, Any]]:
    if not isinstance(fields, list):
        raise RuntimeError("gh project field-list fields must be a list")
    for index, field in enumerate(fields):
        if (
            not isinstance(field, dict)
            or not nonempty_string(field.get("id"))
            or not nonempty_string(field.get("name"))
            or not nonempty_string(field.get("type"))
        ):
            raise RuntimeError(f"gh project field-list entry {index} is invalid")
        options = field.get("options")
        if options is not None:
            if not isinstance(options, list):
                raise RuntimeError(f"gh project field-list entry {index} options are invalid")
            for option_index, option in enumerate(options):
                if (
                    not isinstance(option, dict)
                    or not nonempty_string(option.get("id"))
                    or not nonempty_string(option.get("name"))
                ):
                    raise RuntimeError(
                        f"gh project field-list entry {index} option {option_index} is invalid"
                    )
    return fields


def validate_live_labels(labels: Any) -> list[dict[str, Any]]:
    if not isinstance(labels, list):
        raise RuntimeError("GitHub labels must be a list")
    for index, label in enumerate(labels):
        if (
            not isinstance(label, dict)
            or not nonempty_string(label.get("name"))
            or not isinstance(label.get("color"), str)
            or not re.fullmatch(r"[0-9A-Fa-f]{6}", label["color"])
            or label.get("description") is not None
            and not isinstance(label.get("description"), str)
        ):
            raise RuntimeError(f"GitHub labels entry {index} is invalid")
    return labels


def validate_live_milestones(milestones: Any) -> list[dict[str, Any]]:
    if not isinstance(milestones, list):
        raise RuntimeError("GitHub milestones must be a list")
    for index, milestone in enumerate(milestones):
        if (
            not isinstance(milestone, dict)
            or not positive_integer(milestone.get("number"))
            or not nonempty_string(milestone.get("title"))
            or milestone.get("description") is not None
            and not isinstance(milestone.get("description"), str)
        ):
            raise RuntimeError(f"GitHub milestones entry {index} is invalid")
    return milestones


def graphql_data(payload: Any, *, operation: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RuntimeError(f"GitHub returned an invalid GraphQL response for {operation}")
    if "errors" in payload and payload["errors"] != []:
        raise RuntimeError(f"GitHub returned GraphQL errors for {operation}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"GitHub returned no GraphQL data for {operation}")
    return data


def mutation_view_id(payload: Any, *, mutation: str) -> str:
    data = graphql_data(payload, operation=mutation)
    mutation_payload = data.get(mutation) if isinstance(data, dict) else None
    view = (
        mutation_payload.get("projectV2View")
        if isinstance(mutation_payload, dict)
        else None
    )
    view_id = view.get("id") if isinstance(view, dict) else None
    if not nonempty_string(view_id):
        raise RuntimeError(f"GitHub returned an invalid Project view from {mutation}")
    return view_id


def parse_json_values(output: str, *, command: str) -> Any:
    """Parse one JSON value or the whitespace-separated values emitted by gh pagination."""
    decoder = json.JSONDecoder()
    values: list[Any] = []
    cursor = 0
    while cursor < len(output):
        while cursor < len(output) and output[cursor].isspace():
            cursor += 1
        if cursor == len(output):
            break
        try:
            value, cursor = decoder.raw_decode(output, cursor)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"gh returned invalid JSON for {command}") from exc
        values.append(value)
    if not values:
        raise RuntimeError(f"gh returned no JSON for {command}")
    return values[0] if len(values) == 1 else values


def gh_json(root: Path, *args: str) -> Any:
    result = run(["gh", *args], cwd=root)
    return parse_json_values(result.stdout, command=f"gh {' '.join(args)}")


PROJECT_VIEW_QUERY = """
query($owner: String!, $number: Int!) {
  OWNER_KIND(login: $owner) {
    projectV2(number: $number) {
      id
      number
      title
      views(first: 100) {
        nodes { id number name layout filter }
        pageInfo { hasNextPage }
      }
      repositories(first: 100) {
        nodes { nameWithOwner }
        pageInfo { hasNextPage }
      }
    }
  }
}
"""


def read_project(root: Path, *, owner: str, number: int) -> dict[str, Any]:
    if not valid_login(owner) or not positive_integer(number):
        raise ValueError("Project owner and number must be a valid login and positive integer")
    summary = gh_json(
        root,
        "project",
        "view",
        str(number),
        "--owner",
        owner,
        "--format",
        "json",
    )
    if not isinstance(summary, dict):
        raise RuntimeError("gh project view returned an invalid JSON shape")
    owner_data = summary.get("owner")
    if not isinstance(owner_data, dict):
        raise RuntimeError("gh project view returned an invalid owner")
    owner_kind = owner_data.get("type")
    if not isinstance(owner_kind, str) or owner_kind not in {"User", "Organization"}:
        raise RuntimeError(f"unsupported Project owner type: {owner_kind}")
    if (
        not nonempty_string(owner_data.get("login"))
        or owner_data["login"].lower() != owner.lower()
    ):
        raise RuntimeError("gh project view returned a different Project owner")
    query = PROJECT_VIEW_QUERY.replace(
        "OWNER_KIND", "user" if owner_kind == "User" else "organization"
    )
    payload = gh_json(
        root,
        "api",
        "graphql",
        "-F",
        f"owner={owner}",
        "-F",
        f"number={number}",
        "-f",
        f"query={query}",
    )
    data = graphql_data(payload, operation=f"Project {owner}/{number}")
    owner_payload = (
        data.get("user" if owner_kind == "User" else "organization")
        if isinstance(data, dict)
        else None
    )
    project = owner_payload.get("projectV2") if isinstance(owner_payload, dict) else None
    if not isinstance(project, dict):
        raise RuntimeError(f"Project {owner}/{number} was not returned by GitHub")
    if (
        not nonempty_string(project.get("id"))
        or not positive_integer(project.get("number"))
        or project.get("number") != number
        or not nonempty_string(project.get("title"))
    ):
        raise RuntimeError(f"Project {owner}/{number} returned an invalid identity")
    for connection in ("views", "repositories"):
        value = project.get(connection)
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("nodes"), list)
            or not isinstance(value.get("pageInfo"), dict)
            or not isinstance(value["pageInfo"].get("hasNextPage"), bool)
        ):
            raise RuntimeError(f"Project {connection} returned an invalid connection")
        if value["pageInfo"]["hasNextPage"]:
            raise RuntimeError(f"Project {connection} exceed the supported 100-entry audit bound")
    for index, view in enumerate(project["views"]["nodes"]):
        if (
            not isinstance(view, dict)
            or not nonempty_string(view.get("id"))
            or not positive_integer(view.get("number"))
            or not nonempty_string(view.get("name"))
            or not isinstance(view.get("layout"), str)
            or view.get("layout")
            not in {"TABLE_LAYOUT", "BOARD_LAYOUT", "ROADMAP_LAYOUT"}
            or view.get("filter") is not None
            and not isinstance(view.get("filter"), str)
        ):
            raise RuntimeError(f"Project views entry {index} is invalid")
    for index, repository in enumerate(project["repositories"]["nodes"]):
        if not isinstance(repository, dict) or not valid_repository(
            repository.get("nameWithOwner")
        ):
            raise RuntimeError(f"Project repositories entry {index} is invalid")
    return {
        "id": project["id"],
        "number": project["number"],
        "title": project["title"],
        "owner_type": owner_kind,
        "views": project.get("views", {}).get("nodes", []),
        "repositories": project.get("repositories", {}).get("nodes", []),
    }


def read_live(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    repository = config["repository"]
    if repository == "OWNER/REPOSITORY":
        raise ValueError("replace OWNER/REPOSITORY before live GitHub operations")
    identity = run(["gh", "api", "user", "--jq", ".login"], cwd=root).stdout.strip()
    actual_repo = run(
        ["gh", "repo", "view", repository, "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        cwd=root,
    ).stdout.strip()
    if actual_repo.lower() != repository.lower():
        raise RuntimeError(f"resolved repository {actual_repo}, expected {repository}")
    label_pages = gh_json(
        root,
        "api",
        "--paginate",
        f"repos/{repository}/labels?per_page=100",
    )
    milestone_pages = gh_json(
        root,
        "api",
        "--paginate",
        f"repos/{repository}/milestones?state=all&per_page=100",
    )
    fields: list[dict[str, Any]] = []
    project_state: dict[str, Any] = {}
    project_number = config["project"].get("number")
    if project_number is not None:
        field_data = gh_json(
            root,
            "project",
            "field-list",
            str(project_number),
            "--owner",
            config["project"]["owner"],
            "--format",
            "json",
        )
        if not isinstance(field_data, dict):
            raise RuntimeError("gh project field-list returned an invalid JSON shape")
        fields = validate_live_fields(field_data.get("fields"))
        project_state = read_project(
            root,
            owner=config["project"]["owner"],
            number=project_number,
        )
    labels = validate_live_labels(
        flatten_pages(label_pages, collection="GitHub labels")
    )
    milestones = validate_live_milestones(
        flatten_pages(milestone_pages, collection="GitHub milestones")
    )
    return {
        "authenticated_login": identity,
        "repository": actual_repo,
        "labels": labels,
        "milestones": milestones,
        "fields": fields,
        "project": project_state,
        "project_audited": project_number is not None,
    }


def diff_state(config: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    desired_label_names = {item["name"] for item in config.get("labels", [])}
    desired_milestone_titles = {item["title"] for item in config.get("milestones", [])}
    desired_field_names = {item["name"] for item in config.get("fields", [])}
    desired_view_names = {
        item["name"] for item in config.get("project", {}).get("views", [])
    }
    live_labels, label_conflicts = group_live_identities(
        live.get("labels", []),
        key="name",
        collection="labels",
        managed_names=desired_label_names,
    )
    live_milestones, milestone_conflicts = group_live_identities(
        live.get("milestones", []),
        key="title",
        collection="milestones",
        managed_names=desired_milestone_titles,
    )
    live_fields, _ = group_live_identities(
        live.get("fields", []),
        key="name",
        collection="Project fields",
        managed_names=desired_field_names,
    )

    labels_create: list[dict[str, Any]] = []
    labels_update: list[dict[str, Any]] = []
    for desired in config.get("labels", []):
        matches = live_labels.get(desired["name"], [])
        if not matches:
            labels_create.append(desired)
        elif len(matches) > 1:
            continue
        else:
            current = matches[0]
            if current.get("color", "").lower() != desired.get("color", "").lower() or (
                current.get("description") or ""
            ) != (desired.get("description") or ""):
                labels_update.append({"desired": desired, "current": current})

    milestones_create: list[dict[str, Any]] = []
    milestones_update: list[dict[str, Any]] = []
    for desired in config.get("milestones", []):
        matches = live_milestones.get(desired["title"], [])
        if not matches:
            milestones_create.append(desired)
        elif len(matches) > 1:
            continue
        else:
            current = matches[0]
            if (current.get("description") or "") != (desired.get("description") or ""):
                milestones_update.append({"desired": desired, "current": current})

    project_audited = bool(live.get("project_audited"))
    live_project = live.get("project", {})
    missing_fields = (
        [desired for desired in config.get("fields", []) if not live_fields.get(desired["name"])]
        if project_audited
        else []
    )
    mismatched_fields = (
        field_mismatches(config.get("fields", []), live.get("fields", []))
        if project_audited
        else []
    )
    live_views, view_conflicts = group_live_identities(
        live_project.get("views", []),
        key="name",
        collection="Project views",
        managed_names=desired_view_names,
    )
    missing_views = []
    mismatched_views = [
        {
            "name": conflict.get("name", "<invalid>"),
            "reasons": [conflict["reason"]],
            "current": conflict.get("current"),
        }
        for conflict in view_conflicts
    ]
    if project_audited:
        for desired in config.get("project", {}).get("views", []):
            matches = live_views.get(desired["name"], [])
            if not matches:
                missing_views.append(desired)
                continue
            if len(matches) > 1:
                continue
            current = matches[0]
            reasons = []
            if current.get("layout") != desired.get("layout"):
                reasons.append(
                    f"layout is {current.get('layout')}, expected {desired.get('layout')}"
                )
            if (current.get("filter") or "") != (desired.get("filter") or ""):
                reasons.append(
                    f"filter is {current.get('filter')!r}, expected {desired.get('filter')!r}"
                )
            if reasons:
                mismatched_views.append(
                    {"name": desired["name"], "reasons": reasons, "current": current}
                )
    configured_names = desired_view_names
    unmanaged_views = [
        item
        for item in live_project.get("views", [])
        if isinstance(item, dict) and item.get("name") not in configured_names
    ]
    disallowed_unmanaged_views = (
        []
        if config.get("project", {}).get("allow_unmanaged_views", True)
        else unmanaged_views
    )
    linked_repositories = {
        item.get("nameWithOwner", "").lower()
        for item in live_project.get("repositories", [])
    }
    link_required = bool(
        config.get("project", {}).get("bootstrap", {}).get("link_repository", True)
    )
    repository_link_missing = bool(
        project_audited
        and link_required
        and config.get("repository", "").lower() not in linked_repositories
    )
    title_mismatch = bool(
        project_audited
        and live_project.get("title") != config.get("project", {}).get("title")
    )
    warnings: list[str] = []
    if not project_audited:
        warnings.append("project number is null; Project fields and views were not audited")
    else:
        warnings.append(
            "Missing fields and basic saved views can be created; "
            "existing field/view mismatches require manual reconciliation"
        )
        if unmanaged_views and config.get("project", {}).get("allow_unmanaged_views", True):
            warnings.append("unmanaged Project views are preserved")
        elif disallowed_unmanaged_views:
            warnings.append("unmanaged Project views are disallowed but will not be deleted")
    return {
        "labels": {
            "create": labels_create,
            "update": labels_update,
            "identity_conflicts": label_conflicts,
        },
        "milestones": {
            "create": milestones_create,
            "update": milestones_update,
            "identity_conflicts": milestone_conflicts,
        },
        "project": {
            "title_mismatch": title_mismatch,
            "missing_fields": missing_fields,
            "mismatched_fields": mismatched_fields,
            "missing_views": missing_views,
            "mismatched_views": mismatched_views,
            "unmanaged_views": unmanaged_views,
            "disallowed_unmanaged_views": disallowed_unmanaged_views,
            "repository_link_missing": repository_link_missing,
            "configured_views": config.get("project", {}).get("views", []),
        },
        "warnings": warnings,
    }


def has_drift(diff: dict[str, Any]) -> bool:
    return any(
        (
            diff["labels"]["create"],
            diff["labels"]["update"],
            diff["labels"]["identity_conflicts"],
            diff["milestones"]["create"],
            diff["milestones"]["update"],
            diff["milestones"]["identity_conflicts"],
            diff["project"]["missing_fields"],
            diff["project"]["mismatched_fields"],
            diff["project"]["missing_views"],
            diff["project"]["mismatched_views"],
            diff["project"]["disallowed_unmanaged_views"],
            diff["project"]["title_mismatch"],
            diff["project"]["repository_link_missing"],
        )
    )


def project_bootstrap_plan(config: dict[str, Any]) -> dict[str, Any]:
    project = config["project"]
    bootstrap = project.get("bootstrap", {"method": "create", "link_repository": True})
    method = bootstrap.get("method", "create")
    errors: list[str] = []
    if method not in {"create", "copy"}:
        errors.append(f"unsupported project bootstrap method: {method}")
    if method == "copy" and (
        not bootstrap.get("source_owner") or bootstrap.get("source_number") is None
    ):
        errors.append("copy method requires source_owner and source_number")
    actions: list[dict[str, Any]] = []
    if project.get("number") is None:
        actions.append(
            {
                "action": method,
                "title": project["title"],
                "owner": project["owner"],
                "source_owner": bootstrap.get("source_owner"),
                "source_number": bootstrap.get("source_number"),
            }
        )
    actions.extend({"action": "ensure-field", **field} for field in config.get("fields", []))
    if bootstrap.get("link_repository", True):
        actions.append({"action": "link-repository", "repository": config["repository"]})
    actions.extend({"action": "ensure-view", **view} for view in project.get("views", []))
    return {"ok": not errors, "errors": errors, "dry_run": True, "actions": actions}


def create_project_view(root: Path, *, project_id: str, view: dict[str, Any]) -> str:
    if not nonempty_string(project_id):
        raise ValueError("Project ID must be a non-empty string")
    layout = view.get("layout") if isinstance(view, dict) else None
    if (
        not isinstance(view, dict)
        or not nonempty_string(view.get("name"))
        or not isinstance(layout, str)
        or layout not in {"TABLE_LAYOUT", "BOARD_LAYOUT", "ROADMAP_LAYOUT"}
        or not isinstance(view.get("filter", ""), str)
    ):
        raise ValueError("Project view must have a valid name, layout, and filter")
    create_query = """
mutation($project: ID!, $name: String!, $layout: ProjectV2ViewLayout!) {
  createProjectV2View(input: {projectId: $project, name: $name, layout: $layout}) {
    projectV2View { id }
  }
}
"""
    created = gh_json(
        root,
        "api",
        "graphql",
        "-F",
        f"project={project_id}",
        "-F",
        f"name={view['name']}",
        "-F",
        f"layout={view['layout']}",
        "-f",
        f"query={create_query}",
    )
    view_id = mutation_view_id(created, mutation="createProjectV2View")
    desired_filter = view.get("filter") or ""
    if desired_filter:
        update_query = """
mutation($view: ID!, $filter: String!) {
  updateProjectV2View(input: {viewId: $view, filter: $filter}) {
    projectV2View { id }
  }
}
"""
        updated = gh_json(
            root,
            "api",
            "graphql",
            "-F",
            f"view={view_id}",
            "-F",
            f"filter={desired_filter}",
            "-f",
            f"query={update_query}",
        )
        updated_id = mutation_view_id(updated, mutation="updateProjectV2View")
        if updated_id != view_id:
            raise RuntimeError("GitHub updated a different Project view")
    return view_id


def field_mismatches(
    desired_fields: list[dict[str, Any]],
    live_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    desired_names = {item["name"] for item in desired_fields}
    live, conflicts = group_live_identities(
        live_fields,
        key="name",
        collection="Project fields",
        managed_names=desired_names,
    )
    expected_types = {
        "SINGLE_SELECT": "ProjectV2SingleSelectField",
        "TEXT": "ProjectV2Field",
        "NUMBER": "ProjectV2Field",
        "DATE": "ProjectV2Field",
    }
    mismatches: list[dict[str, Any]] = [
        {
            "name": conflict.get("name", "<invalid>"),
            "reasons": [conflict["reason"]],
            "current": conflict.get("current"),
        }
        for conflict in conflicts
    ]
    for desired in desired_fields:
        matches = live.get(desired["name"], [])
        if not matches or len(matches) > 1:
            continue
        current = matches[0]
        reasons = []
        expected_type = expected_types.get(desired["data_type"])
        if expected_type and current.get("type") != expected_type:
            reasons.append(f"type is {current.get('type')}, expected {expected_type}")
        if desired["data_type"] == "SINGLE_SELECT":
            actual_options = [item.get("name") for item in current.get("options", [])]
            if actual_options != desired.get("options", []):
                reasons.append(
                    f"options are {actual_options}, expected {desired.get('options', [])}"
                )
        if reasons:
            mismatches.append({"name": desired["name"], "reasons": reasons, "current": current})
    return mismatches


def bootstrap_project(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    contract_errors = validate_contract(config)
    if contract_errors:
        raise ValueError("invalid planning contract: " + "; ".join(contract_errors))
    project = config["project"]
    bootstrap = project.get("bootstrap", {"method": "create", "link_repository": True})
    repository = config["repository"]
    if repository == "OWNER/REPOSITORY":
        raise ValueError("replace OWNER/REPOSITORY before live GitHub operations")
    actual_repository = run(
        [
            "gh",
            "repo",
            "view",
            repository,
            "--json",
            "nameWithOwner",
            "--jq",
            ".nameWithOwner",
        ],
        cwd=root,
    ).stdout.strip()
    if actual_repository.lower() != repository.lower():
        raise RuntimeError(f"resolved repository {actual_repository}, expected {repository}")
    number = project.get("number")
    operations: list[str] = []
    created_project = False
    if number is None:
        method = bootstrap.get("method", "create")
        if method == "copy":
            created = gh_json(
                root,
                "project",
                "copy",
                str(bootstrap["source_number"]),
                "--source-owner",
                bootstrap["source_owner"],
                "--target-owner",
                project["owner"],
                "--title",
                project["title"],
                "--format",
                "json",
            )
        else:
            created = gh_json(
                root,
                "project",
                "create",
                "--owner",
                project["owner"],
                "--title",
                project["title"],
                "--format",
                "json",
            )
        number = created.get("number") if isinstance(created, dict) else None
        if not positive_integer(number):
            raise RuntimeError("created Project response did not include a valid number")
        created_project = True
        verb = "copied" if method == "copy" else "created"
        operations.append(f"{verb} Project #{number}")

    project_state = read_project(root, owner=project["owner"], number=number)
    if created_project:
        project["number"] = number
        write_json(root / ".github/planning.json", config)

    fields_data = gh_json(
        root,
        "project",
        "field-list",
        str(number),
        "--owner",
        project["owner"],
        "--format",
        "json",
    )
    if not isinstance(fields_data, dict):
        raise RuntimeError("gh project field-list returned an invalid JSON shape")
    fields = validate_live_fields(fields_data.get("fields"))
    existing = {
        item["name"]
        for item in fields
    }
    for field in config.get("fields", []):
        if field["name"] in existing:
            continue
        argv = [
            "gh",
            "project",
            "field-create",
            str(number),
            "--owner",
            project["owner"],
            "--name",
            field["name"],
            "--data-type",
            field["data_type"],
            "--format",
            "json",
        ]
        if field["data_type"] == "SINGLE_SELECT":
            argv.extend(["--single-select-options", ",".join(field.get("options", []))])
        created_field_result = run(argv, cwd=root)
        created_field = parse_json_values(
            created_field_result.stdout,
            command=f"gh project field-create {number}",
        )
        validated_field = validate_live_fields([created_field])[0]
        if validated_field["name"] != field["name"]:
            raise RuntimeError("gh project field-create returned a different field")
        operations.append(f"created Project field {field['name']}")
    linked = {
        item.get("nameWithOwner", "").lower()
        for item in project_state.get("repositories", [])
    }
    if bootstrap.get("link_repository", True) and repository.lower() not in linked:
        run(
            [
                "gh",
                "project",
                "link",
                str(number),
                "--owner",
                project["owner"],
                "--repo",
                repository,
            ],
            cwd=root,
        )
        operations.append(f"linked Project #{number} to {repository}")
    post_fields = gh_json(
        root,
        "project",
        "field-list",
        str(number),
        "--owner",
        project["owner"],
        "--format",
        "json",
    )
    if not isinstance(post_fields, dict):
        raise RuntimeError("gh project field-list returned an invalid JSON shape")
    final_fields = validate_live_fields(post_fields.get("fields"))
    names = {item["name"] for item in final_fields}
    missing = [field["name"] for field in config.get("fields", []) if field["name"] not in names]
    mismatched = field_mismatches(config.get("fields", []), final_fields)
    view_names = {item.get("name") for item in project_state.get("views", [])}
    for view in project.get("views", []):
        if view["name"] in view_names:
            continue
        create_project_view(root, project_id=project_state["id"], view=view)
        operations.append(f"created Project view {view['name']}")
    final_project = read_project(root, owner=project["owner"], number=number)
    final_diff = diff_state(
        config,
        {
            "labels": [],
            "milestones": [],
            "fields": final_fields,
            "project": final_project,
            "project_audited": True,
        },
    )["project"]
    unresolved_project = any(
        (
            final_diff["title_mismatch"],
            final_diff["missing_fields"],
            final_diff["mismatched_fields"],
            final_diff["missing_views"],
            final_diff["mismatched_views"],
            final_diff["repository_link_missing"],
        )
    )
    return {
        "ok": not missing and not mismatched and not unresolved_project,
        "project_number": number,
        "operations": operations,
        "missing_fields": missing,
        "mismatched_fields": mismatched,
        "project_diff": final_diff,
        "manual_views": final_diff["mismatched_views"],
    }


def apply_supported(root: Path, config: dict[str, Any], diff: dict[str, Any]) -> list[str]:
    repository = config["repository"]
    operations: list[str] = []
    for desired in diff["labels"]["create"] + [
        item["desired"] for item in diff["labels"]["update"]
    ]:
        run(
            [
                "gh",
                "label",
                "create",
                desired["name"],
                "--repo",
                repository,
                "--color",
                desired["color"],
                "--description",
                desired.get("description", ""),
                "--force",
            ],
            cwd=root,
        )
        operations.append(f"reconciled label {desired['name']}")

    for desired in diff["milestones"]["create"]:
        run(
            [
                "gh",
                "api",
                "--method",
                "POST",
                f"repos/{repository}/milestones",
                "-f",
                f"title={desired['title']}",
                "-f",
                f"description={desired.get('description', '')}",
            ],
            cwd=root,
        )
        operations.append(f"created milestone {desired['title']}")

    for item in diff["milestones"]["update"]:
        desired = item["desired"]
        number = item["current"]["number"]
        run(
            [
                "gh",
                "api",
                "--method",
                "PATCH",
                f"repos/{repository}/milestones/{number}",
                "-f",
                f"description={desired.get('description', '')}",
            ],
            cwd=root,
        )
        operations.append(f"updated milestone {desired['title']}")
    project_diff = diff["project"]
    if config["project"].get("number") is not None and any(
        (
            project_diff["missing_fields"],
            project_diff["missing_views"],
            project_diff["repository_link_missing"],
        )
    ):
        project_result = bootstrap_project(root, config)
        operations.extend(project_result["operations"])
    return operations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit")
    audit.add_argument("--offline", action="store_true")
    apply = subparsers.add_parser("apply")
    apply.add_argument("--yes", action="store_true", help="Perform supported live writes")
    bootstrap = subparsers.add_parser("bootstrap-project")
    bootstrap.add_argument(
        "--yes", action="store_true", help="Create or copy and configure a Project"
    )
    args = parser.parse_args()

    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    try:
        config = load_json(root / ".github/planning.json")
        errors = validate_contract(config)
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, indent=2))
            return 1
        if args.command == "audit" and args.offline:
            warnings = []
            if config["repository"] == "OWNER/REPOSITORY":
                warnings.append("template placeholders remain; live audit is not available")
            print(json.dumps({"ok": True, "mode": "offline", "warnings": warnings}, indent=2))
            return 0

        if args.command == "bootstrap-project":
            plan = project_bootstrap_plan(config)
            if not plan["ok"]:
                print(json.dumps(plan, indent=2))
                return 1
            if not args.yes:
                print(json.dumps(plan, indent=2))
                print("No GitHub writes performed. Re-run with --yes after reviewing the plan.")
                return 0
            result = bootstrap_project(root, config)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1

        live = read_live(root, config)
        diff = diff_state(config, live)
        if args.command == "audit":
            print(
                json.dumps(
                    {
                        "ok": not has_drift(diff),
                        "mode": "live",
                        "identity": live["authenticated_login"],
                        "repository": live["repository"],
                        "diff": diff,
                    },
                    indent=2,
                )
            )
            return 1 if has_drift(diff) else 0

        print(json.dumps({"dry_run": not args.yes, "diff": diff}, indent=2))
        if not args.yes:
            print("No GitHub writes performed. Re-run with --yes after reviewing the plan.")
            return 0
        operations = apply_supported(root, config, diff)
        post = diff_state(config, read_live(root, config))
        print(json.dumps({"operations": operations, "post_apply_diff": post}, indent=2))
        return 1 if has_drift(post) else 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
