"""
Thread-safe application state, configuration management, and multi-database coordinator.
Zero external pip dependencies.
"""

import os
import json
import time
import sqlite3
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Global indexing lock for concurrency control
INDEX_LOCK = threading.Lock()

# Global indexing progress state
INDEX_STATE = {
    "running": False,
    "total": 0,
    "current": 0,
    "current_file": "",
    "records_indexed": 0,
    "percent": 0,
    "folder": "",
    "status_message": "Idle"
}

# Multi-Database & Watcher App Configuration
APP_CONFIG = {
    "db_storage_dir": BASE_DIR,
    "active_db": "default",
    "databases": {
        "default": {
            "nickname": "Main Database",
            "filename": "sheets_index.db",
            "watch_folder": "",
            "watch_active": False,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    },
    "watcher_settings": {
        "poll_interval_seconds": 3,
        "debounce_delay_seconds": 2.0,
        "max_file_size_mb": 250,
        "ignore_hidden_temp": True
    }
}

DB_PATH = os.path.join(BASE_DIR, "sheets_index.db")
WATCHER_CONFIG = {
    "folder": "",
    "active": False
}

def get_active_db_path():
    """Compute absolute file path to the active SQLite database file."""
    storage_dir = APP_CONFIG.get("db_storage_dir") or BASE_DIR
    try:
        os.makedirs(storage_dir, exist_ok=True)
    except Exception:
        storage_dir = BASE_DIR
    active_key = APP_CONFIG.get("active_db", "default")
    db_meta = APP_CONFIG.get("databases", {}).get(active_key, {})
    fname = db_meta.get("filename") or "sheets_index.db"
    return os.path.join(storage_dir, fname)

def sync_active_db_vars():
    """Keep DB_PATH and WATCHER_CONFIG in sync with the active database profile."""
    global DB_PATH, WATCHER_CONFIG
    DB_PATH = get_active_db_path()
    active_key = APP_CONFIG.get("active_db", "default")
    db_meta = APP_CONFIG.get("databases", {}).get(active_key, {})
    WATCHER_CONFIG["folder"] = db_meta.get("watch_folder", "")
    WATCHER_CONFIG["active"] = db_meta.get("watch_active", False)

def load_config():
    """Load configuration from config.json with migration support."""
    global APP_CONFIG, WATCHER_CONFIG, DB_PATH
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "watch_folder" in data and "databases" not in data:
                old_folder = data.get("watch_folder", "")
                old_active = data.get("watch_active", False)
                APP_CONFIG["databases"]["default"]["watch_folder"] = old_folder
                APP_CONFIG["databases"]["default"]["watch_active"] = old_active
                if old_folder:
                    APP_CONFIG["databases"]["default"]["nickname"] = os.path.basename(old_folder.rstrip('/')) or "Main Database"
            else:
                if "db_storage_dir" in data:
                    APP_CONFIG["db_storage_dir"] = data["db_storage_dir"]
                if "active_db" in data:
                    APP_CONFIG["active_db"] = data["active_db"]
                if "databases" in data and isinstance(data["databases"], dict) and data["databases"]:
                    APP_CONFIG["databases"] = data["databases"]
                if "watcher_settings" in data and isinstance(data["watcher_settings"], dict):
                    APP_CONFIG["watcher_settings"].update(data["watcher_settings"])
            sync_active_db_vars()
        except Exception as e:
            print(f"[CONFIG] Error loading config: {e}")
            sync_active_db_vars()
    else:
        sync_active_db_vars()
        try:
            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT folder FROM files LIMIT 1;")
                row = cur.fetchone()
                if row and row[0]:
                    fld = row[0]
                    while "/FINAL" in fld and not fld.endswith("/FINAL"):
                        fld = os.path.dirname(fld)
                    APP_CONFIG["databases"]["default"]["watch_folder"] = fld
                    APP_CONFIG["databases"]["default"]["watch_active"] = True
                    APP_CONFIG["databases"]["default"]["nickname"] = os.path.basename(fld.rstrip('/')) or "Main Database"
                    sync_active_db_vars()
                    save_config()
                conn.close()
        except Exception:
            pass

def save_config():
    """Persist current configuration to config.json."""
    try:
        active_key = APP_CONFIG.get("active_db", "default")
        if active_key in APP_CONFIG.get("databases", {}):
            APP_CONFIG["databases"][active_key]["watch_folder"] = WATCHER_CONFIG.get("folder", "")
            APP_CONFIG["databases"][active_key]["watch_active"] = WATCHER_CONFIG.get("active", False)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(APP_CONFIG, f, indent=2)
    except Exception as e:
        print(f"[CONFIG] Error saving config: {e}")
