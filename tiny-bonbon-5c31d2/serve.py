#!/usr/bin/env python3
"""Serve the archived Roblox snapshot with offline routing and local catalog tools."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import gzip
import mimetypes
import re

ROOT = Path(__file__).resolve().parent
COMPRESSIBLE = {
    "text/html",
    "text/css",
    "text/javascript",
    "application/javascript",
    "application/json",
    "image/svg+xml",
}
CATALOG_PAGES = {"catalog.html", "ar-catalog.html", "de-catalog.html"}
CATALOG_SCRIPT = b'<script src="/assets/local-catalog.js" defer></script>'
CATALOG_DISCOUNT_SCRIPT = b'<script>(function(){function removeOffers(){document.querySelectorAll(".marketplace-offer-modal-dialog-content").forEach(function(node){var overlay=node.closest(".foundation-web-dialog-overlay");(overlay||node).remove()});document.querySelectorAll(".marketplace-offer-banner").forEach(function(node){node.remove()})}removeOffers();new MutationObserver(removeOffers).observe(document.documentElement,{childList:true,subtree:true})}());</script>'


class SnapshotHandler(SimpleHTTPRequestHandler):
    """Serve captured files and map familiar extensionless URLs to snapshots."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Cache-Control",
            "public, max-age=31536000, immutable" if "/assets/" in self.path else "no-cache",
        )
        self.send_header("Vary", "Accept-Encoding")
        super().end_headers()

    @staticmethod
    def snapshot_path(path: str) -> Path | None:
        """Resolve a URL path to a captured page without allowing path traversal."""
        decoded = unquote(path)
        normalized = re.sub(r"/+", "/", decoded).rstrip("/") or "/"
        parts = normalized.strip("/").split("/") if normalized != "/" else []
        if any(part in (".", "..") for part in parts):
            return None

        aliases = {
            "/": "home.html",
            "/home": "home.html",
            "/catalog": "catalog.html",
            "/catalog.html": "catalog.html",
            "/upgrades/robux": "index.html",
            "/upgrades/robux.html": "index.html",
        }
        if normalized in aliases:
            return ROOT / aliases[normalized]

        # Captures are stored as <original-route>.html. The joined form also
        # maps nested and localized original URLs such as /de/charts/... .
        candidates = []
        if parts:
            candidates.append(ROOT.joinpath(*parts).with_suffix(".html"))
            candidates.append(ROOT / ("-".join(parts) + ".html"))
        for candidate in candidates:
            try:
                candidate.resolve().relative_to(ROOT)
            except ValueError:
                continue
            if candidate.is_file():
                return candidate

        # Nested captured routes retain their original relative asset and HTML
        # links. Resolve those against the archive root so scripts and links do
        # not accidentally request /charts/.../assets/... and fail to load.
        if "assets" in parts:
            asset_index = len(parts) - 1 - parts[::-1].index("assets")
            asset = ROOT.joinpath(*parts[asset_index:])
            try:
                asset.resolve().relative_to(ROOT / "assets")
            except ValueError:
                return None
            if asset.is_file():
                return asset
        if parts and parts[-1].endswith(".html"):
            root_page = ROOT / parts[-1]
            if root_page.is_file():
                return root_page
        return None

    @staticmethod
    def _with_catalog_tools(source: bytes) -> bytes:
        """Add the standalone local-only interaction layer to captured catalogs."""
        if CATALOG_SCRIPT in source and CATALOG_DISCOUNT_SCRIPT in source:
            return source
        if CATALOG_DISCOUNT_SCRIPT not in source:
            source = re.sub(
                rb"</head\s*>", CATALOG_DISCOUNT_SCRIPT + b"</head>", source, count=1, flags=re.IGNORECASE
            )
        if CATALOG_SCRIPT not in source:
            source = re.sub(
                rb"</body\s*>",
                CATALOG_SCRIPT + b"</body>",
                source,
                count=1,
                flags=re.IGNORECASE,
            )
        return source

    def send_head(self):
        parsed = urlsplit(self.path)
        requested = self.snapshot_path(parsed.path)
        if requested is None:
            requested = Path(self.translate_path(self.path))

        if requested.is_dir():
            requested = requested / "index.html"
        try:
            stat = requested.stat()
            source = requested.open("rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        content_type = mimetypes.guess_type(str(requested))[0] or "application/octet-stream"
        can_compress = content_type.split(";", 1)[0] in COMPRESSIBLE
        wants_gzip = "gzip" in self.headers.get("Accept-Encoding", "").lower()
        body = None

        # The capture's scripts expect Roblox services, but the offline archive
        # can still make its saved marketplace listings searchable and sortable.
        if requested.name.lower() in CATALOG_PAGES:
            with source:
                body = self._with_catalog_tools(source.read())

        if can_compress and wants_gzip:
            try:
                if body is None:
                    with source:
                        body = source.read()
                body = gzip.compress(body, compresslevel=6, mtime=0)
            except OSError:
                self.send_error(500, "Could not read file")
                return None
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return None

        length = len(body) if body is not None else stat.st_size
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
        self.end_headers()
        if self.command == "HEAD":
            if body is None:
                source.close()
            return None
        if body is not None:
            self.wfile.write(body)
            return None
        return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=3000, help="port (default: 3000)")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), SnapshotHandler)
    print(f"Serving {ROOT} at http://{args.host}:{args.port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
