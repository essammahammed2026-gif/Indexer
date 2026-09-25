"""
Background folder watcher service for real-time document indexing and change tracking.
Zero external pip dependencies.
"""

import os
import time
import sqlite3
import indexer_engine
import storage
from .state import (
    BASE_DIR,
    INDEX_STATE,
    APP_CONFIG,
    WATCHER_CONFIG,
    get_active_db_path
)
from .indexer_service import SUPPORTED_EXTENSIONS

def folder_watcher_loop():
    """
    Continuous background loop that polls the watched directory for modifications,
    new additions, deletions, or renames, debounces I/O, and updates SQLite.
    """
    known_files = {}  # {path: (mtime, size)}
    
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
            db_path = get_active_db_path()
            
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
                if not known_files and os.path.exists(db_path):
                    try:
                        conn = storage.get_connection(db_path)
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
                        conn = storage.get_connection(db_path)
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
                                storage.record_change_event(
                                    db_path,
                                    event_type="renamed",
                                    file_path=renamed_to,
                                    old_path=mp,
                                    details=f"File moved or renamed from {os.path.basename(mp)} to {os.path.basename(renamed_to)}"
                                )
                                print(f"[WATCHER] Detected file rename: {mp} -> {renamed_to}")
                            else:
                                storage.record_change_event(
                                    db_path,
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
                        conn = storage.get_connection(db_path)
                        indexer_engine.init_db(conn)
                        for cf in ready_files:
                            is_new_file = cf not in known_files
                            print(f"[WATCHER] Auto-indexing: {os.path.basename(cf)}")
                            cnt = 0
                            try:
                                cnt = indexer_engine.process_file(cf, conn)
                                print(f"[WATCHER] Indexed {cnt} records from {os.path.basename(cf)}")
                                
                                storage.record_change_event(
                                    db_path,
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
