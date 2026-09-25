"""
Multi-database profile management handlers: list, switch, create, rename, delete, and import.
Zero external pip dependencies.
"""

import os
import re
import json
import time
import shutil
import sqlite3
import indexer_engine
import storage
from services import (
    BASE_DIR,
    APP_CONFIG,
    WATCHER_CONFIG,
    INDEX_LOCK,
    INDEX_STATE,
    get_active_db_path,
    sync_active_db_vars,
    save_config,
    start_indexing_thread
)

def handle_list_databases(handler, parsed):
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
                conn_chk = storage.get_connection(fpath)
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
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps({
        "ok": True,
        "databases": db_list,
        "active_db": active_key,
        "db_storage_dir": storage_dir
    }).encode("utf-8"))

def handle_switch_database(handler, parsed):
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length)
    try:
        data = json.loads(body.decode("utf-8"))
        target_id = data.get("id", "").strip()
        if not target_id or target_id not in APP_CONFIG.get("databases", {}):
            handler.send_response(400)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"ok": False, "error": f"Database '{target_id}' not found"}).encode("utf-8"))
            return
        with INDEX_LOCK:
            if INDEX_STATE["running"]:
                handler.send_response(400)
                handler.send_header("Content-Type", "application/json")
                handler.end_headers()
                handler.wfile.write(json.dumps({"ok": False, "error": "Cannot switch database while indexing is in progress!"}).encode("utf-8"))
                return
            APP_CONFIG["active_db"] = target_id
            sync_active_db_vars()
            save_config()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({
            "ok": True,
            "active_db": target_id,
            "message": f"Switched to {APP_CONFIG['databases'][target_id].get('nickname')}"
        }).encode("utf-8"))
    except Exception as e:
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))

def handle_rename_database(handler, parsed):
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length)
    try:
        data = json.loads(body.decode("utf-8"))
        target_id = data.get("id", "").strip()
        new_nick = data.get("nickname", "").strip()
        if not target_id or target_id not in APP_CONFIG.get("databases", {}):
            handler.send_response(400)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"ok": False, "error": "Database not found"}).encode("utf-8"))
            return
        if not new_nick:
            handler.send_response(400)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"ok": False, "error": "Nickname cannot be empty"}).encode("utf-8"))
            return
        APP_CONFIG["databases"][target_id]["nickname"] = new_nick
        save_config()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": True, "message": "Nickname updated"}).encode("utf-8"))
    except Exception as e:
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))

def handle_create_database(handler, parsed):
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length)
    try:
        data = json.loads(body.decode("utf-8"))
        nickname = data.get("nickname", "").strip() or "New Database"
        folder = data.get("folder", "").strip()
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
        conn_init = storage.get_connection(get_active_db_path())
        indexer_engine.init_db(conn_init)
        conn_init.close()

        # If folder specified, start indexing
        if folder and os.path.exists(folder):
            start_indexing_thread(folder, force_reindex=False, nickname=nickname, db_key=db_id)

        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": True, "id": db_id, "message": f"Created & activated database '{nickname}'"}).encode("utf-8"))
    except Exception as e:
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))

def handle_delete_database(handler, parsed):
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length)
    try:
        data = json.loads(body.decode("utf-8"))
        target_id = data.get("id", "").strip()
        delete_file = bool(data.get("delete_file", False))
        dbs = APP_CONFIG.get("databases", {})
        if target_id not in dbs:
            handler.send_response(400)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"ok": False, "error": "Database profile not found"}).encode("utf-8"))
            return
        if len(dbs) <= 1:
            handler.send_response(400)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"ok": False, "error": "Cannot delete the last remaining database!"}).encode("utf-8"))
            return
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
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": True, "message": f"Database removed"}).encode("utf-8"))
    except Exception as e:
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))

def handle_import_database(handler, parsed):
    content_type = handler.headers.get("Content-Type", "")
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length <= 0:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": "Empty upload"}).encode("utf-8"))
        return

    body = handler.rfile.read(content_length)
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
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": "Invalid SQLite database file"}).encode("utf-8"))
        return

    db_path = get_active_db_path()
    backup_path = db_path + ".bak"
    try:
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
        with open(db_path, "wb") as f:
            f.write(db_data)
        test_conn = storage.get_connection(db_path)
        test_conn.execute("PRAGMA quick_check;")
        test_conn.close()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": True, "message": "Database imported successfully"}).encode("utf-8"))
    except Exception as ex:
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False, "error": f"Import failed: {ex}"}).encode("utf-8"))
