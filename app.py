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
import indexer_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sheets_index.db")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PORT = 8088

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

WATCHER_CONFIG = {
    "folder": "",
    "active": False
}

INDEX_LOCK = threading.Lock()

def load_config():
    global WATCHER_CONFIG
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                WATCHER_CONFIG["folder"] = data.get("watch_folder", "")
                WATCHER_CONFIG["active"] = data.get("watch_active", True if WATCHER_CONFIG["folder"] else False)
        except Exception as e:
            print(f"[CONFIG] Error loading config: {e}")
    else:
        # Infer default folder from existing database if available
        try:
            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT folder FROM files LIMIT 1;")
                row = cur.fetchone()
                if row and row[0]:
                    # Find common parent or top directory
                    fld = row[0]
                    while "/FINAL" in fld and not fld.endswith("/FINAL"):
                        fld = os.path.dirname(fld)
                    WATCHER_CONFIG["folder"] = fld
                    WATCHER_CONFIG["active"] = True
                    save_config()
                conn.close()
        except Exception:
            pass

def save_config():
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "watch_folder": WATCHER_CONFIG["folder"],
                "watch_active": WATCHER_CONFIG["active"]
            }, f, indent=2)
    except Exception as e:
        print(f"[CONFIG] Error saving config: {e}")

def open_in_app(file_path, sheet_name=None, row_idx=None):
    if not file_path or not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    ext = os.path.splitext(file_path)[1].lower()
    env = os.environ.copy()
    abs_p = os.path.abspath(file_path)
    
    # Try LibreOffice Calc for spreadsheet files
    if ext in ('.xlsx', '.xls', '.csv', '.ods'):
        quoted_path = urllib.parse.quote(abs_p)
        if sheet_name and row_idx:
            uri = f"file://{quoted_path}#{sheet_name}.A{row_idx}"
        elif row_idx:
            uri = f"file://{quoted_path}#A{row_idx}"
        else:
            uri = f"file://{quoted_path}"
            
        try:
            subprocess.Popen(
                ['localc', '--norestore', uri],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return True, f"Opening in Calc at Row {row_idx or 1}"
        except Exception:
            pass

    # Fallback to system default application (xdg-open)
    try:
        subprocess.Popen(
            ['xdg-open', abs_p],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True, "Opened with default application"
    except Exception as e:
        return False, str(e)

def reveal_in_folder(file_path):
    if not file_path:
        return False, "File path is empty"
    abs_p = os.path.abspath(file_path)
    folder = abs_p if os.path.isdir(abs_p) else os.path.dirname(abs_p)
    if not os.path.exists(folder):
        return False, f"Folder not found: {folder}"
    try:
        subprocess.Popen(
            ['xdg-open', folder],
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True, f"Opened folder: {folder}"
    except Exception as e:
        return False, str(e)

def normalize_phone(val):
    if not val:
        return ""
    digits = re.sub(r'\D', '', str(val))
    if digits.startswith('20') and len(digits) in (12, 13, 14):
        if len(digits) == 12:
            return '0' + digits[2:]
    if len(digits) == 10 and digits[0] == '1':
        return '0' + digits
    if len(digits) == 11 and digits.startswith('01'):
        return digits
    return digits

def normalize_arabic(text):
    if not text:
        return ""
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'ى', 'ي', text)
    return text.strip()

def get_stats():
    if not os.path.exists(DB_PATH):
        return {"files": 0, "records": 0}
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM files;")
        total_files = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM cdr_records;")
        total_records = cur.fetchone()[0]
        conn.close()
        return {"files": total_files, "records": total_records}
    except Exception:
        return {"files": 0, "records": 0}

def get_quick_filters():
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS quick_filters (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, query TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        cur.execute("SELECT id, name, query FROM quick_filters ORDER BY id ASC;")
        rows = [{"id": r[0], "name": r[1], "query": r[2]} for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[FILTER ERROR] {e}")
        return []

def add_quick_filter(name, query):
    if not name or not query:
        return False, "Name and query are required"
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS quick_filters (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, query TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        cur.execute("INSERT INTO quick_filters (name, query) VALUES (?, ?);", (name.strip(), query.strip()))
        conn.commit()
        conn.close()
        return True, "Filter saved"
    except Exception as e:
        return False, str(e)

def delete_quick_filter(filter_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM quick_filters WHERE id = ?;", (filter_id,))
        conn.commit()
        conn.close()
        return True, "Filter deleted"
    except Exception as e:
        return False, str(e)


def query_db(query, limit=50, offset=0):
    if not os.path.exists(DB_PATH):
        return {"rows": [], "total": 0, "limit": limit, "offset": offset}
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    query = (query or "").strip()
    if not query:
        conn.close()
        return {"rows": [], "total": 0, "limit": limit, "offset": offset}

    norm_p = normalize_phone(query)
    norm_a = normalize_arabic(query)
    pattern = f"%{query}%"

    # Fast check: If user typed prefix:015 or looking for prefix aggregates
    if query.lower().startswith("prefix:") or (query.isdigit() and len(query) in (3, 4) and query.startswith("01")):
        prefix_val = query.replace("prefix:", "").strip()
        norm_pfx = normalize_phone(prefix_val) if len(prefix_val) > 2 else prefix_val
        pfx_pat = f"{norm_pfx}%"
        
        count_sql = """
        SELECT COUNT(DISTINCT c.other_norm)
        FROM cdr_records c
        WHERE c.other_norm LIKE ? OR c.target_norm LIKE ?;
        """
        cur.execute(count_sql, (pfx_pat, pfx_pat))
        total_cnt = cur.fetchone()[0] or 0

        sql = """
        SELECT c.other_norm, c.other_name, COUNT(*) as cnt, GROUP_CONCAT(DISTINCT f.filename) as src_files
        FROM cdr_records c
        JOIN files f ON c.file_id = f.file_id
        WHERE c.other_norm LIKE ? OR c.target_norm LIKE ?
        GROUP BY c.other_norm
        ORDER BY cnt DESC
        LIMIT ? OFFSET ?;
        """
        cur.execute(sql, (pfx_pat, pfx_pat, limit, offset))
        results = []
        for r in cur.fetchall():
            if r[0]:
                results.append({
                    "phone": r[0],
                    "name": r[1] or "—",
                    "count": r[2],
                    "files": r[3] or "—"
                })
        conn.close()
        return {"type": "prefix", "rows": results, "total": total_cnt, "limit": limit, "offset": offset}

    # 1. Search in structured CDR records
    count_sql = """
    SELECT COUNT(*)
    FROM cdr_records c
    WHERE c.target_norm = ? 
       OR c.other_norm = ? 
       OR c.target_msisdn LIKE ? 
       OR c.other_msisdn LIKE ?
       OR (length(?) > 1 AND c.other_name_norm LIKE ?)
       OR c.other_name LIKE ?
       OR c.other_id LIKE ?
       OR c.raw_row LIKE ?;
    """
    cur.execute(count_sql, (
        norm_p or query,
        norm_p or query,
        pattern,
        pattern,
        norm_a,
        f"%{norm_a}%",
        pattern,
        pattern,
        pattern
    ))
    total_count = cur.fetchone()[0] or 0

    if total_count > 0:
        sql = """
        SELECT f.filename, c.sheet_name, c.row_idx, c.event_time, c.direction, 
               c.target_msisdn, c.other_msisdn, c.other_name, c.duration, c.cell_address, 
               f.file_path, c.raw_row
        FROM cdr_records c
        JOIN files f ON c.file_id = f.file_id
        WHERE c.target_norm = ? 
           OR c.other_norm = ? 
           OR c.target_msisdn LIKE ? 
           OR c.other_msisdn LIKE ?
           OR (length(?) > 1 AND c.other_name_norm LIKE ?)
           OR c.other_name LIKE ?
           OR c.other_id LIKE ?
           OR c.raw_row LIKE ?
        ORDER BY c.event_time DESC
        LIMIT ? OFFSET ?;
        """
        cur.execute(sql, (
            norm_p or query,
            norm_p or query,
            pattern,
            pattern,
            norm_a,
            f"%{norm_a}%",
            pattern,
            pattern,
            pattern,
            limit,
            offset
        ))
        rows = cur.fetchall()
        conn.close()

        cdr_rows = []
        for r in rows:
            raw_text = r[11] or ""
            cdr_rows.append({
                "file": r[0],
                "sheet": r[1],
                "row": r[2],
                "time": r[3] or "—",
                "dir": r[4] or "—",
                "target": r[5] or "—",
                "other": r[6] or "—",
                "name": r[7] or "—",
                "extra": r[8] or "—",
                "address": r[9] or "—",
                "path": r[10],
                "snippet": raw_text[:400] if raw_text else "—"
            })
        return {"type": "cdr", "rows": cdr_rows, "total": total_count, "limit": limit, "offset": offset}

    # 2. Universal Full-Text Search (FTS) fallback for documents, logs, unmapped columns
    clean_q = query.replace('"', ' ')
    safe_fts = f'"{clean_q}"'
    fts_count_sql = "SELECT COUNT(*) FROM universal_search WHERE universal_search MATCH ?;"
    try:
        cur.execute(fts_count_sql, (safe_fts,))
        total_fts = cur.fetchone()[0] or 0
    except Exception:
        total_fts = 0

    if total_fts > 0:
        sql_fts = """
        SELECT u.file_path, u.sheet_name, u.row_idx, u.content,
               c.event_time, c.direction, c.target_msisdn, c.other_msisdn, c.other_name, c.duration, c.cell_address
        FROM universal_search u
        JOIN files f ON u.file_path = f.file_path
        LEFT JOIN cdr_records c ON c.file_id = f.file_id AND c.sheet_name = u.sheet_name AND c.row_idx = u.row_idx
        WHERE universal_search MATCH ?
        LIMIT ? OFFSET ?;
        """
        cur.execute(sql_fts, (safe_fts, limit, offset))
        raw_rows = cur.fetchall()
        conn.close()

        results = []
        for r in raw_rows:
            content_str = r[3] or ""
            results.append({
                "file": os.path.basename(r[0]),
                "sheet": r[1],
                "row": r[2],
                "time": r[4] or "—",
                "dir": r[5] or "—",
                "target": r[6] or "—",
                "other": r[7] or "—",
                "name": r[8] or "—",
                "extra": r[9] or "—",
                "address": r[10] or r[3],
                "path": r[0],
                "snippet": content_str[:400] if content_str else "—"
            })
        return {"type": "cdr", "rows": results, "total": total_fts, "limit": limit, "offset": offset}

    conn.close()
    return {"type": "cdr", "rows": [], "total": 0, "limit": limit, "offset": offset}

SUPPORTED_EXTENSIONS = (
    '.xlsx', '.xls', '.csv', '.tsv',
    '.docx', '.odt', '.txt', '.log', '.json', '.sql', '.pdf'
)

def start_indexing_thread(folder_path):
    """Run full folder scan & index in background with live progress tracking"""
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
        INDEX_STATE["current_file"] = "Scanning folder..."
        INDEX_STATE["status_message"] = "Scanning folder..."

    def _worker():
        global INDEX_STATE
        try:
            files_to_scan = []
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS and not f.startswith('~$') and not f.startswith('.'):
                        files_to_scan.append(os.path.join(root, f))

            INDEX_STATE["total"] = len(files_to_scan)
            if not files_to_scan:
                INDEX_STATE["percent"] = 100
                INDEX_STATE["status_message"] = "No supported document or spreadsheet files found in folder"
                INDEX_STATE["running"] = False
                return

            conn = sqlite3.connect(DB_PATH)
            indexer_engine.init_db(conn)
            total_records = 0

            for i, fpath in enumerate(files_to_scan, 1):
                fname = os.path.basename(fpath)
                INDEX_STATE["current"] = i
                INDEX_STATE["current_file"] = fname
                INDEX_STATE["percent"] = int((i / len(files_to_scan)) * 100)
                INDEX_STATE["status_message"] = f"Indexing {i}/{len(files_to_scan)}: {fname}"

                try:
                    count = indexer_engine.process_file(fpath, conn)
                    total_records += count
                    INDEX_STATE["records_indexed"] = total_records
                except Exception as ex:
                    print(f"[INDEX ERROR] {fname}: {ex}")

            conn.close()
            INDEX_STATE["percent"] = 100
            INDEX_STATE["status_message"] = f"Completed! Indexed {len(files_to_scan)} documents ({total_records:,} searchable entries)"
            
            # Automatically update watch folder
            WATCHER_CONFIG["folder"] = folder_path
            WATCHER_CONFIG["active"] = True
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
    
    # Initialize cache from database
    while True:
        try:
            folder = WATCHER_CONFIG.get("folder")
            active = WATCHER_CONFIG.get("active", False)
            
            if active and folder and os.path.exists(folder) and os.path.isdir(folder) and not INDEX_STATE["running"]:
                current_files = {}
                for root, dirs, files in os.walk(folder):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in SUPPORTED_EXTENSIONS and not f.startswith('~$') and not f.startswith('.'):
                            full_p = os.path.join(root, f)
                            try:
                                stat = os.stat(full_p)
                                current_files[full_p] = (stat.st_mtime, stat.st_size)
                            except Exception:
                                pass

                # If first run, check which files are not in DB
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

                if changed_files and not INDEX_STATE["running"]:
                    print(f"[WATCHER] Detected {len(changed_files)} new/modified files in {folder}")
                    conn = sqlite3.connect(DB_PATH)
                    indexer_engine.init_db(conn)
                    for cf in changed_files:
                        print(f"[WATCHER] Auto-indexing: {os.path.basename(cf)}")
                        try:
                            # Wait brief moment in case file is still copying
                            time.sleep(0.5)
                            cnt = indexer_engine.process_file(cf, conn)
                            print(f"[WATCHER] Indexed {cnt} records from {os.path.basename(cf)}")
                        except Exception as e:
                            print(f"[WATCHER ERROR] Failed to index {cf}: {e}")
                        # Update cache
                        try:
                            st = os.stat(cf)
                            known_files[cf] = (st.st_mtime, st.st_size)
                        except Exception:
                            known_files[cf] = current_files.get(cf)
                    conn.close()

                # Clean up deleted files from known_files
                for p in list(known_files.keys()):
                    if p not in current_files:
                        del known_files[p]
        except Exception as e:
            print(f"[WATCHER ERROR] Loop error: {e}")
            
        time.sleep(3)

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Universal Document & Records Search</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-primary: #0b1120;
    --bg-secondary: #1e293b;
    --bg-card: #162032;
    --border: #334155;
    --accent: #38bdf8;
    --accent-hover: #0ea5e9;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --tag-bg: #0369a1;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-main);
    padding: 24px;
    min-height: 100vh;
  }
  .arabic { font-family: 'Cairo', sans-serif; }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 20px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 12px;
  }
  .header h1 {
    font-size: 1.45rem;
    font-weight: 700;
    color: var(--accent);
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .header-actions {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
  .badge {
    background: #0ea5e920;
    border: 1px solid #0ea5e940;
    color: var(--accent);
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 500;
  }
  .badge-watcher {
    background: #10b98120;
    border: 1px solid #10b98150;
    color: #10b981;
    cursor: pointer;
  }
  .badge-watcher.off {
    background: #ef444420;
    border-color: #ef444450;
    color: #f87171;
  }
  .btn-header {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
  }
  .btn-header:hover {
    background: #334155;
    border-color: var(--accent);
  }
  .btn-header.primary {
    background: #0284c7;
    border-color: #0284c7;
    color: #fff;
  }
  .btn-header.primary:hover {
    background: #0369a1;
  }
  
  /* Live Indexing Progress Bar Banner */
  .progress-banner {
    display: none;
    background: #1e293b;
    border: 1px solid var(--accent);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(56, 189, 248, 0.15);
    animation: fadeIn 0.3s ease;
  }
  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.86rem;
    margin-bottom: 8px;
  }
  .progress-bar-bg {
    width: 100%;
    height: 10px;
    background: #0f172a;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid var(--border);
  }
  .progress-bar-fill {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #38bdf8, #10b981);
    transition: width 0.3s ease;
  }

  .search-box {
    background: var(--bg-secondary);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid var(--border);
    margin-bottom: 24px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  }
  .input-group {
    display: flex;
    gap: 12px;
    position: relative;
  }
  input[type="text"] {
    flex: 1;
    background: #0f172a;
    border: 1px solid var(--border);
    color: #fff;
    padding: 12px 42px 12px 18px;
    border-radius: 8px;
    font-size: 1rem;
    outline: none;
    transition: border-color 0.2s;
  }
  input[type="text"]:focus {
    border-color: var(--accent);
  }
  .clear-btn {
    position: absolute;
    right: 120px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: #64748b;
    font-size: 1.1rem;
    cursor: pointer;
    display: none;
  }
  .clear-btn:hover { color: #f8fafc; }
  .btn-search {
    background: var(--accent);
    color: #0f172a;
    border: none;
    padding: 12px 28px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.95rem;
    cursor: pointer;
    transition: background 0.2s;
  }
  .btn-search:hover {
    background: var(--accent-hover);
  }
  .quick-chips {
    display: flex;
    gap: 8px;
    margin-top: 12px;
    align-items: center;
    font-size: 0.82rem;
    color: var(--text-muted);
    flex-wrap: wrap;
  }
  .chip {
    background: #33415550;
    border: 1px solid var(--border);
    padding: 4px 10px;
    border-radius: 6px;
    cursor: pointer;
    color: #cbd5e1;
    transition: all 0.15s;
  }
  .chip:hover {
    border-color: var(--accent);
    color: #fff;
  }
  
  .status-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    font-size: 0.85rem;
    color: var(--text-muted);
    flex-wrap: wrap;
    gap: 10px;
  }
  .view-toggle {
    display: flex;
    background: #0f172a;
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  .view-btn {
    background: none;
    border: none;
    color: #94a3b8;
    padding: 6px 14px;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
  }
  .view-btn.active {
    background: var(--accent);
    color: #0f172a;
  }

  /* Universal Cards Container */
  .cards-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .result-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }
  .result-card:hover {
    border-color: #0ea5e980;
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }
  .file-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.92rem;
    font-weight: 600;
    color: #f8fafc;
    word-break: break-all;
  }
  .file-type-pill {
    padding: 2px 8px;
    border-radius: 5px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .pill-xlsx, .pill-xls { background: #05966920; border: 1px solid #05966960; color: #34d399; }
  .pill-docx, .pill-odt { background: #2563eb20; border: 1px solid #2563eb60; color: #60a5fa; }
  .pill-pdf { background: #dc262620; border: 1px solid #dc262660; color: #f87171; }
  .pill-csv, .pill-txt { background: #d9770620; border: 1px solid #d9770660; color: #fbbf24; }
  
  .card-actions {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .card-pill-group {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 12px;
  }
  .info-pill {
    background: #0f172a;
    border: 1px solid var(--border);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #cbd5e1;
    cursor: pointer;
    user-select: none;
  }
  .info-pill:hover {
    border-color: var(--accent);
    color: #fff;
  }
  .info-pill .icon { opacity: 0.75; }
  .snippet-box {
    background: #090e1a;
    border-radius: 8px;
    padding: 10px 14px;
    font-family: monospace;
    font-size: 0.84rem;
    color: #cbd5e1;
    line-height: 1.5;
    word-break: break-word;
    border-left: 3px solid var(--accent);
  }
  .highlight {
    background: #fef08a40;
    color: #fef08a;
    padding: 1px 4px;
    border-radius: 3px;
    font-weight: 700;
  }

  /* Table Container */
  .table-container {
    background: var(--bg-secondary);
    border-radius: 12px;
    border: 1px solid var(--border);
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 0.88rem;
  }
  th {
    background: #0f172a;
    color: #94a3b8;
    font-weight: 600;
    padding: 14px 16px;
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
  }
  td {
    padding: 12px 16px;
    border-bottom: 1px solid #1e293b;
    color: #e2e8f0;
  }
  tr:hover td {
    background: #33415530;
  }
  .phone-tag {
    font-family: monospace;
    font-size: 0.95rem;
    color: var(--accent);
    font-weight: 600;
    cursor: pointer;
  }
  .btn-action-open {
    background: #0ea5e920;
    color: #38bdf8;
    border: 1px solid #0ea5e950;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
    transition: all 0.2s;
  }
  .btn-action-open:hover {
    background: #0ea5e9;
    color: #0f172a;
    border-color: #0ea5e9;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
  }
  .btn-action-folder {
    background: #33415550;
    color: #cbd5e1;
    border: 1px solid var(--border);
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.78rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: all 0.2s;
  }
  .btn-action-folder:hover {
    background: #475569;
    color: #fff;
    border-color: var(--accent);
  }
  .pagination-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    background: var(--bg-secondary);
    border-radius: 10px;
    margin-top: 14px;
    border: 1px solid var(--border);
    font-size: 0.88rem;
    color: var(--text-muted);
  }
  .pagination-btns {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .page-btn {
    background: #0f172a;
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.82rem;
    transition: all 0.2s;
  }
  .page-btn:hover:not(:disabled) {
    background: var(--accent);
    color: #0f172a;
    border-color: var(--accent);
  }
  .page-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #1e293b;
    border: 1px solid var(--accent);
    color: #f8fafc;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 0.88rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    z-index: 9999;
    opacity: 0;
    transform: translateY(10px);
    transition: all 0.3s ease;
  }
  .toast.show {
    opacity: 1;
    transform: translateY(0);
  }
  .chip {
    background: #33415550;
    border: 1px solid var(--border);
    padding: 5px 12px;
    border-radius: 6px;
    cursor: pointer;
    color: #cbd5e1;
    transition: all 0.15s;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .chip:hover {
    border-color: var(--accent);
    color: #fff;
  }
  .chip-del {
    color: #64748b;
    border-radius: 50%;
    width: 16px;
    height: 16px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    line-height: 1;
    margin-left: 2px;
    transition: all 0.15s;
  }
  .chip-del:hover {
    background: #ef444430;
    color: #ef4444;
  }
  .btn-add-chip {
    background: #0284c720;
    border: 1px dashed var(--accent);
    color: var(--accent);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    cursor: pointer;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: all 0.2s;
  }
  .btn-add-chip:hover {
    background: #0284c7;
    color: #fff;
    border-style: solid;
  }

  /* Modal for Setting Folder */
  .modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.7);
    z-index: 10000;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(4px);
  }
  .modal-overlay.active { display: flex; }
  .modal-content {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    padding: 24px;
    border-radius: 12px;
    width: 90%;
    max-width: 540px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
  }
  .modal-content h3 {
    margin-bottom: 12px;
    color: var(--accent);
    font-size: 1.2rem;
  }
  .modal-content p {
    font-size: 0.88rem;
    color: var(--text-muted);
    margin-bottom: 16px;
    line-height: 1.4;
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
  }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-5px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
</head>
<body>
  <!-- Index Folder Modal -->
  <div id="folderModal" class="modal-overlay">
    <div class="modal-content">
      <h3>📁 Set Folder to Index</h3>
      <p>Enter the full directory path to scan and index all documents (<code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>, <code>.docx</code>, <code>.odt</code>, <code>.txt</code>, <code>.pdf</code>). Subfolders will be indexed and continuously watched.</p>
      <input type="text" id="folderPathInput" style="width:100%; margin-bottom: 8px;" placeholder="/home/essam/Work/George/FINAL">
      <div class="modal-actions">
        <button class="btn-header" onclick="closeFolderModal()">Cancel</button>
        <button class="btn-header primary" onclick="submitFolderIndex()">Start Indexing</button>
      </div>
    </div>
  </div>

  <!-- Add Quick Filter Modal -->
  <div id="filterModal" class="modal-overlay">
    <div class="modal-content">
      <h3>⚡ Add Quick Filter</h3>
      <p>Create a custom shortcut saved in the database for instant one-click searches.</p>
      <div style="margin-bottom: 12px;">
        <label style="display:block; font-size:0.8rem; color:var(--text-muted); margin-bottom:4px;">Filter Label / Name:</label>
        <input type="text" id="filterNameInput" style="width:100%;" placeholder="e.g. VIP Target, 015 Prefix, Cairo Cases">
      </div>
      <div style="margin-bottom: 16px;">
        <label style="display:block; font-size:0.8rem; color:var(--text-muted); margin-bottom:4px;">Search Query / Keyword / Phone:</label>
        <input type="text" id="filterQueryInput" style="width:100%;" placeholder="e.g. 01012345678 or سوزان or 602018...">
      </div>
      <div class="modal-actions">
        <button class="btn-header" onclick="closeFilterModal()">Cancel</button>
        <button class="btn-header primary" onclick="submitFilter()">Save Filter</button>
      </div>
    </div>
  </div>

  <!-- Hidden File Input for Importing DB -->
  <input type="file" id="dbFileInput" accept=".db,.sqlite,.sqlite3" style="display:none;" onchange="handleImportFile(event)">

  <div class="header">
    <h1>
      🔍 Universal Document & Records Search
    </h1>
    <div class="header-actions">
      <span class="badge" id="statsBadge">Loading stats...</span>
      <span class="badge badge-watcher" id="watcherBadge" onclick="toggleWatcher()" title="Click to toggle live watcher">👁️ Watcher: ON</span>
      <button class="btn-header" onclick="openFolderModal()">📁 Set Folder</button>
      <button class="btn-header" onclick="exportIndex()">📤 Export Index</button>
      <button class="btn-header" onclick="document.getElementById('dbFileInput').click()">📥 Import Index</button>
      <button class="btn-header" onclick="exportCSV()">📑 Export CSV</button>
    </div>
  </div>

  <!-- Live Progress Banner -->
  <div id="progressBanner" class="progress-banner">
    <div class="progress-info">
      <span id="progressStatus" style="font-weight: 600; color: #f8fafc;">Indexing documents...</span>
      <span id="progressPercent" style="font-weight: 700; color: var(--accent);">0%</span>
    </div>
    <div class="progress-bar-bg">
      <div id="progressBarFill" class="progress-bar-fill"></div>
    </div>
    <div style="display:flex; justify-content:space-between; margin-top:6px; font-size:0.78rem; color:var(--text-muted);">
      <span id="progressCurrentFile">Preparing documents...</span>
      <span id="progressRecords">0 entries indexed</span>
    </div>
  </div>

  <div class="search-box">
    <div class="input-group">
      <input type="text" id="queryInput" placeholder="Search anything: phone, name (عربي/EN), National ID, text snippet, or document word..." oninput="handleInput(event)" onkeydown="if(event.key==='Enter') doSearch(0)" autofocus>
      <button id="clearSearchBtn" class="clear-btn" onclick="clearSearch()" title="Clear">✕</button>
      <button class="btn-search" onclick="doSearch(0)">Search</button>
    </div>
    <div class="quick-chips" id="quickChipsContainer">
      <span style="font-size:0.8rem; color:var(--text-muted);">Quick filters:</span>
      <div id="quickChipsList" style="display:inline-flex; flex-wrap:wrap; gap:6px; align-items:center;">
        <!-- Dynamically loaded from database -->
      </div>
      <button class="btn-add-chip" onclick="openFilterModal()" title="Add custom quick filter">+ Add Filter</button>
    </div>
  </div>

  <div class="status-bar">
    <div>
      <span id="resultsCount">Ready</span>
      <span style="margin-left:8px; opacity:0.6;" id="timing">0ms</span>
    </div>
    <div class="view-toggle">
      <button id="btnViewCard" class="view-btn active" onclick="switchView('card')">📇 Universal Cards</button>
      <button id="btnViewTable" class="view-btn" onclick="switchView('table')">📊 Tabular / CDR</button>
    </div>
  </div>

  <!-- Main Results Display Containers -->
  <div id="cardsContainer" class="cards-container">
    <div style="text-align:center; padding: 40px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border);">
      Enter any keyword or phone number above to search across all documents and sheets.
    </div>
  </div>

  <div id="tableContainer" class="table-container" style="display:none;">
    <table id="resultsTable">
      <thead>
        <tr id="tableHead">
          <th>File</th>
          <th>Time</th>
          <th>Dir</th>
          <th>Target</th>
          <th>Other Party</th>
          <th>Name</th>
          <th>Duration / Extra</th>
          <th>Location / Cell</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody id="tableBody">
        <tr>
          <td colspan="9" style="text-align:center; padding: 40px; color:#64748b;">Enter any query above to search.</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div id="paginationBar" class="pagination-bar" style="display:none;">
    <span id="pageInfo">Showing 0-0 of 0</span>
    <div class="pagination-btns">
      <button id="prevBtn" class="page-btn" onclick="changePage(-1)">← Previous</button>
      <span id="pageNumberBadge" style="font-weight:600; color:var(--accent);">Page 1</span>
      <button id="nextBtn" class="page-btn" onclick="changePage(1)">Next →</button>
    </div>
  </div>

  <div id="toast" class="toast">Opening file...</div>

<script>
let currentPage = 0;
const pageSize = 50;
let currentQuery = '';
let totalResults = 0;
let lastResults = [];
let progressPollInterval = null;
let currentViewMode = 'card'; // 'card' or 'table'
let debounceTimer = null;

function showToast(msg, duration = 3000) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

function copyToClipboard(text, label = 'Copied') {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    showToast(`📋 ${label}: ${text}`);
  }).catch(() => {
    showToast(`📋 ${text}`);
  });
}

function switchView(mode) {
  currentViewMode = mode;
  document.getElementById('btnViewCard').classList.toggle('active', mode === 'card');
  document.getElementById('btnViewTable').classList.toggle('active', mode === 'table');
  document.getElementById('cardsContainer').style.display = (mode === 'card') ? 'flex' : 'none';
  document.getElementById('tableContainer').style.display = (mode === 'table') ? 'block' : 'none';
  if (lastResults && lastResults.length > 0) {
    renderViewData({ rows: lastResults, total: totalResults, type: lastResults[0]?.phone ? 'prefix' : 'cdr' });
  }
}

function handleInput(e) {
  const val = e.target.value.trim();
  document.getElementById('clearSearchBtn').style.display = val ? 'block' : 'none';
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    if (val.length >= 2 || val.length === 0) {
      doSearch(0);
    }
  }, 350);
}

function clearSearch() {
  document.getElementById('queryInput').value = '';
  document.getElementById('clearSearchBtn').style.display = 'none';
  document.getElementById('queryInput').focus();
  doSearch(0);
}

async function refreshStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('statsBadge').innerText = `Loaded ${data.files.toLocaleString()} Documents | ${data.records.toLocaleString()} Entries`;
  } catch (e) {
    console.error(e);
  }
}

async function refreshWatcherStatus() {
  try {
    const res = await fetch('/api/watch/status');
    const data = await res.json();
    const badge = document.getElementById('watcherBadge');
    if (data.active && data.folder) {
      badge.className = "badge badge-watcher";
      badge.innerText = `👁️ Watcher: ON (${data.folder.split('/').pop()})`;
      badge.title = `Watching: ${data.folder}\\nClick to pause/toggle`;
    } else {
      badge.className = "badge badge-watcher off";
      badge.innerText = "👁️ Watcher: OFF";
      badge.title = "Click to activate live watcher";
    }
    if (data.folder && !document.getElementById('folderPathInput').value) {
      document.getElementById('folderPathInput').value = data.folder;
    }
  } catch (e) {
    console.error(e);
  }
}

async function toggleWatcher() {
  try {
    const res = await fetch('/api/watch/toggle', { method: 'POST' });
    const data = await res.json();
    showToast(data.message || 'Watcher status updated');
    refreshWatcherStatus();
  } catch (e) {
    showToast('Failed to toggle watcher');
  }
}

function openFolderModal() {
  document.getElementById('folderModal').classList.add('active');
  document.getElementById('folderPathInput').focus();
}

function closeFolderModal() {
  document.getElementById('folderModal').classList.remove('active');
}

async function submitFolderIndex() {
  const folder = document.getElementById('folderPathInput').value.trim();
  if (!folder) {
    alert("Please enter a valid folder path!");
    return;
  }
  closeFolderModal();
  showToast("🚀 Starting indexing...");
  try {
    const res = await fetch(`/api/index/start?folder=${encodeURIComponent(folder)}`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast("Indexing in progress...");
      startProgressPolling();
    } else {
      showToast(`❌ ${data.error || 'Failed to start indexing'}`);
    }
  } catch (err) {
    showToast("❌ Network error starting index");
  }
}

function startProgressPolling() {
  const banner = document.getElementById('progressBanner');
  banner.style.display = 'block';
  if (progressPollInterval) clearInterval(progressPollInterval);

  progressPollInterval = setInterval(async () => {
    try {
      const res = await fetch('/api/index/status');
      const st = await res.json();
      
      document.getElementById('progressStatus').innerText = st.status_message || (st.running ? 'Indexing...' : 'Completed');
      document.getElementById('progressPercent').innerText = `${st.percent}%`;
      document.getElementById('progressBarFill').style.width = `${st.percent}%`;
      document.getElementById('progressCurrentFile').innerText = st.current_file ? `Processing: ${st.current_file}` : '';
      document.getElementById('progressRecords').innerText = `${(st.records_indexed || 0).toLocaleString()} entries indexed`;

      if (!st.running) {
        clearInterval(progressPollInterval);
        progressPollInterval = null;
        refreshStats();
        refreshWatcherStatus();
        setTimeout(() => {
          banner.style.display = 'none';
        }, 3500);
        showToast("✅ Indexing completed successfully!");
      }
    } catch (e) {
      console.error(e);
    }
  }, 800);
}

function exportIndex() {
  showToast("📦 Preparing database export...");
  window.location.href = '/api/index/export';
}

async function handleImportFile(event) {
  const file = event.target.files[0];
  if (!file) return;

  if (!confirm(`Are you sure you want to import '${file.name}'? This will replace your current database index.`)) {
    event.target.value = '';
    return;
  }

  showToast("📥 Uploading and importing index database...");
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/index/import', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.ok) {
      showToast("✅ Index database imported successfully!");
      refreshStats();
      refreshWatcherStatus();
      if (currentQuery) doSearch(0);
    } else {
      showToast(`❌ Import error: ${data.error || 'Failed to import'}`);
    }
  } catch (err) {
    showToast("❌ Network error while importing index");
  } finally {
    event.target.value = '';
  }
}

async function openFile(filePath, sheetName, rowIdx) {
  if (!filePath) {
    showToast("⚠️ File path not available");
    return;
  }
  showToast(`📂 Opening ${sheetName ? sheetName + ' ' : ''}at Row/Page ${rowIdx || 1}...`);
  try {
    const params = new URLSearchParams({
      file: filePath,
      sheet: sheetName || '',
      row: rowIdx || ''
    });
    const res = await fetch(`/api/open?${params.toString()}`);
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message || 'File opened successfully'}`);
    } else {
      showToast(`❌ ${data.error || 'Failed to open file'}`);
    }
  } catch (err) {
    showToast(`❌ Network error while opening file`);
  }
}

async function revealFolder(filePath) {
  if (!filePath) return;
  showToast("📁 Opening folder in file manager...");
  try {
    const res = await fetch(`/api/reveal?file=${encodeURIComponent(filePath)}`);
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message || 'Folder opened'}`);
    } else {
      showToast(`❌ ${data.error || 'Failed to open folder'}`);
    }
  } catch (err) {
    showToast(`❌ Network error opening folder`);
  }
}

function quick(q) {
  document.getElementById('queryInput').value = q;
  document.getElementById('clearSearchBtn').style.display = 'block';
  doSearch(0);
}

function highlightMatch(text, term) {
  if (!text) return '';
  if (!term) return escapeHtml(text);
  const cleanTerm = term.replace(/[\.\*\+\?\^\$\{\}\(\)\|\[\]\\]/g, '\\\\$&');
  const regex = new RegExp(`(${cleanTerm})`, 'gi');
  return escapeHtml(text).replace(regex, '<span class="highlight">$1</span>');
}

async function doSearch(page = 0) {
  const q = document.getElementById('queryInput').value.trim();
  if (!q) {
    lastResults = [];
    totalResults = 0;
    renderViewData({ rows: [], total: 0 });
    document.getElementById('resultsCount').innerText = "Ready";
    document.getElementById('timing').innerText = "0ms";
    return;
  }

  currentPage = page;
  currentQuery = q;
  const offset = currentPage * pageSize;

  const t0 = performance.now();
  document.getElementById('resultsCount').innerText = "Searching...";
  
  try {
    const params = new URLSearchParams({
      q: currentQuery,
      limit: pageSize,
      offset: offset
    });
    const res = await fetch(`/api/search?${params.toString()}`);
    const data = await res.json();
    const t1 = performance.now();
    document.getElementById('timing').innerText = `${Math.round(t1 - t0)}ms`;

    renderViewData(data);
  } catch (err) {
    document.getElementById('resultsCount').innerText = "Error fetching results";
    console.error(err);
  }
}

function changePage(delta) {
  const newPage = currentPage + delta;
  if (newPage < 0) return;
  if (newPage * pageSize >= totalResults) return;
  doSearch(newPage);
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getFileExtBadge(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  const cls = `pill-${ext}`;
  return `<span class="file-type-pill ${cls}">${ext || 'DOC'}</span>`;
}

function renderViewData(data) {
  lastResults = data.rows || [];
  totalResults = data.total || 0;
  const paginationBar = document.getElementById('paginationBar');

  if (totalResults > pageSize) {
    paginationBar.style.display = 'flex';
    const start = (currentPage * pageSize) + 1;
    const end = Math.min((currentPage + 1) * pageSize, totalResults);
    document.getElementById('pageInfo').innerText = `Showing ${start}-${end} of ${totalResults.toLocaleString()} matches`;
    document.getElementById('pageNumberBadge').innerText = `Page ${currentPage + 1} of ${Math.ceil(totalResults / pageSize)}`;
    document.getElementById('prevBtn').disabled = (currentPage === 0);
    document.getElementById('nextBtn').disabled = ((currentPage + 1) * pageSize >= totalResults);
  } else if (totalResults > 0) {
    paginationBar.style.display = 'flex';
    document.getElementById('pageInfo').innerText = `Showing ${totalResults} matches`;
    document.getElementById('pageNumberBadge').innerText = `Page 1 of 1`;
    document.getElementById('prevBtn').disabled = true;
    document.getElementById('nextBtn').disabled = true;
  } else {
    paginationBar.style.display = 'none';
  }

  if (data.type === 'prefix') {
    document.getElementById('resultsCount').innerText = `Found ${totalResults.toLocaleString()} phone numbers`;
    renderPrefixTable(data.rows);
  } else {
    document.getElementById('resultsCount').innerText = `Found ${totalResults.toLocaleString()} matches`;
    renderCards(data.rows);
    renderTableRows(data.rows);
  }
}

function renderCards(rows) {
  const container = document.getElementById('cardsContainer');
  container.innerHTML = '';

  if (!rows || rows.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 40px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border);">
        No matching records found for "${escapeHtml(currentQuery)}".
      </div>
    `;
    return;
  }

  rows.forEach(r => {
    const card = document.createElement('div');
    card.className = 'result-card';
    const escapedPath = (r.path || '').replace(/'/g, "\\\\'");
    const escapedSheet = (r.sheet || '').replace(/'/g, "\\\\'");

    let pillsHtml = '';
    if (r.target && r.target !== '—') {
      pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.target}', 'Target Phone')"><span class="icon">📞 Target:</span> <b>${highlightMatch(r.target, currentQuery)}</b></span>`;
    }
    if (r.other && r.other !== '—') {
      pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.other}', 'Party Phone')"><span class="icon">📱 Party:</span> <b>${highlightMatch(r.other, currentQuery)}</b></span>`;
    }
    if (r.name && r.name !== '—') {
      pillsHtml += `<span class="info-pill arabic" onclick="copyToClipboard('${r.name}', 'Name')"><span class="icon">👤</span> <b>${highlightMatch(r.name, currentQuery)}</b></span>`;
    }
    if (r.time && r.time !== '—') {
      pillsHtml += `<span class="info-pill"><span class="icon">📅</span> ${escapeHtml(r.time)}</span>`;
    }
    if (r.dir && r.dir !== '—') {
      pillsHtml += `<span class="info-pill"><span class="icon">🔄</span> ${escapeHtml(r.dir)}</span>`;
    }
    if (r.address && r.address !== '—') {
      pillsHtml += `<span class="info-pill arabic"><span class="icon">📍</span> ${highlightMatch(r.address, currentQuery)}</span>`;
    }

    card.innerHTML = `
      <div class="card-header">
        <div class="file-meta">
          ${getFileExtBadge(r.file)}
          <span title="${escapeHtml(r.path || '')}">${escapeHtml(r.file)}</span>
          <span style="color:#64748b; font-size:0.8rem; font-weight:normal;">• ${escapeHtml(r.sheet)} (Row ${r.row})</span>
        </div>
        <div class="card-actions">
          <button class="btn-action-open" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})">
            🚀 Open Row ${r.row}
          </button>
          <button class="btn-action-folder" onclick="revealFolder('${escapedPath}')" title="Reveal containing folder">
            📂 Folder
          </button>
        </div>
      </div>
      ${pillsHtml ? `<div class="card-pill-group">${pillsHtml}</div>` : ''}
      <div class="snippet-box">
        ${highlightMatch(r.snippet, currentQuery)}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderTableRows(rows) {
  const tbody = document.getElementById('tableBody');
  const thead = document.getElementById('tableHead');
  tbody.innerHTML = '';
  thead.innerHTML = `
    <th>File</th>
    <th>Time</th>
    <th>Dir</th>
    <th>Target</th>
    <th>Other Party</th>
    <th>Name</th>
    <th>Duration / Extra</th>
    <th>Location / Cell</th>
    <th>Action</th>
  `;

  if (!rows || rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:30px;">No matching records found.</td></tr>';
    return;
  }

  rows.forEach(r => {
    const tr = document.createElement('tr');
    const escapedPath = escapeHtml(r.path || '').replace(/'/g, "\\\\'");
    const escapedSheet = escapeHtml(r.sheet || '').replace(/'/g, "\\\\'");

    tr.innerHTML = `
      <td style="font-size:0.8rem; max-width:180px; word-break:break-all;">
        <b>${escapeHtml(r.file)}</b>
        <div style="color:#64748b; font-size:0.75rem;">${escapeHtml(r.sheet)} (Row ${r.row})</div>
      </td>
      <td style="font-size:0.82rem; white-space:nowrap; color:#cbd5e1;">${escapeHtml(r.time)}</td>
      <td><span class="badge" style="font-size:0.75rem;">${escapeHtml(r.dir)}</span></td>
      <td><span class="phone-tag" onclick="copyToClipboard('${r.target}', 'Target')">${highlightMatch(r.target, currentQuery)}</span></td>
      <td><span class="phone-tag" style="color:#38bdf8;" onclick="quick('${r.other}')">${highlightMatch(r.other, currentQuery)}</span></td>
      <td class="arabic" style="font-weight:600; color:#f8fafc;">${highlightMatch(r.name, currentQuery)}</td>
      <td style="font-size:0.82rem; color:#94a3b8;">${escapeHtml(r.extra)}</td>
      <td class="arabic" style="font-size:0.82rem; color:#94a3b8; max-width:220px;">${highlightMatch(r.address, currentQuery)}</td>
      <td>
        <div style="display:flex; gap:4px; align-items:center;">
          <button class="btn-action-open" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})">
            🚀 Open
          </button>
          <button class="btn-action-folder" onclick="revealFolder('${escapedPath}')" title="Open Folder">
            📂
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderPrefixTable(rows) {
  const tbody = document.getElementById('tableBody');
  const thead = document.getElementById('tableHead');
  switchView('table');
  tbody.innerHTML = '';
  thead.innerHTML = `
    <th>#</th>
    <th>Phone Number</th>
    <th>Associated Name</th>
    <th>Total Records / Calls</th>
    <th>Sample Files</th>
  `;

  if (!rows || rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px;">No phone numbers found.</td></tr>';
    return;
  }

  rows.forEach((r, idx) => {
    const tr = document.createElement('tr');
    const rank = (currentPage * pageSize) + idx + 1;
    tr.innerHTML = `
      <td style="color:#64748b;">${rank}</td>
      <td><span class="phone-tag" onclick="quick('${r.phone}')">${r.phone}</span></td>
      <td class="arabic" style="font-weight:600;">${escapeHtml(r.name)}</td>
      <td><span class="badge">${r.count} calls</span></td>
      <td style="color:#94a3b8; font-size:0.8rem;">${escapeHtml(r.files)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function exportCSV() {
  if (!lastResults || lastResults.length === 0) {
    alert("No data to export!");
    return;
  }
  const keys = Object.keys(lastResults[0]);
  let csv = keys.join(",") + "\\n";
  lastResults.forEach(row => {
    csv += keys.map(k => `"${(row[k] || '').toString().replace(/"/g, '""')}"`).join(",") + "\\n";
  });
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `export_${Date.now()}.csv`;
  a.click();
}

/* Custom Quick Filters Management */
function openFilterModal() {
  const currentQ = document.getElementById('queryInput').value.trim();
  if (currentQ) {
    document.getElementById('filterQueryInput').value = currentQ;
  }
  document.getElementById('filterModal').classList.add('active');
  setTimeout(() => document.getElementById('filterNameInput').focus(), 100);
}

function closeFilterModal() {
  document.getElementById('filterModal').classList.remove('active');
  document.getElementById('filterNameInput').value = '';
  document.getElementById('filterQueryInput').value = '';
}

async function loadQuickFilters() {
  try {
    const res = await fetch('/api/filters');
    const data = await res.json();
    const container = document.getElementById('quickChipsList');
    if (!container) return;
    container.innerHTML = '';
    if (data.ok && Array.isArray(data.filters)) {
      if (data.filters.length === 0) {
        container.innerHTML = '<span style="font-size:0.75rem; color:#64748b; font-style:italic;">None yet. Click + Add Filter to create one!</span>';
        return;
      }
      data.filters.forEach(f => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.title = `Search: ${f.query}`;
        chip.innerHTML = `
          <span onclick="quick('${escapeHtml(f.query)}')">${escapeHtml(f.name || f.query)}</span>
          <span class="chip-del" title="Delete filter" onclick="deleteFilter(${f.id}, event)">✕</span>
        `;
        container.appendChild(chip);
      });
    }
  } catch (err) {
    console.error("Error loading quick filters:", err);
  }
}

async function submitFilter() {
  const name = document.getElementById('filterNameInput').value.trim();
  const query = document.getElementById('filterQueryInput').value.trim();
  if (!name || !query) {
    alert("Please provide both a filter name and a query.");
    return;
  }
  try {
    const res = await fetch('/api/filters/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, query })
    });
    const data = await res.json();
    if (data.ok) {
      showToast("✅ Filter added successfully!");
      closeFilterModal();
      loadQuickFilters();
    } else {
      showToast("❌ " + (data.error || "Failed to add filter"));
    }
  } catch (err) {
    showToast("❌ Network error saving filter");
  }
}

async function deleteFilter(id, evt) {
  if (evt) evt.stopPropagation();
  if (!confirm("Are you sure you want to delete this quick filter?")) return;
  try {
    const res = await fetch('/api/filters/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    const data = await res.json();
    if (data.ok) {
      showToast("🗑️ Filter removed");
      loadQuickFilters();
    } else {
      showToast("❌ " + (data.error || "Failed to remove filter"));
    }
  } catch (err) {
    showToast("❌ Network error deleting filter");
  }
}

window.onload = () => {
  refreshStats();
  refreshWatcherStatus();
  loadQuickFilters();
};
</script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
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
        elif parsed.path == "/api/index/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(INDEX_STATE).encode("utf-8"))
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
            limit = int(limit_val) if limit_val.isdigit() else 50
            offset = int(offset_val) if offset_val.isdigit() else 0
            data = query_db(q, limit=limit, offset=offset)
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
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/filters/add":
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
            folder = qs.get("folder", [""])[0]
            ok, msg = start_indexing_thread(folder)
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok, "message" if ok else "error": msg}).encode("utf-8"))
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
