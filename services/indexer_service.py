"""
Directory and document batch indexing service with live progress updates.
Zero external pip dependencies.
"""

import os
import sqlite3
import threading
import indexer_engine
import storage
from .state import (
    BASE_DIR,
    INDEX_LOCK,
    INDEX_STATE,
    APP_CONFIG,
    WATCHER_CONFIG,
    get_active_db_path,
    save_config
)

SUPPORTED_EXTENSIONS = (
    '.xlsx', '.xls', '.csv', '.tsv',
    '.docx', '.odt', '.txt', '.log', '.json', '.sql', '.pdf',
    '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'
)

def index_single_target(target_path, db_path=None):
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

    if not db_path:
        db_path = get_active_db_path()

    conn = storage.get_connection(db_path)
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

def start_indexing_thread(folder_path, force_reindex=False, force_refresh=False, nickname=None, db_key=None):
    """
    Run folder scan & index with live progress tracking & auto-backup.
    - force_reindex=True: clears existing index and rebuilds from scratch.
    - force_refresh=True: rechecks files against database mtime/size.
    - nickname: Optional nickname for this database.
    - db_key: Optional existing or new database profile key.
    """
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
        try:
            active_db_path = get_active_db_path()
            if os.path.exists(active_db_path):
                storage.backup_database(active_db_path)

            all_files = []
            for root, dirs, files in os.walk(folder_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS and not f.startswith('~$') and not f.startswith('.'):
                        all_files.append(os.path.join(root, f))

            files_to_process = all_files
            conn = storage.get_connection(active_db_path)
            indexer_engine.init_db(conn)

            if force_reindex:
                cur = conn.cursor()
                cur.execute("DELETE FROM files;")
                cur.execute("DELETE FROM cdr_records;")
                cur.execute("DELETE FROM universal_search;")
                cur.execute("DELETE FROM ocr_boxes;")
                conn.commit()

            INDEX_STATE["total"] = len(files_to_process)
            total_records = 0

            for idx, fpath in enumerate(files_to_process):
                fname = os.path.basename(fpath)
                INDEX_STATE["current"] = idx + 1
                INDEX_STATE["current_file"] = fname
                INDEX_STATE["percent"] = round(((idx + 1) / max(len(files_to_process), 1)) * 100, 1)

                try:
                    cnt = indexer_engine.process_file(fpath, conn)
                    total_records += cnt
                    INDEX_STATE["records_indexed"] = total_records
                except Exception as ex:
                    print(f"[INDEX ERROR] {fname}: {ex}")

            conn.close()

            INDEX_STATE["percent"] = 100
            INDEX_STATE["status_message"] = f"Completed! Processed {len(files_to_process)} documents ({total_records:,} searchable entries)"
            
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
