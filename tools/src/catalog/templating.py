from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def _tojson(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def render_json_template(template_path: Path, **context: Any) -> dict[str, Any]:
    if not template_path.is_file():
        raise FileNotFoundError(f"template not found: {template_path}")

    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    env.filters["tojson"] = _tojson

    rendered = env.get_template(template_path.name).render(**context)
    document = json.loads(rendered)
    if not isinstance(document, dict):
        raise ValueError(f"template must render a JSON object: {template_path}")
    return document
