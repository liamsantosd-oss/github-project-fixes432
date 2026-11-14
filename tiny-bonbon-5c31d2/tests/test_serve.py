"""Regression tests for archived page routing and the local static server."""
from __future__ import annotations

from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import serve  # noqa: E402


class QuietSnapshotHandler(serve.SnapshotHandler):
    def log_message(self, _format, *_args):
        pass


class SnapshotRouteTests(unittest.TestCase):
    def test_root_and_home_serve_landing_capture(self):
        self.assertEqual(serve.SnapshotHandler.snapshot_path("/"), ROOT / "home.html")
        self.assertEqual(serve.SnapshotHandler.snapshot_path("/home"), ROOT / "home.html")
        self.assertEqual(serve.SnapshotHandler.snapshot_path("/upgrades/robux"), ROOT / "index.html")

    def test_catalog_page_enhancement_is_injected_without_mutating_archive(self):
        original = (ROOT / "catalog.html").read_bytes()
        enhanced = serve.SnapshotHandler._with_catalog_tools(original)
        self.assertIn(b"/assets/local-catalog.js", enhanced)
        self.assertIn(b"marketplace-offer-modal-dialog-content", enhanced)
        self.assertIn(b"MutationObserver", enhanced)
        self.assertIn(b"overlay||node", enhanced)
        self.assertIn(b"You unlocked 50% off", enhanced)  # Original snapshot remains unchanged; injected script removes the offer at runtime.
        self.assertEqual((ROOT / "catalog.html").read_bytes(), original)
        self.assertEqual(serve.SnapshotHandler._with_catalog_tools(enhanced), enhanced)
        helper = (ROOT / "assets" / "local-catalog.js").read_text(encoding="utf-8")
        self.assertIn("offline-catalog-search", helper)
        self.assertIn("offline-catalog-sort", helper)

    def test_catalog_aliases_resolve_to_capture(self):
        for path in ("/catalog", "/catalog/", "/catalog.html"):
            with self.subTest(path=path):
                self.assertEqual(serve.SnapshotHandler.snapshot_path(path), ROOT / "catalog.html")

    def test_nested_and_locale_routes_resolve_to_snapshots(self):
        cases = {
            "/charts/trending-in/action": "charts-trending-in-action.html",
            "/charts/top-trending": "charts-top-trending.html",
            "/de/charts/trending-in/rpg": "de-charts-trending-in-rpg.html",
            "/ar/login": "ar-login.html",
        }
        for path, filename in cases.items():
            with self.subTest(path=path):
                self.assertEqual(serve.SnapshotHandler.snapshot_path(path), ROOT / filename)

    def test_encoded_traversal_is_rejected(self):
        for path in ("/../README.md", "/%2e%2e/README.md", "/charts/../../README.md"):
            with self.subTest(path=path):
                self.assertIsNone(serve.SnapshotHandler.snapshot_path(path))

    def test_unknown_snapshot_is_not_mapped(self):
        self.assertIsNone(serve.SnapshotHandler.snapshot_path("/not-a-captured-page"))


class SnapshotHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietSnapshotHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_extensionless_routes_and_assets_serve(self):
        for path, expected in (
            ("/", b"meta name=\"pd-saved-from\" content=\"https://www.roblox.com/\""),
            ("/upgrades/robux", b"Buy Robux"),
            ("/catalog?category=all", b"Shop Roblox Catalog"),
            ("/assets/local-catalog.js", b"offline-catalog-search"),
            ("/assets/local-catalog.css", b"offline-catalog-controls"),
            ("/charts/trending-in/action", b"Trending Action Games"),
            ("/assets/r-get-sorts-zyfmyv1d.js", b"__pdR"),
        ):
            with self.subTest(path=path):
                with urlopen(self.base_url + path, timeout=10) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn(expected, response.read())

    def test_missing_page_is_404(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base_url + "/not-a-captured-page", timeout=10)
        self.assertEqual(error.exception.code, 404)

    def test_gzip_and_head_requests(self):
        request = Request(self.base_url + "/catalog", headers={"Accept-Encoding": "gzip"})
        with urlopen(request, timeout=10) as response:
            self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
            self.assertGreater(int(response.headers["Content-Length"]), 0)
        request = Request(self.base_url + "/catalog", method="HEAD")
        with urlopen(request, timeout=10) as response:
            self.assertEqual(response.status, 200)
            self.assertGreater(int(response.headers["Content-Length"]), 0)


class ApiReplayAssetTests(unittest.TestCase):
    def test_pages_install_offline_fetch_and_xhr_replay(self):
        for page in ("index.html", "catalog.html", "charts.html"):
            with self.subTest(page=page):
                html = (ROOT / page).read_text(encoding="utf-8", errors="replace")
                self.assertIn("data-pd-replay", html)
                self.assertIn("window.fetch = function", html)
                self.assertIn("XMLHttpRequest", html)
                self.assertIn("connect-src 'none'", html)

    def test_captured_api_fixture_is_present(self):
        fixture = ROOT / "assets" / "r-get-sorts-zyfmyv1d.js"
        self.assertTrue(fixture.is_file())
        self.assertIn("apis.roblox.com/explore-api/v1/get-sorts", fixture.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
