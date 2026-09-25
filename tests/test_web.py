"""
Unit tests for the web router and endpoint dispatching.
Zero external pip dependencies.
"""

import unittest
from web.router import Router

class DummyHandler:
    def __init__(self, path):
        self.path = path
        self.status = None
        self.headers = {}
        self.body = None

    def send_response(self, code):
        self.status = code

    def send_header(self, k, v):
        self.headers[k] = v

    def end_headers(self):
        pass

    class WFile:
        def __init__(self):
            self.data = b""
        def write(self, b):
            self.data += b

    @property
    def wfile(self):
        if not hasattr(self, "_wfile"):
            self._wfile = self.WFile()
        return self._wfile

class TestWebRouter(unittest.TestCase):
    def setUp(self):
        self.router = Router()
        self.router.add_route("GET", "/api/ping", lambda h, p: h.wfile.write(b"pong"))
        self.router.add_prefix_route("GET", "/static/", lambda h, p: h.wfile.write(b"static asset"))

    def test_exact_route_match(self):
        handler = DummyHandler("/api/ping")
        self.router.dispatch(handler, "GET")
        self.assertEqual(handler.wfile.data, b"pong")

    def test_prefix_route_match(self):
        handler = DummyHandler("/static/css/app.css")
        self.router.dispatch(handler, "GET")
        self.assertEqual(handler.wfile.data, b"static asset")

    def test_not_found(self):
        handler = DummyHandler("/nonexistent")
        self.router.dispatch(handler, "GET")
        self.assertEqual(handler.status, 404)
        self.assertEqual(handler.wfile.data, b"Not Found")

if __name__ == "__main__":
    unittest.main()
