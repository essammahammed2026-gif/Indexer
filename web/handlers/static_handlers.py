"""
Static asset and template handlers.
Zero external pip dependencies.
"""

import os
import shutil
from services import BASE_DIR

def handle_index_html(handler, parsed):
    """Serve the single page application HTML shell."""
    tpl_path = os.path.join(BASE_DIR, "templates", "index.html")
    if not os.path.exists(tpl_path):
        handler.send_response(404)
        handler.end_headers()
        handler.wfile.write(b"Template not found")
        return
    with open(tpl_path, "r", encoding="utf-8") as f:
        content = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(content.encode("utf-8"))

def handle_static_asset(handler, parsed):
    """Serve static CSS, JS, SVG, and image files safely within static/ directory."""
    rel_path = parsed.path[len("/static/"):].lstrip("/")
    static_dir = os.path.join(BASE_DIR, "static")
    safe_path = os.path.normpath(os.path.join(static_dir, rel_path))
    if os.path.commonpath([static_dir, safe_path]) == static_dir and os.path.exists(safe_path) and os.path.isfile(safe_path):
        mime = "text/plain"
        if safe_path.endswith(".css"):
            mime = "text/css; charset=utf-8"
        elif safe_path.endswith(".js"):
            mime = "application/javascript; charset=utf-8"
        elif safe_path.endswith(".svg"):
            mime = "image/svg+xml"
        elif safe_path.endswith(".png"):
            mime = "image/png"
        handler.send_response(200)
        handler.send_header("Content-Type", mime)
        handler.send_header("Content-Length", str(os.path.getsize(safe_path)))
        handler.send_header("Cache-Control", "no-cache")
        handler.end_headers()
        with open(safe_path, "rb") as sf:
            shutil.copyfileobj(sf, handler.wfile)
    else:
        handler.send_response(404)
        handler.end_headers()
        handler.wfile.write(b"Static asset not found")
