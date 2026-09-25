"""
Web request routing table and HTTP dispatcher for Indexer.
Zero external pip dependencies.
"""

import urllib.parse

class Router:
    """
    Lightweight HTTP request router mapping (method, path) to handler functions.
    Supports exact path matching and prefix path matching (e.g. /static/).
    """
    def __init__(self):
        self.routes = {"GET": {}, "POST": {}}
        self.prefix_routes = {"GET": [], "POST": []}

    def add_route(self, method, path, handler):
        self.routes[method.upper()][path] = handler

    def add_prefix_route(self, method, prefix, handler):
        self.prefix_routes[method.upper()].append((prefix, handler))

    def dispatch(self, handler_instance, method):
        method = method.upper()
        parsed = urllib.parse.urlparse(handler_instance.path)
        path = parsed.path

        # 1. Exact route match
        if method in self.routes and path in self.routes[method]:
            return self.routes[method][path](handler_instance, parsed)

        # 2. Prefix route match (longest prefix first)
        if method in self.prefix_routes:
            for prefix, h in sorted(self.prefix_routes[method], key=lambda x: len(x[0]), reverse=True):
                if path.startswith(prefix):
                    return h(handler_instance, parsed)

        # 3. Not found
        handler_instance.send_response(404)
        handler_instance.end_headers()
        handler_instance.wfile.write(b"Not Found")
