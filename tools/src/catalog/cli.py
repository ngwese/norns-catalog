from __future__ import annotations

import argparse
import sys
from pathlib import Path

from catalog.build import build_catalog, write_catalog
from catalog.serve import serve_catalog
from catalog.setup import setup_config
from catalog.source import build_source, write_source


def _repo_root() -> Path:
    # src/catalog/cli.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3]


def _tools_root() -> Path:
    # src/catalog/cli.py -> tools/ is parents[2]
    return Path(__file__).resolve().parents[2]


def _default_template(name: str) -> Path:
    return _tools_root() / "templates" / name


def _root_config_path() -> Path:
    return _repo_root() / "config.json"


def _require_root_config() -> int | None:
    config_path = _root_config_path()
    if config_path.is_file():
        return None

    print(
        f'error: missing {config_path.name} at the repository root.\n'
        f'Run "./catalog.sh setup --name <catalog-name>" '
        f'(or ".\\catalog.ps1 setup --name <catalog-name>" on Windows) to create it.',
        file=sys.stderr,
    )
    return 1


def setup_command(args: argparse.Namespace) -> int:
    config_path = _root_config_path()
    template_path = (
        Path(args.template) if args.template else _default_template("config.json.j2")
    )

    try:
        setup_config(
            catalog_name=args.name,
            config_path=config_path,
            template_path=template_path,
        )
    except Exception as exc:  # noqa: BLE001 - surface setup errors to the CLI
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {config_path}")
    return 0


def build_command(args: argparse.Namespace) -> int:
    if (status := _require_root_config()) is not None:
        return status

    config_path = Path(args.config) if args.config else _root_config_path()
    entries_dir = Path(args.entries) if args.entries else config_path.parent / "entries"
    template_path = (
        Path(args.template) if args.template else _default_template("catalog.json.j2")
    )

    try:
        catalog = build_catalog(
            config_path=config_path,
            entries_dir=entries_dir,
            template_path=template_path,
            include=args.include,
            exclude=args.exclude,
        )
    except Exception as exc:  # noqa: BLE001 - surface build errors to the CLI
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else None
    write_catalog(catalog, output)
    return 0


def build_source_command(args: argparse.Namespace) -> int:
    if (status := _require_root_config()) is not None:
        return status

    repo_root = _repo_root()
    config_path = Path(args.config) if args.config else _root_config_path()
    template_path = (
        Path(args.template) if args.template else _default_template("source.json.j2")
    )

    try:
        source = build_source(
            config_path=config_path,
            repo_root=repo_root,
            template_path=template_path,
        )
    except Exception as exc:  # noqa: BLE001 - surface build errors to the CLI
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else None
    write_source(source, output)
    return 0


def serve_command(args: argparse.Namespace) -> int:
    if (status := _require_root_config()) is not None:
        return status

    config_path = Path(args.config) if args.config else _root_config_path()
    entries_dir = Path(args.entries) if args.entries else config_path.parent / "entries"
    template_path = (
        Path(args.template) if args.template else _default_template("catalog.json.j2")
    )

    try:
        serve_catalog(
            host=args.host,
            port=args.port,
            config_path=config_path,
            entries_dir=entries_dir,
            template_path=template_path,
            include=args.include,
            exclude=args.exclude,
        )
    except Exception as exc:  # noqa: BLE001 - surface serve errors to the CLI
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="catalog", description="Norns catalog tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser(
        "setup",
        help="Render config.json for the repository from the config template",
    )
    setup_parser.add_argument(
        "--name",
        required=True,
        help="Catalog name written into config.json",
    )
    setup_parser.add_argument(
        "--template",
        help="Path to the Jinja2 config template (defaults to tools/templates/config.json.j2)",
    )
    setup_parser.set_defaults(func=setup_command)

    build_parser = subparsers.add_parser(
        "build",
        help="Assemble entries into a catalog and validate against the configured schema",
    )
    build_parser.add_argument(
        "output",
        nargs="?",
        help="Optional output file path; writes to stdout when omitted",
    )
    build_parser.add_argument(
        "--config",
        help="Path to config.json (defaults to the repository root config.json)",
    )
    build_parser.add_argument(
        "--entries",
        help="Directory containing entry JSON files (defaults to <config-dir>/entries)",
    )
    build_parser.add_argument(
        "--template",
        help="Path to the Jinja2 catalog template (defaults to tools/templates/catalog.json.j2)",
    )
    build_parser.add_argument(
        "--include",
        action="append",
        default=None,
        metavar="TAG",
        help="Only include entries that have any of these tags (repeatable; default: all entries)",
    )
    build_parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="TAG",
        help="Exclude entries that have any of these tags (repeatable; applied after --include)",
    )
    build_parser.set_defaults(func=build_command)

    build_source_parser = subparsers.add_parser(
        "build-source",
        help="Build a maiden catalog source file from git origin and validate it",
    )
    build_source_parser.add_argument(
        "output",
        nargs="?",
        help="Optional output file path; writes to stdout when omitted",
    )
    build_source_parser.add_argument(
        "--config",
        help="Path to config.json (defaults to the repository root config.json)",
    )
    build_source_parser.add_argument(
        "--template",
        help="Path to the Jinja2 source template (defaults to tools/templates/source.json.j2)",
    )
    build_source_parser.set_defaults(func=build_source_command)

    serve_parser = subparsers.add_parser(
        "serve",
        help="Build the catalog, serve it over HTTP, and rebuild when entries change",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    serve_parser.add_argument(
        "--config",
        help="Path to config.json (defaults to the repository root config.json)",
    )
    serve_parser.add_argument(
        "--entries",
        help="Directory containing entry JSON files (defaults to <config-dir>/entries)",
    )
    serve_parser.add_argument(
        "--template",
        help="Path to the Jinja2 catalog template (defaults to tools/templates/catalog.json.j2)",
    )
    serve_parser.add_argument(
        "--include",
        action="append",
        default=None,
        metavar="TAG",
        help="Only include entries that have any of these tags (repeatable; default: all entries)",
    )
    serve_parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="TAG",
        help="Exclude entries that have any of these tags (repeatable; applied after --include)",
    )
    serve_parser.set_defaults(func=serve_command)

    args = parser.parse_args(argv)
    return args.func(args)
