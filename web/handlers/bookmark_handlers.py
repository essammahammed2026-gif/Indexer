"""
Lead bookmarking and tagging HTTP handlers.
Zero external pip dependencies.
"""

import json
import storage
from services import get_active_db_path

def handle_get_bookmarks(handler, parsed):
    bookmarks = storage.get_bookmarks(get_active_db_path())
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps({"ok": True, "bookmarks": bookmarks}).encode("utf-8"))

def handle_add_bookmark(handler, parsed):
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length)
    try:
        data = json.loads(body.decode("utf-8"))
        fpath = data.get("file", "").strip()
        sname = data.get("sheet", "").strip()
        row = data.get("row", 1)
        tag = data.get("tag", "Lead").strip()
        notes = data.get("notes", "").strip()
        ok, msg = storage.add_bookmark(get_active_db_path(), fpath, sname, row, tag=tag, notes=notes)
        handler.send_response(200 if ok else 400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
    except Exception as e:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))

def handle_delete_bookmark(handler, parsed):
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length)
    try:
        data = json.loads(body.decode("utf-8"))
        fpath = data.get("file", "").strip()
        sname = data.get("sheet", "").strip()
        row = data.get("row", 1)
        ok, msg = storage.remove_bookmark(get_active_db_path(), fpath, sname, row)
        handler.send_response(200 if ok else 400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
    except Exception as e:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
