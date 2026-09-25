"""
Application configuration and watcher settings HTTP handlers.
Zero external pip dependencies.
"""

import os
from services import (
    BASE_DIR,
    APP_CONFIG,
    sync_active_db_vars,
    save_config
)
from ..http_utils import read_json_body, send_json, send_success, send_error

def handle_get_settings(handler, parsed):
    send_success(
        handler,
        db_storage_dir=APP_CONFIG.get("db_storage_dir", BASE_DIR),
        watcher_settings=APP_CONFIG.get("watcher_settings", {}),
        active_db=APP_CONFIG.get("active_db", "default")
    )

def handle_save_settings(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    try:
        storage_dir = (data or {}).get("db_storage_dir", "").strip()
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
        send_success(handler, "Settings saved successfully")
    except Exception as e:
        send_error(handler, str(e), 500)
