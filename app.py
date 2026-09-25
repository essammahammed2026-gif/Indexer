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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PORT = 8088

# Storage directory for user-uploaded scoped files & images
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Global indexing and watcher states
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

INDEX_LOCK = threading.Lock()

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
    """Keep global DB_PATH and WATCHER_CONFIG in sync with the active database profile."""
    global DB_PATH, WATCHER_CONFIG
    DB_PATH = get_active_db_path()
    active_key = APP_CONFIG.get("active_db", "default")
    db_meta = APP_CONFIG.get("databases", {}).get(active_key, {})
    WATCHER_CONFIG["folder"] = db_meta.get("watch_folder", "")
    WATCHER_CONFIG["active"] = db_meta.get("watch_active", False)

def load_config():
    global APP_CONFIG, WATCHER_CONFIG, DB_PATH
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Backward compatibility migration from old config format
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
        # Default initialization
        sync_active_db_vars()
        # If default sheets_index.db already exists in BASE_DIR, initialize from it
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
    try:
        active_key = APP_CONFIG.get("active_db", "default")
        if active_key in APP_CONFIG.get("databases", {}):
            APP_CONFIG["databases"][active_key]["watch_folder"] = WATCHER_CONFIG.get("folder", "")
            APP_CONFIG["databases"][active_key]["watch_active"] = WATCHER_CONFIG.get("active", False)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(APP_CONFIG, f, indent=2)
    except Exception as e:
        print(f"[CONFIG] Error saving config: {e}")


def get_stats():
    active_key = APP_CONFIG.get("active_db", "default")
    db_meta = APP_CONFIG.get("databases", {}).get(active_key, {})
    nickname = db_meta.get("nickname", "Main Database")
    storage_dir = APP_CONFIG.get("db_storage_dir", BASE_DIR)
    folder = WATCHER_CONFIG.get("folder", "")
    res = storage.get_stats(DB_PATH, folder=folder, active_key=active_key, nickname=nickname, storage_dir=storage_dir)
    res["watcher"] = WATCHER_CONFIG.get("active", False)
    return res

def get_quick_filters():
    return storage.get_quick_filters(DB_PATH)

def add_quick_filter(name, query):
    return storage.add_quick_filter(DB_PATH, name, query)

def delete_quick_filter(filter_id):
    return storage.delete_quick_filter(DB_PATH, filter_id)

# Bookmark Helpers
def get_bookmarks():
    return storage.get_bookmarks(DB_PATH)

def add_bookmark(file_path, sheet_name, row_idx, tag="Lead", notes=""):
    return storage.add_bookmark(DB_PATH, file_path, sheet_name, row_idx, tag=tag, notes=notes)

def remove_bookmark(file_path, sheet_name, row_idx):
    return storage.remove_bookmark(DB_PATH, file_path, sheet_name, row_idx)

def get_context_window(file_path, sheet_name, row_idx, window=3):
    return storage.get_context_window(DB_PATH, file_path, sheet_name, row_idx, window=window)

def get_ocr_boxes(file_path, sheet_name="Image"):
    """Retrieve OCR bounding boxes, dimensions, and extracted text lines for an image or PDF page."""
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS ocr_boxes (id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT NOT NULL, sheet_name TEXT NOT NULL, img_width INTEGER, img_height INTEGER, boxes_json TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(file_path, sheet_name));")
        cur.execute("""
        SELECT img_width, img_height, boxes_json FROM ocr_boxes
        WHERE file_path = ? AND sheet_name = ?;
        """, (file_path, sheet_name))
        row = cur.fetchone()
        
        # Also query extracted text lines from universal_search
        lines = []
        try:
            cur.execute("""
            SELECT content FROM universal_search
            WHERE file_path = ? AND sheet_name = ?
            ORDER BY CAST(row_idx AS INTEGER) ASC;
            """, (file_path, sheet_name))
            lines = [r[0] for r in cur.fetchall() if r[0] and r[0].strip()]
        except Exception:
            pass

        # If bounding boxes are not in database yet and file exists, generate on-demand!
        if not row and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'):
                try:
                    import indexer_engine
                    text, boxes = indexer_engine.run_ocr_detailed(file_path)
                    w, h = indexer_engine.get_image_dimensions(file_path)
                    if boxes:
                        cur.execute("""
                        INSERT INTO ocr_boxes (file_path, sheet_name, img_width, img_height, boxes_json)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(file_path, sheet_name) DO UPDATE SET
                            img_width = excluded.img_width,
                            img_height = excluded.img_height,
                            boxes_json = excluded.boxes_json;
                        """, (file_path, sheet_name, w, h, json.dumps(boxes, ensure_ascii=False)))
                        conn.commit()
                        row = (w, h, json.dumps(boxes, ensure_ascii=False))
                    if not lines and text:
                        lines = [l.strip() for l in text.splitlines() if l.strip()]
                except Exception as ex:
                    print(f"[ON-DEMAND OCR ERROR] {ex}")

        conn.close()
        if row:
            return {
                "width": row[0],
                "height": row[1],
                "boxes": json.loads(row[2]),
                "lines": lines
            }
        elif lines:
            return {
                "width": None,
                "height": None,
                "boxes": [],
                "lines": lines
            }
        return None
    except Exception as e:
        print(f"[OCR BOXES ERROR] {e}")
        return None

def backup_database():
    return storage.backup_database(DB_PATH)

def record_change_event(event_type, file_path, old_path=None, records_count=0, details=""):
    return storage.record_change_event(DB_PATH, event_type, file_path, old_path=old_path, records_count=records_count, details=details)

def get_change_events(limit=50, offset=0, unread_only=False):
    return storage.get_change_events(DB_PATH, limit=limit, offset=offset, unread_only=unread_only)

def mark_change_events_read(event_ids=None):
    return storage.mark_change_events_read(DB_PATH, event_ids=event_ids)

def clear_all_change_events():
    return storage.clear_all_change_events(DB_PATH)



def query_db(query, limit=50, offset=0, scope_file=None, scope_folder=None, mode="general"):
    return storage.query_db(DB_PATH, query, limit=limit, offset=offset, scope_file=scope_file, scope_folder=scope_folder, mode=mode)

def index_single_target(target_path):
    """
    Synchronously index a single file or a folder (used by the Scoped Target Search tab).
    Returns (ok: bool, message: str, count: int, scanned_files: list).
    """
    target_path = os.path.abspath(target_path)
    if not os.path.exists(target_path):
        return False, f"Target path does not exist: {target_path}", 0, []

    files_to_index = []
    if os.path.isdir(target_path):
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS and not f.startswith('~$') and not f.startswith('.'):
                    files_to_index.append(os.path.join(root, f))
    else:
        files_to_index = [target_path]

    if not files_to_index:
        return False, "No supported documents or spreadsheets found in selection", 0, []

    conn = sqlite3.connect(DB_PATH)
    indexer_engine.init_db(conn)
    total_cnt = 0
    scanned = []
    for fpath in files_to_index:
        try:
            cnt = indexer_engine.process_file(fpath, conn)
            total_cnt += cnt
            scanned.append({"file": os.path.basename(fpath), "path": fpath, "records": cnt})
        except Exception as e:
            print(f"[SCOPED INDEX ERROR] {fpath}: {e}")

    conn.close()
    return True, f"Indexed {len(files_to_index)} item(s) successfully ({total_cnt:,} records)", total_cnt, scanned

SUPPORTED_EXTENSIONS = (
    '.xlsx', '.xls', '.csv', '.tsv',
    '.docx', '.odt', '.txt', '.log', '.json', '.sql', '.pdf',
    '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'
)

def start_indexing_thread(folder_path, force_reindex=False, force_refresh=False, nickname=None, db_key=None):
    """
    Run folder scan & index with live progress tracking & auto-backup.
    - force_reindex=True: clears existing index (files, cdr, universal_search, ocr) and indexes everything from scratch.
    - force_refresh=True: rechecks all files against database mtime/size, updates modified/added files, removes missing files without full re-index.
    - nickname: Optional human-readable nickname for this database.
    - db_key: Optional existing or new database profile key.
    """
    global INDEX_STATE
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return False, f"Folder does not exist: {folder_path}"

    with INDEX_LOCK:
        if INDEX_STATE["running"]:
            return False, "Indexing is already in progress!"
        INDEX_STATE["running"] = True
        INDEX_STATE["folder"] = folder_path
        INDEX_STATE["current"] = 0
        INDEX_STATE["total"] = 0
        INDEX_STATE["percent"] = 0
        INDEX_STATE["records_indexed"] = 0
        if force_reindex:
            INDEX_STATE["current_file"] = "Creating safety backup & wiping index for full rebuild..."
            INDEX_STATE["status_message"] = "Preparing complete re-index..."
        elif force_refresh:
            INDEX_STATE["current_file"] = "Scanning for added, modified or moved documents..."
            INDEX_STATE["status_message"] = "Checking for file changes..."
        else:
            INDEX_STATE["current_file"] = "Creating safety backup & scanning folder..."
            INDEX_STATE["status_message"] = "Scanning folder..."

    def _worker():
        global INDEX_STATE, DB_PATH
        try:
            # 1. Automatic safety snapshot before starting index if database exists
            if os.path.exists(DB_PATH):
                backup_database()

            conn = sqlite3.connect(DB_PATH)
            indexer_engine.init_db(conn)

            # If force_reindex: reset index tables (preserve bookmarks and quick_filters)
            if force_reindex:
                print(f"[RE-INDEX] Wiping current index data for fresh re-index of {folder_path}...")
                conn.execute("DELETE FROM cdr_records;")
                conn.execute("DELETE FROM universal_search;")
                conn.execute("DELETE FROM ocr_boxes;")
                conn.execute("DELETE FROM files;")
                conn.commit()
                record_change_event(
                    event_type="reindex_started",
                    file_path=folder_path,
                    details="Full index rebuild initiated"
                )

            # Collect existing files in DB
            db_files = {}
            if not force_reindex:
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT file_path, filename FROM files;")
                    for fp, fn in cur.fetchall():
                        db_files[fp] = fn
                except Exception:
                    pass

            files_to_scan = []
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS and not f.startswith('~$') and not f.startswith('.'):
                        files_to_scan.append(os.path.join(root, f))

            INDEX_STATE["total"] = len(files_to_scan)
            if not files_to_scan:
                INDEX_STATE["percent"] = 100
                INDEX_STATE["status_message"] = "No supported document, sheet, or image files found in folder"
                INDEX_STATE["running"] = False
                conn.close()
                return

            # In force_refresh mode: determine which files actually need indexing or were deleted/moved
            files_to_process = files_to_scan
            removed_count = 0
            if force_refresh and not force_reindex:
                current_set = set(files_to_scan)
                # Check for removed or renamed files in DB
                for old_fp in list(db_files.keys()):
                    if old_fp.startswith(folder_path) and old_fp not in current_set:
                        old_name = db_files[old_fp]
                        matched_rename = None
                        for cur_fp in files_to_scan:
                            if cur_fp not in db_files and os.path.basename(cur_fp) == old_name:
                                matched_rename = cur_fp
                                break

                        cur = conn.cursor()
                        cur.execute("SELECT file_id FROM files WHERE file_path = ?;", (old_fp,))
                        row = cur.fetchone()
                        if row:
                            fid = row[0]
                            cur.execute("DELETE FROM cdr_records WHERE file_id = ?;", (fid,))
                            cur.execute("DELETE FROM universal_search WHERE file_path = ?;", (old_fp,))
                            cur.execute("DELETE FROM ocr_boxes WHERE file_path = ?;", (old_fp,))
                            cur.execute("DELETE FROM files WHERE file_id = ?;", (fid,))
                            conn.commit()

                        if matched_rename:
                            record_change_event(
                                event_type="renamed",
                                file_path=matched_rename,
                                old_path=old_fp,
                                details=f"Moved/renamed from {os.path.basename(old_fp)} to {os.path.basename(matched_rename)}"
                            )
                        else:
                            record_change_event(
                                event_type="deleted",
                                file_path=old_fp,
                                details=f"File deleted or moved out of watch directory"
                            )
                        removed_count += 1

                # Filter files_to_process: only newly added or modified since indexed_at
                cur = conn.cursor()
                cur.execute("SELECT file_path, indexed_at FROM files;")
                db_indexed = {r[0]: r[1] for r in cur.fetchall()}

                needed = []
                for fp in files_to_scan:
                    if fp not in db_indexed:
                        needed.append(fp)
                    else:
                        try:
                            mtime = os.path.getmtime(fp)
                            idx_str = db_indexed[fp]
                            idx_time = time.mktime(time.strptime(idx_str, "%Y-%m-%d %H:%M:%S")) if idx_str else 0
                            if mtime > idx_time:
                                needed.append(fp)
                        except Exception:
                            needed.append(fp)
                files_to_process = needed
                INDEX_STATE["total"] = len(files_to_process)
                if not files_to_process:
                    INDEX_STATE["percent"] = 100
                    INDEX_STATE["status_message"] = f"Index is up to date! ({len(files_to_scan)} documents checked, {removed_count} pruned)"
                    INDEX_STATE["running"] = False
                    conn.close()
                    return

            total_records = 0
            completed = 0
            for fpath in files_to_process:
                fname = os.path.basename(fpath)
                completed += 1
                INDEX_STATE["current"] = completed
                INDEX_STATE["current_file"] = fname
                INDEX_STATE["percent"] = int((completed / len(files_to_process)) * 100)
                INDEX_STATE["status_message"] = f"Indexing {completed}/{len(files_to_process)}: {fname}"

                is_new = (fpath not in db_files)
                try:
                    cnt = indexer_engine.process_file(fpath, conn)
                    total_records += cnt
                    INDEX_STATE["records_indexed"] = total_records

                    # If force_refresh or single refresh, record change notification
                    if force_refresh:
                        record_change_event(
                            event_type="added" if is_new else "modified",
                            file_path=fpath,
                            records_count=cnt,
                            details=f"{'Added new file' if is_new else 'Updated modified file'} with {cnt:,} records"
                        )
                except Exception as ex:
                    print(f"[INDEX ERROR] {fname}: {ex}")

            if force_reindex:
                record_change_event(
                    event_type="reindex_completed",
                    file_path=folder_path,
                    records_count=total_records,
                    details=f"Full re-index complete: {len(files_to_process)} files ({total_records:,} records)"
                )

            conn.close()

            INDEX_STATE["percent"] = 100
            INDEX_STATE["status_message"] = f"Completed! Processed {len(files_to_process)} documents ({total_records:,} searchable entries)"
            
            # Automatically update watch folder & database registry
            WATCHER_CONFIG["folder"] = folder_path
            WATCHER_CONFIG["active"] = True
            active_key = APP_CONFIG.get("active_db", "default")
            if active_key in APP_CONFIG.get("databases", {}):
                APP_CONFIG["databases"][active_key]["watch_folder"] = folder_path
                APP_CONFIG["databases"][active_key]["watch_active"] = True
                if nickname:
                    APP_CONFIG["databases"][active_key]["nickname"] = nickname
            save_config()
        except Exception as e:
            INDEX_STATE["status_message"] = f"Error during indexing: {e}"
        finally:
            INDEX_STATE["running"] = False

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return True, "Indexing started"

# Background Folder Watcher
def folder_watcher_loop():
    known_files = {} # {path: (mtime, size)}
    
    while True:
        try:
            folder = WATCHER_CONFIG.get("folder")
            active = WATCHER_CONFIG.get("active", False)
            w_settings = APP_CONFIG.get("watcher_settings", {})
            poll_interval = max(1, int(w_settings.get("poll_interval_seconds", 3)))
            debounce_sec = max(0.5, float(w_settings.get("debounce_delay_seconds", 2.0)))
            max_size_mb = float(w_settings.get("max_file_size_mb", 250))
            ignore_hidden_temp = bool(w_settings.get("ignore_hidden_temp", True))
            max_bytes = max_size_mb * 1024 * 1024 if max_size_mb > 0 else float('inf')
            
            if active and folder and os.path.exists(folder) and os.path.isdir(folder) and not INDEX_STATE["running"]:
                current_files = {}
                for root, dirs, files in os.walk(folder):
                    # Prune hidden directories
                    if ignore_hidden_temp:
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for f in files:
                        if ignore_hidden_temp and (f.startswith('~$') or f.startswith('.')):
                            continue
                        ext = os.path.splitext(f)[1].lower()
                        if ext in SUPPORTED_EXTENSIONS:
                            full_p = os.path.join(root, f)
                            try:
                                stat = os.stat(full_p)
                                if stat.st_size <= max_bytes:
                                    current_files[full_p] = (stat.st_mtime, stat.st_size)
                            except Exception:
                                pass

                # If first run on this database, check which files are in DB
                if not known_files and os.path.exists(DB_PATH):
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute("SELECT file_path FROM files;")
                        for (fp,) in cur.fetchall():
                            if fp in current_files:
                                known_files[fp] = current_files[fp]
                        conn.close()
                    except Exception:
                        pass

                # Detect newly added or modified files
                changed_files = []
                for p, st in current_files.items():
                    if p not in known_files or known_files[p] != st:
                        changed_files.append(p)

                # Detect deleted or moved files
                missing_files = []
                for p in list(known_files.keys()):
                    if p not in current_files:
                        missing_files.append(p)

                # Process missing (deleted / renamed) files
                if missing_files and not INDEX_STATE["running"]:
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        indexer_engine.init_db(conn)
                        for mp in missing_files:
                            old_name = os.path.basename(mp)
                            renamed_to = None
                            for cf in changed_files:
                                if os.path.basename(cf) == old_name:
                                    renamed_to = cf
                                    break

                            # Clean old path from database
                            cur = conn.cursor()
                            cur.execute("SELECT file_id FROM files WHERE file_path = ?;", (mp,))
                            row = cur.fetchone()
                            if row:
                                fid = row[0]
                                cur.execute("DELETE FROM cdr_records WHERE file_id = ?;", (fid,))
                                cur.execute("DELETE FROM universal_search WHERE file_path = ?;", (mp,))
                                cur.execute("DELETE FROM ocr_boxes WHERE file_path = ?;", (mp,))
                                cur.execute("DELETE FROM files WHERE file_id = ?;", (fid,))
                                conn.commit()

                            del known_files[mp]

                            if renamed_to:
                                record_change_event(
                                    event_type="renamed",
                                    file_path=renamed_to,
                                    old_path=mp,
                                    details=f"File moved or renamed from {os.path.basename(mp)} to {os.path.basename(renamed_to)}"
                                )
                                print(f"[WATCHER] Detected file rename: {mp} -> {renamed_to}")
                            else:
                                record_change_event(
                                    event_type="deleted",
                                    file_path=mp,
                                    details="File was removed or deleted from watched directory"
                                )
                                print(f"[WATCHER] Detected file removal: {mp}")
                        conn.close()
                    except Exception as e:
                        print(f"[WATCHER ERROR] Failed to clean removed files: {e}")

                # Process newly added or modified files
                if changed_files and not INDEX_STATE["running"]:
                    # Debounce check: ensure files have settled (size & mtime steady for debounce_sec)
                    time.sleep(debounce_sec)
                    ready_files = []
                    for cf in changed_files:
                        try:
                            st_now = os.stat(cf)
                            if (st_now.st_mtime, st_now.st_size) == current_files.get(cf):
                                ready_files.append(cf)
                        except Exception:
                            pass

                    if ready_files:
                        print(f"[WATCHER] Processing {len(ready_files)} settled file(s) in {folder}")
                        conn = sqlite3.connect(DB_PATH)
                        indexer_engine.init_db(conn)
                        for cf in ready_files:
                            is_new_file = cf not in known_files
                            print(f"[WATCHER] Auto-indexing: {os.path.basename(cf)}")
                            cnt = 0
                            try:
                                cnt = indexer_engine.process_file(cf, conn)
                                print(f"[WATCHER] Indexed {cnt} records from {os.path.basename(cf)}")
                                
                                record_change_event(
                                    event_type="added" if is_new_file else "modified",
                                    file_path=cf,
                                    records_count=cnt,
                                    details=f"{'Added new file' if is_new_file else 'Updated modified file'} with {cnt:,} searchable entries"
                                )
                            except Exception as e:
                                print(f"[WATCHER ERROR] Failed to index {cf}: {e}")
                            
                            try:
                                st = os.stat(cf)
                                known_files[cf] = (st.st_mtime, st.st_size)
                            except Exception:
                                known_files[cf] = current_files.get(cf)
                        conn.close()
        except Exception as e:
            print(f"[WATCHER ERROR] Loop error: {e}")
            
        time.sleep(poll_interval)

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
