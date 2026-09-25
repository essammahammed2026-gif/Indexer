"""
Search, statistics, quick filters, context window, export, and CSV streaming API handlers.
Zero external pip dependencies.
"""

import os
import io
import csv
import shutil
import urllib.parse
import storage
from services import (
    BASE_DIR,
    APP_CONFIG,
    WATCHER_CONFIG,
    get_active_db_path
)
from ..http_utils import read_json_body, send_json, send_error, send_success

def handle_stats(handler, parsed):
    active_key = APP_CONFIG.get("active_db", "")
    db_meta = APP_CONFIG.get("databases", {}).get(active_key, {})
    nickname = db_meta.get("nickname", "No Database Loaded" if not active_key else "Main Database")
    storage_dir = APP_CONFIG.get("db_storage_dir", BASE_DIR)
    folder = WATCHER_CONFIG.get("folder", "")
    active_path = get_active_db_path()
    res = storage.get_stats(active_path, folder=folder, active_key=active_key, nickname=nickname, storage_dir=storage_dir)
    res["watcher"] = WATCHER_CONFIG.get("active", False)
    res["has_active_db"] = bool(active_key and active_path and os.path.exists(active_path))
    send_json(handler, res)

def handle_search(handler, parsed):
    active_key = APP_CONFIG.get("active_db", "")
    active_path = get_active_db_path()
    qs = urllib.parse.parse_qs(parsed.query)
    q = qs.get("q", [""])[0]
    limit_val = qs.get("limit", ["50"])[0]
    offset_val = qs.get("offset", ["0"])[0]
    scope_file = qs.get("file", [None])[0]
    scope_folder = qs.get("folder", [None])[0]
    mode_val = qs.get("mode", ["general"])[0].lower()
    limit = int(limit_val) if limit_val.isdigit() else 50
    offset = int(offset_val) if offset_val.isdigit() else 0
    if not active_key or not active_path:
        send_json(handler, {"rows": [], "total": 0, "limit": limit, "offset": offset, "mode": mode_val, "no_db": True})
        return
    data = storage.query_db(active_path, q, limit=limit, offset=offset, scope_file=scope_file, scope_folder=scope_folder, mode=mode_val)
    send_json(handler, data)

def handle_search_csv(handler, parsed):
    """Export search results directly to CSV format for browser download."""
    qs = urllib.parse.parse_qs(parsed.query)
    q = qs.get("q", [""])[0]
    scope_file = qs.get("file", [None])[0]
    scope_folder = qs.get("folder", [None])[0]
    mode_val = qs.get("mode", ["general"])[0].lower()

    if not q:
        send_error(handler, "Query cannot be empty for CSV export", 400)
        return

    data = storage.query_db(get_active_db_path(), q, limit=10000, offset=0, scope_file=scope_file, scope_folder=scope_folder, mode=mode_val)
    rows = data.get("rows", [])

    output = io.StringIO()
    writer = csv.writer(output)

    if mode_val == "telecom" and data.get("type") == "prefix":
        writer.writerow(["Phone", "Name", "Total Matches", "Matched Files"])
        for r in rows:
            writer.writerow([r.get("phone", ""), r.get("name", ""), r.get("count", 0), r.get("files", "")])
    elif mode_val == "telecom":
        writer.writerow(["File", "Sheet", "Row", "Time", "Direction", "Target MSISDN", "Other Party", "Name", "Duration", "Other ID", "Address", "Cell"])
        for r in rows:
            writer.writerow([
                r.get("file", ""), r.get("sheet", ""), r.get("row", ""),
                r.get("time", ""), r.get("dir", ""), r.get("target", ""),
                r.get("other", ""), r.get("name", ""), r.get("duration", ""),
                r.get("other_id", ""), r.get("address", ""), r.get("cell_id", "")
            ])
    else:
        writer.writerow(["File", "Folder", "Sheet", "Row", "Snippet / Content", "Path"])
        for r in rows:
            writer.writerow([
                r.get("file", ""), r.get("folder", ""), r.get("sheet", ""),
                r.get("row", ""), r.get("snippet", ""), r.get("path", "")
            ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    safe_q = urllib.parse.quote(q[:30])
    handler.send_response(200)
    handler.send_header("Content-Type", "text/csv; charset=utf-8")
    handler.send_header("Content-Disposition", f'attachment; filename="search_results_{safe_q}.csv"')
    handler.send_header("Content-Length", str(len(csv_bytes)))
    handler.end_headers()
    handler.wfile.write(csv_bytes)

def handle_context(handler, parsed):
    qs = urllib.parse.parse_qs(parsed.query)
    file_path = qs.get("file", [""])[0]
    sheet_name = qs.get("sheet", [""])[0]
    row_val = qs.get("row", [""])[0]
    row_idx = int(row_val) if row_val.isdigit() else 1
    ctx = storage.get_context_window(get_active_db_path(), file_path, sheet_name, row_idx, window=3)
    send_success(handler, lines=ctx)

def handle_get_filters(handler, parsed):
    filters = storage.get_quick_filters(get_active_db_path())
    send_success(handler, filters=filters)

def handle_add_filter(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    name = (data or {}).get("name", "").strip()
    query = (data or {}).get("query", "").strip()
    ok, msg = storage.add_quick_filter(get_active_db_path(), name, query)
    if ok:
        send_success(handler, msg)
    else:
        send_error(handler, msg, 400)

def handle_delete_filter(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    filter_id = (data or {}).get("id")
    ok, msg = storage.delete_quick_filter(get_active_db_path(), filter_id)
    if ok:
        send_success(handler, msg)
    else:
        send_error(handler, msg, 400)

def handle_export(handler, parsed):
    db_path = get_active_db_path()
    if not os.path.exists(db_path):
        send_error(handler, "Index database not found", 404)
        return
    file_size = os.path.getsize(db_path)
    handler.send_response(200)
    handler.send_header("Content-Type", "application/octet-stream")
    handler.send_header("Content-Disposition", "attachment; filename=sheets_index.db")
    handler.send_header("Content-Length", str(file_size))
    handler.end_headers()
    with open(db_path, "rb") as f:
        shutil.copyfileobj(f, handler.wfile)
