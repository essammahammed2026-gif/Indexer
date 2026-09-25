"""
Search, statistics, quick filters, context window, and export API handlers.
Zero external pip dependencies.
"""

import os
import json
import shutil
import urllib.parse
import storage
from services import (
    BASE_DIR,
    APP_CONFIG,
    WATCHER_CONFIG,
    get_active_db_path
)

def handle_stats(handler, parsed):
    active_key = APP_CONFIG.get("active_db", "default")
    db_meta = APP_CONFIG.get("databases", {}).get(active_key, {})
    nickname = db_meta.get("nickname", "Main Database")
    storage_dir = APP_CONFIG.get("db_storage_dir", BASE_DIR)
    folder = WATCHER_CONFIG.get("folder", "")
    res = storage.get_stats(get_active_db_path(), folder=folder, active_key=active_key, nickname=nickname, storage_dir=storage_dir)
    res["watcher"] = WATCHER_CONFIG.get("active", False)
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(res).encode("utf-8"))

def handle_search(handler, parsed):
    qs = urllib.parse.parse_qs(parsed.query)
    q = qs.get("q", [""])[0]
    limit_val = qs.get("limit", ["50"])[0]
    offset_val = qs.get("offset", ["0"])[0]
    scope_file = qs.get("file", [None])[0]
    scope_folder = qs.get("folder", [None])[0]
    mode_val = qs.get("mode", ["general"])[0].lower()
    limit = int(limit_val) if limit_val.isdigit() else 50
    offset = int(offset_val) if offset_val.isdigit() else 0
    data = storage.query_db(get_active_db_path(), q, limit=limit, offset=offset, scope_file=scope_file, scope_folder=scope_folder, mode=mode_val)
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

def handle_context(handler, parsed):
    qs = urllib.parse.parse_qs(parsed.query)
    file_path = qs.get("file", [""])[0]
    sheet_name = qs.get("sheet", [""])[0]
    row_val = qs.get("row", [""])[0]
    row_idx = int(row_val) if row_val.isdigit() else 1
    ctx = storage.get_context_window(get_active_db_path(), file_path, sheet_name, row_idx, window=3)
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps({"ok": True, "lines": ctx}).encode("utf-8"))

def handle_get_filters(handler, parsed):
    filters = storage.get_quick_filters(get_active_db_path())
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps({"ok": True, "filters": filters}).encode("utf-8"))

def handle_add_filter(handler, parsed):
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length)
    try:
        data = json.loads(body.decode("utf-8"))
        name = data.get("name", "").strip()
        query = data.get("query", "").strip()
        ok, msg = storage.add_quick_filter(get_active_db_path(), name, query)
        handler.send_response(200 if ok else 400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
    except Exception as e:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))

def handle_delete_filter(handler, parsed):
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length)
    try:
        data = json.loads(body.decode("utf-8"))
        filter_id = data.get("id")
        ok, msg = storage.delete_quick_filter(get_active_db_path(), filter_id)
        handler.send_response(200 if ok else 400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
    except Exception as e:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))

def handle_export(handler, parsed):
    db_path = get_active_db_path()
    if not os.path.exists(db_path):
        handler.send_response(404)
        handler.end_headers()
        handler.wfile.write(b"Index database not found")
        return
    file_size = os.path.getsize(db_path)
    handler.send_response(200)
    handler.send_header("Content-Type", "application/octet-stream")
    handler.send_header("Content-Disposition", "attachment; filename=sheets_index.db")
    handler.send_header("Content-Length", str(file_size))
    handler.end_headers()
    with open(db_path, "rb") as f:
        shutil.copyfileobj(f, handler.wfile)
