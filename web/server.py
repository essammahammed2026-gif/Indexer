"""
Built-in HTTP server instance and handler dispatch for Indexer.
Zero external pip dependencies.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from .routes import create_router

class AppRequestHandler(BaseHTTPRequestHandler):
    """BaseHTTPRequestHandler delegating all methods to our Router."""
    router = create_router()

    def do_GET(self):
        self.router.dispatch(self, "GET")

    def do_POST(self):
        self.router.dispatch(self, "POST")

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP access logging
        pass

def run_server(host="127.0.0.1", port=8088):
    """Initialize and run the single-threaded or multi-threaded HTTP server."""
    server_address = (host, port)
    HTTPServer.allow_reuse_address = True
    httpd = HTTPServer(server_address, AppRequestHandler)
    print(f"\n=======================================================")
    print(f"🚀 Excel & CDR Browser GUI is running at:")
    print(f"👉 http://localhost:{port}")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down GUI server.")
        httpd.server_close()
