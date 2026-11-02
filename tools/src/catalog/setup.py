from __future__ import annotations

from pathlib import Path

from catalog.jsonutil import write_json
from catalog.templating import render_json_template


def setup_config(
    catalog_name: str,
    config_path: Path,
    template_path: Path,
) -> Path:
    if not catalog_name.strip():
        raise ValueError("catalog name must not be empty")

    config = render_json_template(template_path, catalog_name=catalog_name.strip())
    write_json(config, config_path)
    return config_path
