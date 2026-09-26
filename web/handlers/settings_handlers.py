"""
Application configuration, watcher settings, and factory reset HTTP handlers.
Zero external pip dependencies.
Strictly NO fallbacks to default databases or application directory.
"""

import os
import re
import time
from services import (
    INDEX_LOCK,
    INDEX_STATE,
    APP_CONFIG,
    WATCHER_CONFIG,
    sync_active_db_vars,
    save_config
)
from ..http_utils import read_json_body, send_json, send_success, send_error

def discover_databases_in_dir(storage_dir):
    """
    Scan storage_dir for existing .db files (from previous installs) and register them.
    Returns list of newly discovered database metadata.
    """
    discovered = []
    if not storage_dir or not os.path.isdir(storage_dir):
        return discovered
    dbs = APP_CONFIG.setdefault("databases", {})
    existing_files = {meta.get("filename"): k for k, meta in dbs.items()}
    for entry in sorted(os.listdir(storage_dir)):
        if entry.endswith(".db") and not entry.endswith("-wal") and not entry.endswith("-shm"):
            full_p = os.path.join(storage_dir, entry)
            if not os.path.isfile(full_p):
                continue
            if entry in existing_files:
                continue
            base = os.path.splitext(entry)[0]
            db_id = re.sub(r'[^a-zA-Z0-9_]', '_', base.lower()).strip('_') or f"db_{int(time.time())}"
            if db_id in dbs:
                db_id = f"{db_id}_{int(time.time())}"
            nick = base.replace('_', ' ').replace('-', ' ').title()
            if nick.lower() == "sheets index":
                nick = "Main Archive Index"
            dbs[db_id] = {
                "nickname": nick,
                "filename": entry,
                "watch_folder": "",
                "watch_active": False,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            existing_files[entry] = db_id
            discovered.append({"id": db_id, "nickname": nick, "filename": entry})
    return discovered

def handle_get_settings(handler, parsed):
    storage_dir = APP_CONFIG.get("db_storage_dir", "")
    needs_setup = not bool(storage_dir and os.path.isdir(storage_dir))
    send_success(
        handler,
        db_storage_dir=storage_dir,
        watcher_settings=APP_CONFIG.get("watcher_settings", {}),
        active_db=APP_CONFIG.get("active_db", ""),
        needs_setup=needs_setup
    )

def handle_init_storage(handler, parsed):
    """
    First-launch / storage setup handler.
    Initializes the storage directory and discovers any previous index databases.
    """
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    folder = (data or {}).get("folder", "").strip()
    if not folder:
        send_error(handler, "Storage folder path cannot be empty", 400)
        return
    try:
        storage_dir = os.path.abspath(folder)
        os.makedirs(storage_dir, exist_ok=True)
        APP_CONFIG["db_storage_dir"] = storage_dir
        discovered = discover_databases_in_dir(storage_dir)
        sync_active_db_vars()
        save_config()
        send_success(
            handler,
            f"Storage configured at '{storage_dir}'. Found {len(discovered)} existing database(s).",
            db_storage_dir=storage_dir,
            discovered_count=len(discovered),
            discovered=discovered
        )
    except Exception as e:
        send_error(handler, f"Failed to initialize storage folder: {e}", 500)

def handle_save_settings(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    try:
        storage_dir = (data or {}).get("db_storage_dir", "").strip()
        discovered_count = 0
        if storage_dir:
            storage_dir = os.path.abspath(storage_dir)
            os.makedirs(storage_dir, exist_ok=True)
            APP_CONFIG["db_storage_dir"] = storage_dir
            discovered = discover_databases_in_dir(storage_dir)
            discovered_count = len(discovered)
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
        send_success(
            handler,
            "Settings saved successfully" + (f" (found {discovered_count} existing index database(s))" if discovered_count else "")
        )
    except Exception as e:
        send_error(handler, str(e), 500)

def handle_reset_app(handler, parsed):
    """
    Reset application configuration to fresh first-launch state.
    Unbinds database profiles, resets watchers, and clears storage directory.
    Leaves user database files on disk untouched.
    """
    with INDEX_LOCK:
        if INDEX_STATE.get("running"):
            INDEX_STATE["stopped"] = True
            INDEX_STATE["paused"] = False
            INDEX_STATE["running"] = False
        APP_CONFIG["db_storage_dir"] = ""
        APP_CONFIG["active_db"] = ""
        APP_CONFIG["databases"] = {}
        APP_CONFIG["watcher_settings"] = {
            "poll_interval_seconds": 3,
            "debounce_delay_seconds": 2.0,
            "max_file_size_mb": 250,
            "ignore_hidden_temp": True
        }
        WATCHER_CONFIG["folder"] = ""
        WATCHER_CONFIG["active"] = False
        sync_active_db_vars()
        save_config()
    send_success(handler, "Application reset successfully. Please choose an index storage folder.")
