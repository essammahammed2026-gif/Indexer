"""
Thread-safe application state, configuration management, and multi-database coordinator.
Zero external pip dependencies.
"""

import os
import json
import time
import tempfile
import sqlite3
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
TEMP_UPLOADS_DIR = os.path.join(tempfile.gettempdir(), "indexer_uploads")
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)
UPLOADS_DIR = TEMP_UPLOADS_DIR  # Backward-compatibility alias

# Global indexing lock for concurrency control
INDEX_LOCK = threading.Lock()

# Global indexing progress state
INDEX_STATE = {
    "running": False,
    "paused": False,
    "stopped": False,
    "total": 0,
    "current": 0,
    "current_file": "",
    "records_indexed": 0,
    "percent": 0,
    "folder": "",
    "status_message": "Idle",
    "db_id": None,
    "db_path": None,
    "nickname": "",
    "completed_db_id": None,
    "completed_nickname": None
}

# Multi-Database & Watcher App Configuration
# Clean defaults: starts with no database loaded and no hardcoded fallback storage
APP_CONFIG = {
    "db_storage_dir": "",
    "active_db": "",
    "databases": {},
    "watcher_settings": {
        "poll_interval_seconds": 3,
        "debounce_delay_seconds": 2.0,
        "max_file_size_mb": 250,
        "ignore_hidden_temp": True
    }
}

DB_PATH = ""
WATCHER_CONFIG = {
    "folder": "",
    "active": False
}

def get_active_db_path():
    """
    Compute absolute file path to the active SQLite database file.
    Returns '' if no database is loaded or if the file does not exist.
    Strictly NO fallbacks to default databases or application directory.
    """
    active_key = APP_CONFIG.get("active_db")
    if not active_key or active_key not in APP_CONFIG.get("databases", {}):
        return ""
    storage_dir = (APP_CONFIG.get("db_storage_dir") or "").strip()
    if not storage_dir or not os.path.isdir(storage_dir):
        return ""
    db_meta = APP_CONFIG.get("databases", {}).get(active_key, {})
    fname = db_meta.get("filename") or ""
    if not fname:
        return ""
    target = os.path.join(storage_dir, fname)
    return target if os.path.exists(target) else ""

def sync_active_db_vars():
    """Keep DB_PATH and WATCHER_CONFIG in sync with the active database profile."""
    global DB_PATH, WATCHER_CONFIG
    DB_PATH = get_active_db_path()
    active_key = APP_CONFIG.get("active_db")
    if active_key and active_key in APP_CONFIG.get("databases", {}):
        db_meta = APP_CONFIG.get("databases", {}).get(active_key, {})
        WATCHER_CONFIG["folder"] = db_meta.get("watch_folder", "")
        WATCHER_CONFIG["active"] = db_meta.get("watch_active", False)
    else:
        WATCHER_CONFIG["folder"] = ""
        WATCHER_CONFIG["active"] = False

def load_config(startup=False):
    """
    Load configuration from config.json.
    Always initializes with active_db = '' (never auto-loads on startup).
    """
    global APP_CONFIG, WATCHER_CONFIG, DB_PATH
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "db_storage_dir" in data:
                APP_CONFIG["db_storage_dir"] = data["db_storage_dir"]
            if "databases" in data and isinstance(data["databases"], dict):
                APP_CONFIG["databases"] = data["databases"]
            if "watcher_settings" in data and isinstance(data["watcher_settings"], dict):
                APP_CONFIG["watcher_settings"].update(data["watcher_settings"])
            # The app must ALWAYS start with no database loaded
            APP_CONFIG["active_db"] = ""
            sync_active_db_vars()
        except Exception as e:
            print(f"[CONFIG] Error loading config: {e}")
            APP_CONFIG["active_db"] = ""
            sync_active_db_vars()
    else:
        APP_CONFIG["active_db"] = ""
        sync_active_db_vars()

def save_config():
    """Persist current configuration to config.json with active_db always unset."""
    try:
        active_key = APP_CONFIG.get("active_db", "")
        if active_key and active_key in APP_CONFIG.get("databases", {}):
            APP_CONFIG["databases"][active_key]["watch_folder"] = WATCHER_CONFIG.get("folder", "")
            APP_CONFIG["databases"][active_key]["watch_active"] = WATCHER_CONFIG.get("active", False)
        payload = dict(APP_CONFIG)
        payload["active_db"] = ""  # Never persist an auto-loaded database
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        print(f"[CONFIG] Error saving config: {e}")
