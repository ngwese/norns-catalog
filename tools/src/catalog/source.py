from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from catalog.jsonutil import load_json, load_schema, validate_against_schema, write_json
from catalog.templating import render_json_template


GITHUB_SSH = re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?$")
GITHUB_SSH_URL = re.compile(r"^ssh://git@github\.com/(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?$")


def _run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def git_origin_url(repo_root: Path) -> str:
    try:
        return _run_git(repo_root, "remote", "get-url", "origin")
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"unable to read git origin in {repo_root}") from exc


def parse_github_repo(origin: str) -> tuple[str, str]:
    origin = origin.strip()

    match = GITHUB_SSH.match(origin) or GITHUB_SSH_URL.match(origin)
    if match:
        return match.group("owner"), match.group("repo")

    parsed = urlparse(origin)
    if parsed.scheme in {"http", "https"} and parsed.netloc in {"github.com", "www.github.com"}:
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2:
            return parts[0], parts[1].removesuffix(".git")

    raise ValueError(f"unsupported git origin (expected GitHub): {origin}")


def catalog_download_url(repo_root: Path, catalog_name: str) -> str:
    owner, repo = parse_github_repo(git_origin_url(repo_root))
    return f"https://{owner}.github.io/{repo}/{catalog_name}.json"


def build_source(
    config_path: Path,
    repo_root: Path,
    template_path: Path,
) -> dict[str, Any]:
    config = load_json(config_path)

    catalog_name = config.get("catalog_name")
    if not catalog_name:
        raise ValueError(f"config missing catalog_name: {config_path}")

    schema_ref = config.get("source_schema")
    if not schema_ref:
        raise ValueError(f"config missing source_schema: {config_path}")

    download_url = catalog_download_url(repo_root, catalog_name)
    source = render_json_template(
        template_path,
        catalog_name=catalog_name,
        download_url=download_url,
    )

    schema = load_schema(schema_ref)
    validate_against_schema(source, schema, "source")
    return source


def write_source(source: dict[str, Any], output: Path | None) -> None:
    write_json(source, output)
