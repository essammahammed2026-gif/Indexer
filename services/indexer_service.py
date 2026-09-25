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

import time

def pause_indexing():
    """Pause active indexing loop."""
    with INDEX_LOCK:
        if INDEX_STATE["running"] and not INDEX_STATE["paused"]:
            INDEX_STATE["paused"] = True
            INDEX_STATE["status_message"] = "Indexing paused"
            return True, "Indexing paused"
    return False, "Indexing is not active or already paused"

def resume_indexing():
    """Resume paused indexing loop."""
    with INDEX_LOCK:
        if INDEX_STATE["running"] and INDEX_STATE["paused"]:
            INDEX_STATE["paused"] = False
            INDEX_STATE["status_message"] = "Indexing resumed..."
            return True, "Indexing resumed"
    return False, "Indexing is not paused"

def stop_indexing():
    """Stop active indexing and delete incomplete database index files from system."""
    with INDEX_LOCK:
        if INDEX_STATE["running"]:
            INDEX_STATE["stopped"] = True
            INDEX_STATE["paused"] = False
            INDEX_STATE["status_message"] = "Stopping and cleaning up index..."
            return True, "Stopping indexing..."
    return False, "Indexing is not active"

def start_indexing_thread(folder_path, force_reindex=False, force_refresh=False, nickname=None, db_key=None, target_db_path=None):
    """
    Run folder scan & index in background with live progress tracking.
    - target_db_path: Path to target database (allows user to keep using current active DB).
    - Supports pause, resume, and stop-with-cleanup.
    """
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return False, f"Folder does not exist: {folder_path}"

    with INDEX_LOCK:
        if INDEX_STATE["running"]:
            return False, "Indexing is already in progress!"
        INDEX_STATE["running"] = True
        INDEX_STATE["paused"] = False
        INDEX_STATE["stopped"] = False
        INDEX_STATE["folder"] = folder_path
        INDEX_STATE["current"] = 0
        INDEX_STATE["total"] = 0
        INDEX_STATE["percent"] = 0
        INDEX_STATE["records_indexed"] = 0
        INDEX_STATE["db_id"] = db_key
        INDEX_STATE["db_path"] = target_db_path or get_active_db_path()
        INDEX_STATE["nickname"] = nickname or (db_key or "Index")
        INDEX_STATE["completed_db_id"] = None
        INDEX_STATE["completed_nickname"] = None

        if force_reindex:
            INDEX_STATE["current_file"] = "Wiping existing index for full rebuild..."
            INDEX_STATE["status_message"] = "Preparing complete re-index..."
        elif force_refresh:
            INDEX_STATE["current_file"] = "Scanning for added, modified or moved documents..."
            INDEX_STATE["status_message"] = "Checking for file changes..."
        else:
            INDEX_STATE["current_file"] = "Scanning folder structure..."
            INDEX_STATE["status_message"] = "Scanning folder..."

    def _worker():
        target_path = INDEX_STATE["db_path"]
        stopped = False
        try:
            if not target_path:
                target_path = get_active_db_path()

            # Fast directory file scan
            all_files = []
            for root, dirs, files in os.walk(folder_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS and not f.startswith('~$') and not f.startswith('.'):
                        all_files.append(os.path.join(root, f))

            INDEX_STATE["total"] = len(all_files)
            if not all_files:
                INDEX_STATE["status_message"] = "No supported files found in folder"
                INDEX_STATE["percent"] = 100
                return

            conn = storage.get_connection(target_path)
            indexer_engine.init_db(conn)

            if force_reindex:
                cur = conn.cursor()
                cur.execute("DELETE FROM files;")
                cur.execute("DELETE FROM cdr_records;")
                cur.execute("DELETE FROM universal_search;")
                cur.execute("DELETE FROM ocr_boxes;")
                conn.commit()

            total_records = 0

            for idx, fpath in enumerate(all_files):
                # Check for stop request
                if INDEX_STATE.get("stopped"):
                    stopped = True
                    break

                # Handle pause loop
                while INDEX_STATE.get("paused") and not INDEX_STATE.get("stopped"):
                    time.sleep(0.3)

                if INDEX_STATE.get("stopped"):
                    stopped = True
                    break

                fname = os.path.basename(fpath)
                INDEX_STATE["current"] = idx + 1
                INDEX_STATE["current_file"] = fname
                INDEX_STATE["percent"] = round(((idx + 1) / max(len(all_files), 1)) * 100, 1)
                INDEX_STATE["status_message"] = f"Indexing file {idx + 1} of {len(all_files)}"

                try:
                    cnt = indexer_engine.process_file(fpath, conn)
                    total_records += cnt
                    INDEX_STATE["records_indexed"] = total_records
                except Exception as ex:
                    print(f"[INDEX ERROR] {fname}: {ex}")

            conn.close()

            if stopped:
                # User pressed Stop -> Delete the unfinished index completely from disk & registry
                INDEX_STATE["status_message"] = "Indexing stopped and index deleted."
                INDEX_STATE["percent"] = 0
                if target_path and os.path.exists(target_path):
                    try:
                        os.remove(target_path)
                        for suff in ["-wal", "-shm"]:
                            if os.path.exists(target_path + suff):
                                os.remove(target_path + suff)
                    except Exception as err:
                        print(f"[CLEANUP ERROR] {err}")
                if db_key and db_key in APP_CONFIG.get("databases", {}):
                    APP_CONFIG["databases"].pop(db_key, None)
                    save_config()
                return

            INDEX_STATE["percent"] = 100
            INDEX_STATE["status_message"] = f"Completed! Processed {len(all_files)} files ({total_records:,} searchable entries)"
            INDEX_STATE["completed_db_id"] = db_key
            INDEX_STATE["completed_nickname"] = nickname or db_key

            # Update database profile with watch folder
            if db_key and db_key in APP_CONFIG.get("databases", {}):
                APP_CONFIG["databases"][db_key]["watch_folder"] = folder_path
                APP_CONFIG["databases"][db_key]["watch_active"] = True
                if nickname:
                    APP_CONFIG["databases"][db_key]["nickname"] = nickname
                save_config()
        except Exception as e:
            INDEX_STATE["status_message"] = f"Error during indexing: {e}"
        finally:
            INDEX_STATE["running"] = False
            INDEX_STATE["paused"] = False
            INDEX_STATE["stopped"] = False

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return True, "Indexing started in background"
