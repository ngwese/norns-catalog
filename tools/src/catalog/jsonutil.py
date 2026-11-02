from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from jsonschema import Draft7Validator


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


@lru_cache(maxsize=8)
def load_schema(schema_ref: str) -> dict[str, Any]:
    if schema_ref.startswith(("http://", "https://")):
        with urlopen(schema_ref) as response:  # noqa: S310 - schema URL comes from project config
            return json.load(response)

    return load_json(Path(schema_ref))


def validate_against_schema(document: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if not errors:
        return

    lines = [f"{label} failed schema validation:"]
    for error in errors:
        location = ".".join(str(p) for p in error.path) or "<root>"
        lines.append(f"  - {location}: {error.message}")
    raise ValueError("\n".join(lines))


def write_json(document: dict[str, Any], output: Path | None) -> None:
    payload = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    if output is None:
        try:
            sys.stdout.write(payload)
        except BrokenPipeError:
            # Allow callers like `catalog build | head` without a traceback.
            sys.stdout.close()
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload)
