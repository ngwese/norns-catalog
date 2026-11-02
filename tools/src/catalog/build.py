from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from catalog.jsonutil import load_json, load_schema, validate_against_schema, write_json
from catalog.templating import render_json_template


def load_entries(entries_dir: Path) -> list[dict[str, Any]]:
    if not entries_dir.is_dir():
        raise FileNotFoundError(f"entries directory not found: {entries_dir}")

    entries: list[dict[str, Any]] = []
    for path in sorted(entries_dir.glob("*.json")):
        entry = load_json(path)
        if not isinstance(entry, dict):
            raise ValueError(f"entry must be a JSON object: {path}")
        entries.append(entry)

    return entries


def _entry_tags(entry: dict[str, Any]) -> set[str]:
    tags = entry.get("tags") or []
    if not isinstance(tags, list):
        raise ValueError(f"entry tags must be a list: {entry.get('project_name', '<unknown>')}")
    return {tag for tag in tags if isinstance(tag, str)}


def filter_entries(
    entries: list[dict[str, Any]],
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[dict[str, Any]]:
    filtered = entries

    if include:
        include_tags = set(include)
        filtered = [
            entry for entry in filtered if include_tags.intersection(_entry_tags(entry))
        ]

    if exclude:
        exclude_tags = set(exclude)
        filtered = [
            entry for entry in filtered if not exclude_tags.intersection(_entry_tags(entry))
        ]

    return filtered


def sort_entries_by_name(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda entry: entry.get("project_name", "").casefold())


def build_catalog(
    config_path: Path,
    entries_dir: Path,
    template_path: Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> dict[str, Any]:
    config = load_json(config_path)

    catalog_name = config.get("catalog_name")
    if not catalog_name:
        raise ValueError(f"config missing catalog_name: {config_path}")

    schema_ref = config.get("catalog_schema")
    if not schema_ref:
        raise ValueError(f"config missing catalog_schema: {config_path}")

    entries = sort_entries_by_name(
        filter_entries(load_entries(entries_dir), include=include, exclude=exclude)
    )

    catalog = render_json_template(
        template_path,
        catalog_name=catalog_name,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        entries=entries,
    )

    schema = load_schema(schema_ref)
    validate_against_schema(catalog, schema, "catalog")
    return catalog


def write_catalog(catalog: dict[str, Any], output: Path | None) -> None:
    write_json(catalog, output)
