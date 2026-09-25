"""
Multi-database profile management handlers: list, switch, create, rename, delete, and import.
Zero external pip dependencies.
"""

import os
import re
import time
import shutil
import storage
from services import (
    BASE_DIR,
    APP_CONFIG,
    INDEX_LOCK,
    INDEX_STATE,
    get_active_db_path,
    sync_active_db_vars,
    save_config,
    start_indexing_thread
)
from ..http_utils import read_json_body, send_json, send_success, send_error

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
    send_success(handler, databases=db_list, active_db=active_key, db_storage_dir=storage_dir)

def handle_switch_database(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    target_id = (data or {}).get("id", "").strip()
    if not target_id or target_id not in APP_CONFIG.get("databases", {}):
        send_error(handler, f"Database '{target_id}' not found", 400)
        return
    with INDEX_LOCK:
        if INDEX_STATE["running"]:
            send_error(handler, "Cannot switch database while indexing is in progress!", 400)
            return
        APP_CONFIG["active_db"] = target_id
        sync_active_db_vars()
        save_config()
    send_success(handler, f"Switched to {APP_CONFIG['databases'][target_id].get('nickname')}", active_db=target_id)

def handle_rename_database(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    target_id = (data or {}).get("id", "").strip()
    new_nick = (data or {}).get("nickname", "").strip()
    if not target_id or target_id not in APP_CONFIG.get("databases", {}):
        send_error(handler, "Database not found", 400)
        return
    if not new_nick:
        send_error(handler, "Nickname cannot be empty", 400)
        return
    APP_CONFIG["databases"][target_id]["nickname"] = new_nick
    save_config()
    send_success(handler, "Nickname updated")

def handle_create_database(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    nickname = (data or {}).get("nickname", "").strip() or "New Database"
    folder = (data or {}).get("folder", "").strip()
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

    # Initialize schema immediately
    conn_init = storage.get_connection(get_active_db_path())
    storage.init_tables(conn_init)
    conn_init.close()

    if folder and os.path.exists(folder):
        start_indexing_thread(folder, force_reindex=False, nickname=nickname, db_key=db_id)

    send_success(handler, f"Created & activated database '{nickname}'", id=db_id)

def handle_delete_database(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    target_id = (data or {}).get("id", "").strip()
    delete_file = bool((data or {}).get("delete_file", False))
    dbs = APP_CONFIG.get("databases", {})
    if target_id not in dbs:
        send_error(handler, "Database profile not found", 400)
        return
    if len(dbs) <= 1:
        send_error(handler, "Cannot delete the last remaining database!", 400)
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
    send_success(handler, "Database removed")

def handle_import_database(handler, parsed):
    content_type = handler.headers.get("Content-Type", "")
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length <= 0:
        send_error(handler, "Empty upload", 400)
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
        send_error(handler, "Invalid SQLite database file", 400)
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
        send_success(handler, "Database imported successfully")
    except Exception as ex:
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
        send_error(handler, f"Import failed: {ex}", 500)
