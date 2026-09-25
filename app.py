#!/usr/bin/env python3
"""
CDR & Excel Records Browser - Lightweight Web GUI (Built-in http.server + SQLite)
Supports:
- Unified search (Phones, Names, National ID, Cell IDs, arbitrary sheet values)
- Quick action to open matched row in LibreOffice Calc or default app
- Set Folder to Index with real-time Progress Bar
- Export & Import entire index database
- Live folder watcher automatically indexing newly added/updated sheets
Zero external dependencies (Python standard library only).
"""
import os
import sys
import json
import sqlite3
import re
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
import threading
import subprocess
import time
import shutil
import tempfile
import indexer_engine
from core import (
    normalize_phone,
    normalize_arabic,
    levenshtein_dist,
    parse_google_query,
    open_in_app,
    reveal_in_folder,
    pick_folder_dialog,
    pick_file_dialog
)
import storage

import storage
from services import (
    BASE_DIR,
    CONFIG_PATH,
    UPLOADS_DIR,
    INDEX_LOCK,
    INDEX_STATE,
    APP_CONFIG,
    WATCHER_CONFIG,
    get_active_db_path,
    sync_active_db_vars,
    load_config,
    save_config,
    SUPPORTED_EXTENSIONS,
    index_single_target,
    start_indexing_thread,
    folder_watcher_loop
)
from services.state import DB_PATH

PORT = 8088


def get_db_path():
    return get_active_db_path()

# Data & Search Helpers delegating to storage & services
def get_stats():
    active_key = APP_CONFIG.get("active_db", "default")
    db_meta = APP_CONFIG.get("databases", {}).get(active_key, {})
    nickname = db_meta.get("nickname", "Main Database")
    storage_dir = APP_CONFIG.get("db_storage_dir", BASE_DIR)
    folder = WATCHER_CONFIG.get("folder", "")
    res = storage.get_stats(get_active_db_path(), folder=folder, active_key=active_key, nickname=nickname, storage_dir=storage_dir)
    res["watcher"] = WATCHER_CONFIG.get("active", False)
    return res

def get_quick_filters():
    return storage.get_quick_filters(get_active_db_path())

def add_quick_filter(name, query):
    return storage.add_quick_filter(get_active_db_path(), name, query)

def delete_quick_filter(filter_id):
    return storage.delete_quick_filter(get_active_db_path(), filter_id)

def get_bookmarks():
    return storage.get_bookmarks(get_active_db_path())

def add_bookmark(file_path, sheet_name, row_idx, tag="Lead", notes=""):
    return storage.add_bookmark(get_active_db_path(), file_path, sheet_name, row_idx, tag=tag, notes=notes)

def remove_bookmark(file_path, sheet_name, row_idx):
    return storage.remove_bookmark(get_active_db_path(), file_path, sheet_name, row_idx)

def get_context_window(file_path, sheet_name, row_idx, window=3):
    return storage.get_context_window(get_active_db_path(), file_path, sheet_name, row_idx, window=window)

def get_ocr_boxes(file_path, sheet_name="Image"):
    return storage.get_ocr_boxes(get_active_db_path(), file_path, sheet_name=sheet_name)

def backup_database():
    return storage.backup_database(get_active_db_path())

def record_change_event(event_type, file_path, old_path=None, records_count=0, details=""):
    return storage.record_change_event(get_active_db_path(), event_type, file_path, old_path=old_path, records_count=records_count, details=details)

def get_change_events(limit=50, offset=0, unread_only=False):
    return storage.get_change_events(get_active_db_path(), limit=limit, offset=offset, unread_only=unread_only)

def mark_change_events_read(event_ids=None):
    return storage.mark_change_events_read(get_active_db_path(), event_ids=event_ids)

def clear_all_change_events():
    return storage.clear_all_change_events(get_active_db_path())

def query_db(query, limit=50, offset=0, scope_file=None, scope_folder=None, mode="general"):
    return storage.query_db(get_active_db_path(), query, limit=limit, offset=offset, scope_file=scope_file, scope_folder=scope_folder, mode=mode)

def get_html_template():
    tpl_path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(tpl_path, "r", encoding="utf-8") as f:
        return f.read()


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_html_template().encode("utf-8"))
        elif parsed.path.startswith("/static/"):
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
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(os.path.getsize(safe_path)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                with open(safe_path, "rb") as sf:
                    shutil.copyfileobj(sf, self.wfile)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Static asset not found")
        elif parsed.path == "/api/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(get_stats()).encode("utf-8"))
        elif parsed.path == "/api/watch/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(WATCHER_CONFIG).encode("utf-8"))
        elif parsed.path == "/api/index/status" or parsed.path == "/api/progress":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = dict(INDEX_STATE)
            resp["in_progress"] = INDEX_STATE.get("running", False)
            resp["status"] = INDEX_STATE.get("status_message", "")
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif parsed.path == "/api/notifications":
            qs = urllib.parse.parse_qs(parsed.query)
            limit = int(qs.get("limit", ["50"])[0]) if qs.get("limit", [""])[0].isdigit() else 50
            offset = int(qs.get("offset", ["0"])[0]) if qs.get("offset", [""])[0].isdigit() else 0
            unread_only = qs.get("unread", ["0"])[0] in ("1", "true")
            res_data = get_change_events(limit=limit, offset=offset, unread_only=unread_only)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res_data).encode("utf-8"))
        elif parsed.path == "/api/index/export":
            if not os.path.exists(DB_PATH):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Index database not found")
                return
            file_size = os.path.getsize(DB_PATH)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", "attachment; filename=sheets_index.db")
            self.send_header("Content-Length", str(file_size))
            self.end_headers()
            with open(DB_PATH, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
        elif parsed.path == "/api/search":
            qs = urllib.parse.parse_qs(parsed.query)
            q = qs.get("q", [""])[0]
            limit_val = qs.get("limit", ["50"])[0]
            offset_val = qs.get("offset", ["0"])[0]
            scope_file = qs.get("file", [None])[0]
            scope_folder = qs.get("folder", [None])[0]
            mode_val = qs.get("mode", ["general"])[0].lower()
            limit = int(limit_val) if limit_val.isdigit() else 50
            offset = int(offset_val) if offset_val.isdigit() else 0
            data = query_db(q, limit=limit, offset=offset, scope_file=scope_file, scope_folder=scope_folder, mode=mode_val)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        elif parsed.path == "/api/open":
            qs = urllib.parse.parse_qs(parsed.query)
            file_path = qs.get("file", [""])[0]
            sheet_name = qs.get("sheet", [""])[0]
            row_val = qs.get("row", [""])[0]
            row_idx = int(row_val) if row_val.isdigit() else None
            ok, msg = open_in_app(file_path, sheet_name=sheet_name, row_idx=row_idx)
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok, "message" if ok else "error": msg}).encode("utf-8"))
        elif parsed.path == "/api/reveal":
            qs = urllib.parse.parse_qs(parsed.query)
            file_path = qs.get("file", [""])[0]
            ok, msg = reveal_in_folder(file_path)
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok, "message" if ok else "error": msg}).encode("utf-8"))
        elif parsed.path == "/api/filters":
            filters = get_quick_filters()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "filters": filters}).encode("utf-8"))
        elif parsed.path == "/api/bookmarks":
            bookmarks = get_bookmarks()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "bookmarks": bookmarks}).encode("utf-8"))
        elif parsed.path == "/api/context":
            qs = urllib.parse.parse_qs(parsed.query)
            file_path = qs.get("file", [""])[0]
            sheet_name = qs.get("sheet", [""])[0]
            row_val = qs.get("row", [""])[0]
            row_idx = int(row_val) if row_val.isdigit() else 1
            ctx = get_context_window(file_path, sheet_name, row_idx, window=3)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "lines": ctx}).encode("utf-8"))
        elif parsed.path == "/api/image/view":
            qs = urllib.parse.parse_qs(parsed.query)
            file_path = qs.get("file", [""])[0]
            if not file_path or not os.path.exists(file_path):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Image file not found")
                return
            ext = os.path.splitext(file_path)[1].lower()
            mime = "image/png"
            if ext in ('.jpg', '.jpeg'): mime = "image/jpeg"
            elif ext == '.webp': mime = "image/webp"
            elif ext == '.bmp': mime = "image/bmp"
            elif ext == '.tiff': mime = "image/tiff"
            try:
                with open(file_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
        elif parsed.path == "/api/image/boxes":
            qs = urllib.parse.parse_qs(parsed.query)
            file_path = qs.get("file", [""])[0]
            sheet_name = qs.get("sheet", ["Image"])[0]
            box_data = get_ocr_boxes(file_path, sheet_name=sheet_name)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "data": box_data}).encode("utf-8"))
        elif parsed.path == "/api/dialog/pick-folder":
            chosen = pick_folder_dialog("Select Folder to Index or Search")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": bool(chosen), "path": chosen or ""}).encode("utf-8"))
        elif parsed.path == "/api/dialog/pick-file":
            chosen = pick_file_dialog("Select File or Image to Index")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": bool(chosen), "path": chosen or ""}).encode("utf-8"))
        elif parsed.path == "/api/backup":
            ok, msg = backup_database()
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
        elif parsed.path == "/api/databases":
            # List all configured databases with live file size & records count
            storage_dir = APP_CONFIG.get("db_storage_dir", BASE_DIR)
            active_key = APP_CONFIG.get("active_db", "default")
            db_list = []
            for db_key, meta in APP_CONFIG.get("databases", {}).items():
                fname = meta.get("filename", "sheets_index.db")
                fpath = os.path.join(storage_dir, fname)
                fsize = 0
                records = 0
                files_count = 0
                exists = os.path.exists(fpath)
                if exists:
                    try:
                        fsize = os.path.getsize(fpath)
                        conn_chk = sqlite3.connect(fpath)
                        cur_chk = conn_chk.cursor()
                        cur_chk.execute("SELECT COUNT(*) FROM files;")
                        files_count = cur_chk.fetchone()[0]
                        cur_chk.execute("SELECT COUNT(*) FROM cdr_records;")
                        records = cur_chk.fetchone()[0]
                        conn_chk.close()
                    except Exception:
                        pass
                db_list.append({
                    "id": db_key,
                    "nickname": meta.get("nickname") or db_key,
                    "filename": fname,
                    "path": fpath,
                    "exists": exists,
                    "size": fsize,
                    "files_count": files_count,
                    "records_count": records,
                    "watch_folder": meta.get("watch_folder", ""),
                    "watch_active": meta.get("watch_active", False),
                    "created_at": meta.get("created_at", ""),
                    "is_active": (db_key == active_key)
                })
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "ok": True,
                "databases": db_list,
                "active_db": active_key,
                "db_storage_dir": storage_dir
            }).encode("utf-8"))
        elif parsed.path == "/api/settings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "ok": True,
                "db_storage_dir": APP_CONFIG.get("db_storage_dir", BASE_DIR),
                "watcher_settings": APP_CONFIG.get("watcher_settings", {}),
                "active_db": APP_CONFIG.get("active_db", "default")
            }).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/databases/switch":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                target_id = data.get("id", "").strip()
                if not target_id or target_id not in APP_CONFIG.get("databases", {}):
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": f"Database '{target_id}' not found"}).encode("utf-8"))
                    return
                with INDEX_LOCK:
                    if INDEX_STATE["running"]:
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"ok": False, "error": "Cannot switch database while indexing is in progress!"}).encode("utf-8"))
                        return
                    APP_CONFIG["active_db"] = target_id
                    sync_active_db_vars()
                    save_config()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "active_db": target_id,
                    "message": f"Switched to {APP_CONFIG['databases'][target_id].get('nickname')}"
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/databases/rename":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                target_id = data.get("id", "").strip()
                new_nick = data.get("nickname", "").strip()
                if not target_id or target_id not in APP_CONFIG.get("databases", {}):
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Database not found"}).encode("utf-8"))
                    return
                if not new_nick:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Nickname cannot be empty"}).encode("utf-8"))
                    return
                APP_CONFIG["databases"][target_id]["nickname"] = new_nick
                save_config()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "message": "Nickname updated"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/databases/create":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                nickname = data.get("nickname", "").strip() or "New Database"
                folder = data.get("folder", "").strip()
                # Generate unique ID and filename
                db_id = re.sub(r'[^a-zA-Z0-9_]', '_', nickname.lower()).strip('_')
                if not db_id:
                    db_id = f"db_{int(time.time())}"
                if db_id in APP_CONFIG.get("databases", {}):
                    db_id = f"{db_id}_{int(time.time())}"
                fname = f"indexer_{db_id}.db"
                APP_CONFIG["databases"][db_id] = {
                    "nickname": nickname,
                    "filename": fname,
                    "watch_folder": folder,
                    "watch_active": bool(folder),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                APP_CONFIG["active_db"] = db_id
                sync_active_db_vars()
                save_config()

                # Initialize database schema immediately
                conn_init = sqlite3.connect(DB_PATH)
                indexer_engine.init_db(conn_init)
                conn_init.close()

                # If folder specified, start indexing
                if folder and os.path.exists(folder):
                    start_indexing_thread(folder, force_reindex=False, nickname=nickname, db_key=db_id)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "id": db_id, "message": f"Created & activated database '{nickname}'"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/databases/delete":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                target_id = data.get("id", "").strip()
                delete_file = bool(data.get("delete_file", False))
                dbs = APP_CONFIG.get("databases", {})
                if target_id not in dbs:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Database profile not found"}).encode("utf-8"))
                    return
                if len(dbs) <= 1:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Cannot delete the last remaining database!"}).encode("utf-8"))
                    return
                # If deleted DB is active, switch to another
                meta = dbs.pop(target_id)
                storage_dir = APP_CONFIG.get("db_storage_dir", BASE_DIR)
                fpath = os.path.join(storage_dir, meta.get("filename", ""))
                if delete_file and os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                        for suff in ["-wal", "-shm"]:
                            if os.path.exists(fpath + suff):
                                os.remove(fpath + suff)
                    except Exception as ex:
                        print(f"[DELETE DB FILE ERROR] {ex}")
                if APP_CONFIG.get("active_db") == target_id:
                    APP_CONFIG["active_db"] = list(dbs.keys())[0]
                    sync_active_db_vars()
                save_config()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "message": f"Database removed"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/settings/save":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                storage_dir = data.get("db_storage_dir", "").strip()
                if storage_dir:
                    storage_dir = os.path.abspath(storage_dir)
                    os.makedirs(storage_dir, exist_ok=True)
                    APP_CONFIG["db_storage_dir"] = storage_dir
                if "watcher_settings" in data and isinstance(data["watcher_settings"], dict):
                    ws = data["watcher_settings"]
                    if "poll_interval_seconds" in ws:
                        APP_CONFIG["watcher_settings"]["poll_interval_seconds"] = max(1, int(ws["poll_interval_seconds"]))
                    if "debounce_delay_seconds" in ws:
                        APP_CONFIG["watcher_settings"]["debounce_delay_seconds"] = max(0.5, float(ws["debounce_delay_seconds"]))
                    if "max_file_size_mb" in ws:
                        APP_CONFIG["watcher_settings"]["max_file_size_mb"] = max(1, float(ws["max_file_size_mb"]))
                    if "ignore_hidden_temp" in ws:
                        APP_CONFIG["watcher_settings"]["ignore_hidden_temp"] = bool(ws["ignore_hidden_temp"])
                sync_active_db_vars()
                save_config()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "message": "Settings saved successfully"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/bookmarks/add":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                fpath = data.get("file", "").strip()
                sname = data.get("sheet", "").strip()
                row = data.get("row", 1)
                tag = data.get("tag", "Lead").strip()
                notes = data.get("notes", "").strip()
                ok, msg = add_bookmark(fpath, sname, row, tag=tag, notes=notes)
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/bookmarks/delete":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                fpath = data.get("file", "").strip()
                sname = data.get("sheet", "").strip()
                row = data.get("row", 1)
                ok, msg = remove_bookmark(fpath, sname, row)
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/filters/add":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                name = data.get("name", "").strip()
                query = data.get("query", "").strip()
                ok, msg = add_quick_filter(name, query)
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/filters/delete":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                filter_id = data.get("id")
                ok, msg = delete_quick_filter(filter_id)
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/index/start":
            qs = urllib.parse.parse_qs(parsed.query)
            folder = qs.get("folder", [""])[0] or WATCHER_CONFIG.get("folder", "")
            force_reindex = qs.get("reindex", ["0"])[0] in ("1", "true")
            force_refresh = qs.get("refresh", ["0"])[0] in ("1", "true")
            nickname = qs.get("nickname", [""])[0].strip()
            create_new_db = qs.get("create_db", ["0"])[0] in ("1", "true")

            if create_new_db and folder:
                if not nickname:
                    nickname = os.path.basename(folder.rstrip('/')) or "Indexed Folder"
                db_id = re.sub(r'[^a-zA-Z0-9_]', '_', nickname.lower()).strip('_')
                if not db_id:
                    db_id = f"db_{int(time.time())}"
                if db_id in APP_CONFIG.get("databases", {}):
                    db_id = f"{db_id}_{int(time.time())}"
                fname = f"indexer_{db_id}.db"
                APP_CONFIG["databases"][db_id] = {
                    "nickname": nickname,
                    "filename": fname,
                    "watch_folder": folder,
                    "watch_active": True,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                APP_CONFIG["active_db"] = db_id
                sync_active_db_vars()
                save_config()
                # Init new DB file
                conn_init = sqlite3.connect(DB_PATH)
                indexer_engine.init_db(conn_init)
                conn_init.close()

            ok, msg = start_indexing_thread(folder, force_reindex=force_reindex, force_refresh=force_refresh, nickname=nickname)
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok, "message" if ok else "error": msg, "active_db": APP_CONFIG.get("active_db")}).encode("utf-8"))
        elif parsed.path == "/api/index/refresh":
            folder = WATCHER_CONFIG.get("folder", "")
            if not folder:
                # Try inferring from files table
                try:
                    conn = sqlite3.connect(DB_PATH)
                    row = conn.cursor().execute("SELECT folder FROM files LIMIT 1;").fetchone()
                    if row and row[0]:
                        folder = row[0]
                    conn.close()
                except Exception:
                    pass
            if not folder or not os.path.exists(folder):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "No indexed folder set to refresh. Please choose a folder."}).encode("utf-8"))
            else:
                ok, msg = start_indexing_thread(folder, force_refresh=True)
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": ok, "message" if ok else "error": msg}).encode("utf-8"))
        elif parsed.path == "/api/index/reindex":
            qs = urllib.parse.parse_qs(parsed.query)
            folder = qs.get("folder", [""])[0] or WATCHER_CONFIG.get("folder", "")
            if not folder:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    row = conn.cursor().execute("SELECT folder FROM files LIMIT 1;").fetchone()
                    if row and row[0]:
                        folder = row[0]
                    conn.close()
                except Exception:
                    pass
            if not folder or not os.path.exists(folder):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "No folder specified to re-index."}).encode("utf-8"))
            else:
                ok, msg = start_indexing_thread(folder, force_reindex=True)
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": ok, "message" if ok else "error": msg}).encode("utf-8"))
        elif parsed.path == "/api/notifications/read":
            content_length = int(self.headers.get("Content-Length", 0))
            event_ids = None
            if content_length > 0:
                try:
                    body = self.rfile.read(content_length)
                    data = json.loads(body.decode("utf-8"))
                    event_ids = data.get("ids")
                except Exception:
                    pass
            ok, msg = mark_change_events_read(event_ids=event_ids)
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
        elif parsed.path == "/api/notifications/clear":
            ok, msg = clear_all_change_events()
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok, "message": msg}).encode("utf-8"))
        elif parsed.path == "/api/watch/toggle":
            WATCHER_CONFIG["active"] = not WATCHER_CONFIG.get("active", False)
            save_config()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "ok": True,
                "active": WATCHER_CONFIG["active"],
                "message": f"Watcher turned {'ON' if WATCHER_CONFIG['active'] else 'OFF'}"
            }).encode("utf-8"))
        elif parsed.path == "/api/index/import":
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Empty upload"}).encode("utf-8"))
                return

            body = self.rfile.read(content_length)
            
            # Handle multipart/form-data
            db_data = None
            if "boundary=" in content_type:
                boundary = content_type.split("boundary=")[-1].strip().encode('latin-1')
                parts = body.split(b"--" + boundary)
                for part in parts:
                    if b"filename=" in part:
                        header_end = part.find(b"\r\n\r\n")
                        if header_end != -1:
                            db_data = part[header_end + 4:].rstrip(b"\r\n--")
                            break
            else:
                db_data = body

            if not db_data or len(db_data) < 100 or not db_data.startswith(b"SQLite format 3"):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Invalid SQLite database file"}).encode("utf-8"))
                return

            # Safely replace database
            backup_path = DB_PATH + ".bak"
            try:
                if os.path.exists(DB_PATH):
                    shutil.copy2(DB_PATH, backup_path)
                with open(DB_PATH, "wb") as f:
                    f.write(db_data)
                # Verify SQLite integrity
                test_conn = sqlite3.connect(DB_PATH)
                test_conn.execute("PRAGMA quick_check;")
                test_conn.close()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "message": "Database imported successfully"}).encode("utf-8"))
            except Exception as ex:
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, DB_PATH)
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": f"Import failed: {ex}"}).encode("utf-8"))
        elif parsed.path == "/api/target/index":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                target_path = data.get("path", "").strip()
                if not target_path:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Path cannot be empty"}).encode("utf-8"))
                    return
                ok, msg, count, scanned = index_single_target(target_path)
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": ok,
                    "message" if ok else "error": msg,
                    "count": count,
                    "scanned": scanned,
                    "target": os.path.abspath(target_path),
                    "is_dir": os.path.isdir(target_path)
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/target/upload":
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Empty upload payload"}).encode("utf-8"))
                return
            body = self.rfile.read(content_length)
            file_bytes = None
            filename = "upload"
            if "boundary=" in content_type:
                boundary = content_type.split("boundary=")[-1].strip().encode('latin-1')
                parts = body.split(b"--" + boundary)
                for part in parts:
                    if b"filename=" in part:
                        try:
                            # Extract filename from header
                            head_line = part.split(b"\r\n\r\n")[0].decode('latin-1', errors='ignore')
                            fn_match = re.search(r'filename="([^"]+)"', head_line)
                            if fn_match:
                                filename = os.path.basename(fn_match.group(1))
                        except Exception:
                            pass
                        header_end = part.find(b"\r\n\r\n")
                        if header_end != -1:
                            file_bytes = part[header_end + 4:].rstrip(b"\r\n--")
                            break
            else:
                file_bytes = body

            if not file_bytes:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "No file content detected"}).encode("utf-8"))
                return

            # Clean filename
            filename = re.sub(r'[^\w\.\-_ ]', '_', filename)
            dest_path = os.path.join(UPLOADS_DIR, f"{int(time.time())}_{filename}")
            try:
                with open(dest_path, "wb") as f:
                    f.write(file_bytes)
                ok, msg, count, scanned = index_single_target(dest_path)
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": ok,
                    "message": msg if ok else f"Uploaded but indexing error: {msg}",
                    "path": dest_path,
                    "filename": filename,
                    "count": count,
                    "scanned": scanned
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": f"Failed to save and index file: {e}"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_server():
    server_address = ("127.0.0.1", PORT)
    HTTPServer.allow_reuse_address = True
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"\n=======================================================")
    print(f"🚀 Excel & CDR Browser GUI is running at:")
    print(f"👉 http://localhost:{PORT}")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down GUI server.")
        httpd.server_close()

if __name__ == "__main__":
    load_config()

    # Start live directory watcher in background daemon thread
    watcher_thread = threading.Thread(target=folder_watcher_loop, daemon=True)
    watcher_thread.start()

    run_server()
