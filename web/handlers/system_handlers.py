"""
Desktop interoperability, dialog runners, change notifications, background indexing triggers,
watcher toggles, and scoped target indexing HTTP handlers.
Zero external pip dependencies.
"""

import os
import re
import time
import urllib.parse
from core import (
    open_in_app,
    reveal_in_folder,
    pick_folder_dialog,
    pick_file_dialog
)
import storage
from services import (
    UPLOADS_DIR,
    INDEX_STATE,
    APP_CONFIG,
    WATCHER_CONFIG,
    get_active_db_path,
    sync_active_db_vars,
    save_config,
    start_indexing_thread,
    index_single_target
)
from ..http_utils import read_json_body, send_json, send_success, send_error

def handle_open(handler, parsed):
    qs = urllib.parse.parse_qs(parsed.query)
    file_path = qs.get("file", [""])[0]
    sheet_name = qs.get("sheet", [""])[0]
    row_val = qs.get("row", [""])[0]
    row_idx = int(row_val) if row_val.isdigit() else None
    ok, msg = open_in_app(file_path, sheet_name=sheet_name, row_idx=row_idx)
    if ok:
        send_success(handler, msg)
    else:
        send_error(handler, msg, 400)

def handle_reveal(handler, parsed):
    qs = urllib.parse.parse_qs(parsed.query)
    file_path = qs.get("file", [""])[0]
    ok, msg = reveal_in_folder(file_path)
    if ok:
        send_success(handler, msg)
    else:
        send_error(handler, msg, 400)

def handle_pick_folder_dialog(handler, parsed):
    chosen = pick_folder_dialog("Select Folder to Index or Search")
    send_success(handler, path=chosen or "")

def handle_pick_file_dialog(handler, parsed):
    chosen = pick_file_dialog("Select File or Image to Index")
    send_success(handler, path=chosen or "")

def handle_backup(handler, parsed):
    ok, msg = storage.backup_database(get_active_db_path())
    if ok:
        send_success(handler, msg)
    else:
        send_error(handler, msg, 500)

def handle_watch_status(handler, parsed):
    send_json(handler, WATCHER_CONFIG)

def handle_watch_toggle(handler, parsed):
    WATCHER_CONFIG["active"] = not WATCHER_CONFIG.get("active", False)
    save_config()
    send_success(
        handler,
        f"Watcher turned {'ON' if WATCHER_CONFIG['active'] else 'OFF'}",
        active=WATCHER_CONFIG["active"]
    )

def handle_index_status(handler, parsed):
    resp = dict(INDEX_STATE)
    resp["in_progress"] = INDEX_STATE.get("running", False)
    resp["status"] = INDEX_STATE.get("status_message", "")
    send_json(handler, resp)

def handle_get_notifications(handler, parsed):
    qs = urllib.parse.parse_qs(parsed.query)
    limit = int(qs.get("limit", ["50"])[0]) if qs.get("limit", [""])[0].isdigit() else 50
    offset = int(qs.get("offset", ["0"])[0]) if qs.get("offset", [""])[0].isdigit() else 0
    unread_only = qs.get("unread", ["0"])[0] in ("1", "true")
    res_data = storage.get_change_events(get_active_db_path(), limit=limit, offset=offset, unread_only=unread_only)
    send_json(handler, res_data)

def handle_read_notifications(handler, parsed):
    data, err = read_json_body(handler)
    event_ids = (data or {}).get("ids") if data else None
    ok, msg = storage.mark_change_events_read(get_active_db_path(), event_ids=event_ids)
    if ok:
        send_success(handler, msg)
    else:
        send_error(handler, msg, 500)

def handle_clear_notifications(handler, parsed):
    ok, msg = storage.clear_all_change_events(get_active_db_path())
    if ok:
        send_success(handler, msg)
    else:
        send_error(handler, msg, 500)

def handle_index_start(handler, parsed):
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
        conn_init = storage.get_connection(get_active_db_path())
        storage.init_tables(conn_init)
        conn_init.close()

    ok, msg = start_indexing_thread(folder, force_reindex=force_reindex, force_refresh=force_refresh, nickname=nickname)
    if ok:
        send_success(handler, msg, active_db=APP_CONFIG.get("active_db"))
    else:
        send_error(handler, msg, 400)

def handle_index_refresh(handler, parsed):
    folder = WATCHER_CONFIG.get("folder", "")
    if not folder:
        try:
            conn = storage.get_connection(get_active_db_path())
            row = conn.cursor().execute("SELECT folder FROM files LIMIT 1;").fetchone()
            if row and row[0]:
                folder = row[0]
            conn.close()
        except Exception:
            pass
    if not folder or not os.path.exists(folder):
        send_error(handler, "No indexed folder set to refresh. Please choose a folder.", 400)
    else:
        ok, msg = start_indexing_thread(folder, force_refresh=True)
        if ok:
            send_success(handler, msg)
        else:
            send_error(handler, msg, 400)

def handle_index_reindex(handler, parsed):
    qs = urllib.parse.parse_qs(parsed.query)
    folder = qs.get("folder", [""])[0] or WATCHER_CONFIG.get("folder", "")
    if not folder:
        try:
            conn = storage.get_connection(get_active_db_path())
            row = conn.cursor().execute("SELECT folder FROM files LIMIT 1;").fetchone()
            if row and row[0]:
                folder = row[0]
            conn.close()
        except Exception:
            pass
    if not folder or not os.path.exists(folder):
        send_error(handler, "No folder specified to re-index.", 400)
    else:
        ok, msg = start_indexing_thread(folder, force_reindex=True)
        if ok:
            send_success(handler, msg)
        else:
            send_error(handler, msg, 400)

def handle_target_index(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    target_path = (data or {}).get("path", "").strip()
    if not target_path:
        send_error(handler, "Path cannot be empty", 400)
        return
    ok, msg, count, scanned = index_single_target(target_path)
    if ok:
        send_success(
            handler,
            msg,
            count=count,
            scanned=scanned,
            target=os.path.abspath(target_path),
            is_dir=os.path.isdir(target_path)
        )
    else:
        send_error(handler, msg, 400)

def handle_target_upload(handler, parsed):
    content_type = handler.headers.get("Content-Type", "")
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length <= 0:
        send_error(handler, "Empty upload payload", 400)
        return
    body = handler.rfile.read(content_length)
    file_bytes = None
    filename = "upload"
    if "boundary=" in content_type:
        boundary = content_type.split("boundary=")[-1].strip().encode('latin-1')
        parts = body.split(b"--" + boundary)
        for part in parts:
            if b"filename=" in part:
                try:
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
        send_error(handler, "No file content detected", 400)
        return

    filename = re.sub(r'[^\w\.\-_ ]', '_', filename)
    dest_path = os.path.join(UPLOADS_DIR, f"{int(time.time())}_{filename}")
    try:
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
        ok, msg, count, scanned = index_single_target(dest_path)
        if ok:
            send_success(
                handler,
                msg,
                path=dest_path,
                filename=filename,
                count=count,
                scanned=scanned
            )
        else:
            send_error(handler, f"Uploaded but indexing error: {msg}", 400)
    except Exception as e:
        send_error(handler, f"Failed to save and index file: {e}", 500)
