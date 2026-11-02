from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from catalog.build import build_catalog


class CatalogCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._catalog: dict[str, Any] | None = None
        self._payload = b"{}\n"
        self._error: str | None = "catalog has not been built yet"

    def update(self, catalog: dict[str, Any]) -> None:
        payload = (json.dumps(catalog, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        with self._lock:
            self._catalog = catalog
            self._payload = payload
            self._error = None

    def snapshot(self) -> tuple[bytes | None, str | None, str | None]:
        with self._lock:
            if self._catalog is None:
                return None, self._error or "catalog unavailable", None
            name = self._catalog.get("catalog_name")
            catalog_name = name if isinstance(name, str) else None
            return self._payload, None, catalog_name


def _is_json_path(path: str | bytes | None) -> bool:
    if path is None:
        return False
    return Path(os.fsdecode(path)).suffix.lower() == ".json"


class EntriesReloadHandler(FileSystemEventHandler):
    def __init__(self, rebuild: Callable[[], None], debounce_seconds: float = 0.25) -> None:
        super().__init__()
        self._rebuild = rebuild
        self._debounce_seconds = debounce_seconds
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _schedule(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_seconds, self._rebuild)
            self._timer.daemon = True
            self._timer.start()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        relevant = _is_json_path(event.src_path)
        if event.event_type == "moved":
            relevant = relevant or _is_json_path(getattr(event, "dest_path", None))

        if relevant:
            self._schedule()


def make_handler(cache: CatalogCache) -> type[BaseHTTPRequestHandler]:
    class CatalogRequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            path = urlparse(self.path).path.rstrip("/") or "/"
            payload, error, catalog_name = cache.snapshot()

            allowed = {"/", "/catalog.json"}
            if catalog_name:
                allowed.add(f"/{catalog_name}.json")

            if path not in allowed:
                body = b'{"error":"not found"}\n'
                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if error is not None or payload is None:
                message = error or "catalog unavailable"
                body = (json.dumps({"error": message}, indent=2) + "\n").encode("utf-8")
                self.send_response(503)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

    return CatalogRequestHandler


def serve_catalog(
    *,
    host: str,
    port: int,
    config_path: Path,
    entries_dir: Path,
    template_path: Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> None:
    if not entries_dir.is_dir():
        raise FileNotFoundError(f"entries directory not found: {entries_dir}")

    cache = CatalogCache()

    def rebuild() -> None:
        try:
            catalog = build_catalog(
                config_path=config_path,
                entries_dir=entries_dir,
                template_path=template_path,
                include=include,
                exclude=exclude,
            )
            cache.update(catalog)
            count = len(catalog.get("entries", []))
            print(f"catalog ready ({count} entries)", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - keep serving last good catalog if possible
            print(f"error rebuilding catalog: {exc}", file=sys.stderr)

    rebuild()
    if cache.snapshot()[0] is None:
        raise RuntimeError("initial catalog build failed")

    observer = Observer()
    handler = EntriesReloadHandler(rebuild)
    observer.schedule(handler, str(entries_dir), recursive=False)
    observer.start()

    server = ThreadingHTTPServer((host, port), make_handler(cache))
    print(f"serving catalog on http://{host}:{port}/", file=sys.stderr)
    print(f"watching {entries_dir}", file=sys.stderr)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", file=sys.stderr)
    finally:
        observer.stop()
        observer.join(timeout=5)
        server.server_close()
