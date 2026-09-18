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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sheets_index.db")
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
        return {"files": 0, "records": 0, "watcher": WATCHER_CONFIG.get("active", False)}
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM files;")
        total_files = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM cdr_records;")
        total_records = cur.fetchone()[0]
        conn.close()
        return {"files": total_files, "records": total_records, "watcher": WATCHER_CONFIG.get("active", False)}
    except Exception:
        return {"files": 0, "records": 0, "watcher": WATCHER_CONFIG.get("active", False)}

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

# Bookmark Helpers
def get_bookmarks():
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT NOT NULL, sheet_name TEXT NOT NULL, row_idx INTEGER NOT NULL, tag TEXT DEFAULT 'Lead', notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(file_path, sheet_name, row_idx));")
        cur.execute("""
        SELECT b.id, b.file_path, b.sheet_name, b.row_idx, b.tag, b.notes, b.created_at,
               c.target_msisdn, c.other_msisdn, c.other_name, c.event_time, c.direction, c.raw_row
        FROM bookmarks b
        LEFT JOIN files f ON b.file_path = f.file_path
        LEFT JOIN cdr_records c ON c.file_id = f.file_id AND c.sheet_name = b.sheet_name AND c.row_idx = b.row_idx
        ORDER BY b.id DESC;
        """)
        results = []
        for r in cur.fetchall():
            results.append({
                "id": r[0],
                "path": r[1],
                "file": os.path.basename(r[1]),
                "sheet": r[2],
                "row": r[3],
                "tag": r[4],
                "notes": r[5] or "",
                "created_at": r[6],
                "target": r[7] or "—",
                "other": r[8] or "—",
                "name": r[9] or "—",
                "time": r[10] or "—",
                "dir": r[11] or "—",
                "snippet": (r[12] or "")[:400]
            })
        conn.close()
        return results
    except Exception as e:
        print(f"[BOOKMARK ERROR] {e}")
        return []

def add_bookmark(file_path, sheet_name, row_idx, tag="Lead", notes=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT NOT NULL, sheet_name TEXT NOT NULL, row_idx INTEGER NOT NULL, tag TEXT DEFAULT 'Lead', notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(file_path, sheet_name, row_idx));")
        cur.execute("""
        INSERT INTO bookmarks (file_path, sheet_name, row_idx, tag, notes)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(file_path, sheet_name, row_idx) DO UPDATE SET tag = excluded.tag, notes = excluded.notes;
        """, (file_path, sheet_name, int(row_idx), tag, notes))
        conn.commit()
        conn.close()
        return True, "Bookmark saved"
    except Exception as e:
        return False, str(e)

def remove_bookmark(file_path, sheet_name, row_idx):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM bookmarks WHERE file_path = ? AND sheet_name = ? AND row_idx = ?;", (file_path, sheet_name, int(row_idx)))
        conn.commit()
        conn.close()
        return True, "Bookmark removed"
    except Exception as e:
        return False, str(e)

def get_context_window(file_path, sheet_name, row_idx, window=3):
    """Retrieve up to +/- 3 lines around row_idx for document preview."""
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        r_idx = int(row_idx)
        min_r = max(1, r_idx - window)
        max_r = r_idx + window
        cur.execute("""
        SELECT row_idx, content FROM universal_search
        WHERE file_path = ? AND sheet_name = ? AND row_idx BETWEEN ? AND ?
        ORDER BY row_idx ASC;
        """, (file_path, sheet_name, min_r, max_r))
        rows = [{"row": r[0], "content": r[1], "target": (r[0] == r_idx)} for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[CONTEXT ERROR] {e}")
        return []

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
    """Create a rotating daily backup snapshot of sheets_index.db"""
    if not os.path.exists(DB_PATH):
        return False, "Database does not exist yet"
    try:
        date_str = time.strftime("%Y%m%d")
        snap_path = f"{DB_PATH}.snap_{date_str}"
        shutil.copy2(DB_PATH, snap_path)
        return True, f"Backup created: {os.path.basename(snap_path)}"
    except Exception as e:
        return False, str(e)


def levenshtein_dist(s1, s2):
    """Fast, pure standard-library Levenshtein distance for fuzzy typo matching."""
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)
    # Optimization: limit to 40 chars max for speed
    s1, s2 = s1[:40], s2[:40]
    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)
    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0 = v1[:]
    return v0[len(s2)]

def parse_google_query(raw_query):
    """
    Parses Google-style search operators:
    - Exact phrases: "word1 word2"
    - Exclude words: -term
    - OR logic: term1 OR term2
    - AND logic: term1 AND term2
    - File extension filter: filetype:pdf or filetype:xlsx
    Returns dict: fts_match, filetype, exact_phrases, clean_tokens.
    """
    clean = (raw_query or "").strip()
    if not clean:
        return {"fts_match": "", "filetype": None, "exact_phrases": [], "clean_tokens": []}

    # 1. filetype:ext
    filetype = None
    ft_m = re.search(r"\bfiletype:([a-zA-Z0-9]+)\b", clean, re.IGNORECASE)
    if ft_m:
        filetype = ft_m.group(1).lower().strip()
        clean = re.sub(r"\bfiletype:[a-zA-Z0-9]+\b", " ", clean, flags=re.IGNORECASE).strip()

    # 2. Extract exact phrases in quotes "..."
    exact_phrases = [p.strip() for p in re.findall(r"\"([^\"]+)\"", clean) if p.strip()]
    clean_no_quotes = re.sub(r"\"[^\"]*\"", " ", clean).strip()

    # 3. Parse negative terms (-term)
    tokens = clean_no_quotes.split()
    pos_tokens = []
    neg_tokens = []
    for t in tokens:
        if t.startswith("-") and len(t) > 1:
            term = t[1:].strip("(),:;\"'")
            if term:
                neg_tokens.append(term)
        else:
            pos_tokens.append(t)

    # 4. Handle OR / AND logic in remaining positive tokens
    pos_str = " ".join(pos_tokens)
    fts_parts = []

    # Add exact phrases
    for ph in exact_phrases:
        clean_ph = ph.replace('"', '')
        fts_parts.append(f'"{clean_ph}"')

    or_split = re.split(r"\s+OR\s+", pos_str, flags=re.IGNORECASE)
    if len(or_split) > 1:
        sub_fts = []
        for segment in or_split:
            words = [w.strip("(),:;\"'") for w in segment.split() if w.strip("(),:;\"'") and w.upper() != "AND"]
            if words:
                sub_fts.append(" AND ".join([f'""{w}""' for w in words]))
        if sub_fts:
            fts_parts.append("(" + " OR ".join(sub_fts) + ")")
    else:
        words = [w.strip("(),:;\"'") for w in pos_str.split() if w.strip("(),:;\"'") and w.upper() != "AND"]
        for w in words:
            fts_parts.append(f'""{w}""')

    fts_match = " AND ".join(fts_parts) if fts_parts else ""

    for nt in neg_tokens:
        clean_nt = nt.replace('"', '')
        if fts_match:
            fts_match += f' NOT ""{clean_nt}""'

    clean_tokens = [w for w in pos_str.split() if w.upper() not in ("OR", "AND")] + exact_phrases

    return {
        "fts_match": fts_match,
        "filetype": filetype,
        "exact_phrases": exact_phrases,
        "clean_tokens": [t.strip("(),:;\"'") for t in clean_tokens if t.strip("(),:;\"'")]
    }

def query_db(query, limit=50, offset=0, scope_file=None, scope_folder=None, mode="general"):
    if not os.path.exists(DB_PATH):
        return {"rows": [], "total": 0, "limit": limit, "offset": offset, "mode": mode}
        
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("levenshtein", 2, levenshtein_dist)
    cur = conn.cursor()
    query = (query or "").strip()
    if not query:
        conn.close()
        return {"rows": [], "total": 0, "limit": limit, "offset": offset, "mode": mode}

    norm_p = normalize_phone(query)
    norm_a = normalize_arabic(query)
    pattern = f"%{query}%"

    # Extract clean digits for partial number matching
    digits_only = re.sub(r'\D', '', query)

    scope_clause_cdr = ""
    scope_params_cdr = []
    scope_clause_fts = ""
    scope_params_fts = []

    if scope_file:
        scope_clause_cdr = " AND f.file_path = ? "
        scope_params_cdr.append(scope_file)
        scope_clause_fts = " AND u.file_path = ? "
        scope_params_fts.append(scope_file)
    elif scope_folder:
        clean_fld = os.path.abspath(scope_folder)
        scope_clause_cdr = " AND (f.folder = ? OR f.file_path LIKE ?) "
        scope_params_cdr.extend([clean_fld, f"{clean_fld}%"])
        scope_clause_fts = " AND (f.folder = ? OR u.file_path LIKE ?) "
        scope_params_fts.extend([clean_fld, f"{clean_fld}%"])

    # Prefix search for Telecom mode
    if mode == "telecom" and (query.lower().startswith("prefix:") or (query.isdigit() and len(query) in (3, 4) and query.startswith("01"))):
        prefix_val = query.replace("prefix:", "").strip()
        norm_pfx = normalize_phone(prefix_val) if len(prefix_val) > 2 else prefix_val
        pfx_pat = f"{norm_pfx}%"
        
        count_sql = f"""
        SELECT COUNT(DISTINCT c.other_norm)
        FROM cdr_records c
        JOIN files f ON c.file_id = f.file_id
        WHERE (c.other_norm LIKE ? OR c.target_norm LIKE ?) {scope_clause_cdr};
        """
        cur.execute(count_sql, [pfx_pat, pfx_pat] + scope_params_cdr)
        total_cnt = cur.fetchone()[0] or 0

        sql = f"""
        SELECT c.other_norm, c.other_name, COUNT(*) as cnt, GROUP_CONCAT(DISTINCT f.filename) as src_files
        FROM cdr_records c
        JOIN files f ON c.file_id = f.file_id
        WHERE (c.other_norm LIKE ? OR c.target_norm LIKE ?) {scope_clause_cdr}
        GROUP BY c.other_norm
        ORDER BY cnt DESC
        LIMIT ? OFFSET ?;
        """
        cur.execute(sql, [pfx_pat, pfx_pat] + scope_params_cdr + [limit, offset])
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
        return {"type": "prefix", "rows": results, "total": total_cnt, "limit": limit, "offset": offset, "mode": mode}

    # MODE A: TELECOM CDR SEARCH (With partial number, substring & fuzzy matching)
    if mode == "telecom":
        # Check if digits partial query (e.g. 989378 or 01017)
        cdr_partial_sql = ""
        cdr_partial_params = []
        if len(digits_only) >= 4:
            pfx_dig = f"%{digits_only}%"
            cdr_partial_sql = " OR c.target_msisdn LIKE ? OR c.other_msisdn LIKE ? OR c.target_norm LIKE ? OR c.other_norm LIKE ? "
            cdr_partial_params = [pfx_dig, pfx_dig, pfx_dig, pfx_dig]

        count_sql = f"""
        SELECT COUNT(*)
        FROM cdr_records c
        JOIN files f ON c.file_id = f.file_id
        WHERE (c.target_norm = ? 
           OR c.other_norm = ? 
           OR c.target_msisdn LIKE ? 
           OR c.other_msisdn LIKE ?
           OR (length(?) > 1 AND c.other_name_norm LIKE ?)
           OR c.other_name LIKE ?
           OR c.other_id LIKE ?
           OR c.raw_row LIKE ?
           {cdr_partial_sql}) {scope_clause_cdr};
        """
        cur_params = [
            norm_p or query,
            norm_p or query,
            pattern,
            pattern,
            norm_a,
            f"%{norm_a}%",
            pattern,
            pattern,
            pattern
        ] + cdr_partial_params + scope_params_cdr
        cur.execute(count_sql, cur_params)
        total_count = cur.fetchone()[0] or 0

        # Levenshtein fuzzy name match fallback if total_count == 0
        if total_count == 0 and len(query) >= 4 and not query.isdigit():
            clean_token = norm_a.split()[0] if norm_a else query
            max_dist = 1 if len(clean_token) <= 5 else 2
            fuzzy_count_sql = f"""
            SELECT COUNT(*)
            FROM cdr_records c
            JOIN files f ON c.file_id = f.file_id
            WHERE levenshtein(c.other_name_norm, ?) <= ? {scope_clause_cdr};
            """
            try:
                cur.execute(fuzzy_count_sql, [clean_token, max_dist] + scope_params_cdr)
                total_count = cur.fetchone()[0] or 0
                if total_count > 0:
                    sql_fuz = f"""
                    SELECT f.filename, c.sheet_name, c.row_idx, c.event_time, c.direction, 
                           c.target_msisdn, c.other_msisdn, c.other_name, c.duration, c.cell_address, 
                           f.file_path, c.raw_row, f.folder
                    FROM cdr_records c
                    JOIN files f ON c.file_id = f.file_id
                    WHERE levenshtein(c.other_name_norm, ?) <= ? {scope_clause_cdr}
                    ORDER BY c.event_time DESC
                    LIMIT ? OFFSET ?;
                    """
                    cur.execute(sql_fuz, [clean_token, max_dist] + scope_params_cdr + [limit, offset])
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
                            "duration": r[8] or "—",
                            "address": r[9] or "—",
                            "path": r[10],
                            "folder": r[12] or "",
                            "snippet": raw_text[:400] if raw_text else "—"
                        })
                    return {"type": "cdr", "rows": cdr_rows, "total": total_count, "limit": limit, "offset": offset, "mode": mode, "fuzzy": True}
            except Exception:
                pass

        if total_count > 0:
            sql = f"""
            SELECT f.filename, c.sheet_name, c.row_idx, c.event_time, c.direction, 
                   c.target_msisdn, c.other_msisdn, c.other_name, c.duration, c.cell_address, 
                   f.file_path, c.raw_row, f.folder
            FROM cdr_records c
            JOIN files f ON c.file_id = f.file_id
            WHERE (c.target_norm = ? 
               OR c.other_norm = ? 
               OR c.target_msisdn LIKE ? 
               OR c.other_msisdn LIKE ?
               OR (length(?) > 1 AND c.other_name_norm LIKE ?)
               OR c.other_name LIKE ?
               OR c.other_id LIKE ?
               OR c.raw_row LIKE ?
               {cdr_partial_sql}) {scope_clause_cdr}
            ORDER BY c.event_time DESC
            LIMIT ? OFFSET ?;
            """
            cur.execute(sql, cur_params + [limit, offset])
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
                    "duration": r[8] or "—",
                    "address": r[9] or "—",
                    "path": r[10],
                    "folder": r[12] or "",
                    "snippet": raw_text[:400] if raw_text else "—"
                })
            return {"type": "cdr", "rows": cdr_rows, "total": total_count, "limit": limit, "offset": offset, "mode": mode}

    # MODE B: GENERAL SEARCH (DEFAULT)
    # 1. Parse Google-style search operators (exact phrase, NOT -term, OR, AND, filetype:ext)
    parsed_q = parse_google_query(query)
    fts_expr = parsed_q["fts_match"]
    filetype_filter = parsed_q["filetype"]
    exact_phrases = parsed_q["exact_phrases"]
    clean_tokens = parsed_q["clean_tokens"]

    filetype_clause_fts = ""
    filetype_params_fts = []
    if filetype_filter:
        filetype_clause_fts = " AND lower(f.file_path) LIKE ? "
        filetype_params_fts = [f"%.{filetype_filter}"]

    # Exact token prioritization: if user searches "manial" or "john doe", rows containing the exact token get exact_prio = 0
    exact_prio_clause = " 1 as exact_prio, "
    exact_prio_params = []
    first_exact_term = exact_phrases[0] if exact_phrases else (clean_tokens[0] if clean_tokens else "")
    if first_exact_term:
        exact_prio_clause = " (CASE WHEN lower(u.content) LIKE ? THEN 0 ELSE 1 END) as exact_prio, "
        exact_prio_params = [f"%{first_exact_term.lower()}%"]

    total_fts = 0
    safe_fts = fts_expr or f'""{query.replace("\"", " ").strip()}""'
    fts_count_sql = f"""
    SELECT COUNT(*) 
    FROM universal_search u
    JOIN files f ON u.file_path = f.file_path
    WHERE universal_search MATCH ? {scope_clause_fts} {filetype_clause_fts};
    """
    try:
        cur.execute(fts_count_sql, [safe_fts] + scope_params_fts + filetype_params_fts)
        total_fts = cur.fetchone()[0] or 0
    except Exception:
        # Fallback to standard token FTS if complex syntax error
        try:
            clean_q = query.replace('"', ' ').strip()
            cur.execute(fts_count_sql, [f'"{clean_q}"'] + scope_params_fts + filetype_params_fts)
            total_fts = cur.fetchone()[0] or 0
            safe_fts = f'"{clean_q}"'
        except Exception:
            total_fts = 0

    if total_fts > 0:
        sql_fts = f"""
        SELECT u.file_path, u.sheet_name, u.row_idx, u.content,
               f.folder, f.indexed_at,
               c.event_time, c.direction, c.target_msisdn, c.other_msisdn, c.other_name, c.duration, c.cell_address,
               {exact_prio_clause}
               u.rank
        FROM universal_search u
        JOIN files f ON u.file_path = f.file_path
        LEFT JOIN cdr_records c ON c.file_id = f.file_id AND c.sheet_name = u.sheet_name AND c.row_idx = u.row_idx
        WHERE universal_search MATCH ? {scope_clause_fts} {filetype_clause_fts}
        ORDER BY exact_prio ASC, u.rank ASC
        LIMIT ? OFFSET ?;
        """
        cur.execute(sql_fts, exact_prio_params + [safe_fts] + scope_params_fts + filetype_params_fts + [limit, offset])
        raw_rows = cur.fetchall()
        conn.close()

        results = []
        for r in raw_rows:
            fpath = r[0]
            content_str = r[3] or ""
            fname = os.path.basename(fpath)
            fsize = None
            try:
                if os.path.exists(fpath):
                    fsize = os.path.getsize(fpath)
            except Exception:
                pass

            results.append({
                "file": fname,
                "folder": r[4] or os.path.dirname(fpath),
                "path": fpath,
                "sheet": r[1],
                "row": r[2],
                "content": content_str,
                "snippet": content_str[:500] if content_str else "—",
                "size": fsize,
                "indexed_at": r[5] or "—",
                "time": r[6] or "—",
                "dir": r[7] or "—",
                "target": r[8] or "—",
                "other": r[9] or "—",
                "name": r[10] or "—",
                "duration": r[11] or "—",
                "address": r[12] or "—"
            })
        return {"type": "general", "rows": results, "total": total_fts, "limit": limit, "offset": offset, "mode": mode}

    # 2. Fallback in General Mode: Check CDR records & partial number matching
    cdr_partial_sql = ""
    cdr_partial_params = []
    if len(digits_only) >= 4:
        pfx_dig = f"%{digits_only}%"
        cdr_partial_sql = " OR c.target_msisdn LIKE ? OR c.other_msisdn LIKE ? OR c.target_norm LIKE ? OR c.other_norm LIKE ? "
        cdr_partial_params = [pfx_dig, pfx_dig, pfx_dig, pfx_dig]

    count_sql = f"""
    SELECT COUNT(*)
    FROM cdr_records c
    JOIN files f ON c.file_id = f.file_id
    WHERE (c.target_norm = ? 
       OR c.other_norm = ? 
       OR c.target_msisdn LIKE ? 
       OR c.other_msisdn LIKE ?
       OR (length(?) > 1 AND c.other_name_norm LIKE ?)
       OR c.other_name LIKE ?
       OR c.other_id LIKE ?
       OR c.raw_row LIKE ?
       {cdr_partial_sql}) {scope_clause_cdr};
    """
    cur_params = [
        norm_p or query,
        norm_p or query,
        pattern,
        pattern,
        norm_a,
        f"%{norm_a}%",
        pattern,
        pattern,
        pattern
    ] + cdr_partial_params + scope_params_cdr
    try:
        cur.execute(count_sql, cur_params)
        total_count = cur.fetchone()[0] or 0
    except Exception:
        total_count = 0

    # 3. Levenshtein fuzzy name match in General mode fallback
    if total_count == 0 and len(query) >= 4 and not query.isdigit():
        clean_token = norm_a.split()[0] if norm_a else query
        max_dist = 1 if len(clean_token) <= 5 else 2
        fuzzy_count_sql = f"""
        SELECT COUNT(*)
        FROM cdr_records c
        JOIN files f ON c.file_id = f.file_id
        WHERE levenshtein(c.other_name_norm, ?) <= ? {scope_clause_cdr};
        """
        try:
            cur.execute(fuzzy_count_sql, [clean_token, max_dist] + scope_params_cdr)
            total_count = cur.fetchone()[0] or 0
            if total_count > 0:
                sql_fuz = f"""
                SELECT f.filename, c.sheet_name, c.row_idx, c.event_time, c.direction, 
                       c.target_msisdn, c.other_msisdn, c.other_name, c.duration, c.cell_address, 
                       f.file_path, c.raw_row, f.folder, f.indexed_at
                FROM cdr_records c
                JOIN files f ON c.file_id = f.file_id
                WHERE levenshtein(c.other_name_norm, ?) <= ? {scope_clause_cdr}
                ORDER BY c.event_time DESC
                LIMIT ? OFFSET ?;
                """
                cur.execute(sql_fuz, [clean_token, max_dist] + scope_params_cdr + [limit, offset])
                rows = cur.fetchall()
                conn.close()
                cdr_rows = []
                for r in rows:
                    raw_text = r[11] or ""
                    fpath = r[10]
                    fsize = None
                    try:
                        if os.path.exists(fpath):
                            fsize = os.path.getsize(fpath)
                    except Exception:
                        pass
                    cdr_rows.append({
                        "file": r[0],
                        "folder": r[12] or os.path.dirname(fpath),
                        "path": fpath,
                        "sheet": r[1],
                        "row": r[2],
                        "time": r[3] or "—",
                        "dir": r[4] or "—",
                        "target": r[5] or "—",
                        "other": r[6] or "—",
                        "name": r[7] or "—",
                        "duration": r[8] or "—",
                        "address": r[9] or "—",
                        "size": fsize,
                        "indexed_at": r[13] or "—",
                        "snippet": raw_text[:500] if raw_text else "—"
                    })
                return {"type": "general", "rows": cdr_rows, "total": total_count, "limit": limit, "offset": offset, "mode": mode, "fuzzy": True}
        except Exception:
            pass

    if total_count > 0:
        sql = f"""
        SELECT f.filename, c.sheet_name, c.row_idx, c.event_time, c.direction, 
               c.target_msisdn, c.other_msisdn, c.other_name, c.duration, c.cell_address, 
               f.file_path, c.raw_row, f.folder, f.indexed_at
        FROM cdr_records c
        JOIN files f ON c.file_id = f.file_id
        WHERE (c.target_norm = ? 
           OR c.other_norm = ? 
           OR c.target_msisdn LIKE ? 
           OR c.other_msisdn LIKE ?
           OR (length(?) > 1 AND c.other_name_norm LIKE ?)
           OR c.other_name LIKE ?
           OR c.other_id LIKE ?
           OR c.raw_row LIKE ?) {scope_clause_cdr}
        ORDER BY c.event_time DESC
        LIMIT ? OFFSET ?;
        """
        cur.execute(sql, cur_params + [limit, offset])
        rows = cur.fetchall()
        conn.close()

        cdr_rows = []
        for r in rows:
            raw_text = r[11] or ""
            fpath = r[10]
            fsize = None
            try:
                if os.path.exists(fpath):
                    fsize = os.path.getsize(fpath)
            except Exception:
                pass

            cdr_rows.append({
                "file": r[0],
                "folder": r[12] or os.path.dirname(fpath),
                "path": fpath,
                "sheet": r[1],
                "row": r[2],
                "time": r[3] or "—",
                "dir": r[4] or "—",
                "target": r[5] or "—",
                "other": r[6] or "—",
                "name": r[7] or "—",
                "duration": r[8] or "—",
                "address": r[9] or "—",
                "size": fsize,
                "indexed_at": r[13] or "—",
                "snippet": raw_text[:500] if raw_text else "—"
            })
        return {"type": "general" if mode == "general" else "cdr", "rows": cdr_rows, "total": total_count, "limit": limit, "offset": offset, "mode": mode}

    conn.close()
    return {"type": "general" if mode == "general" else "cdr", "rows": [], "total": 0, "limit": limit, "offset": offset, "mode": mode}

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

def start_indexing_thread(folder_path):
    """Run folder scan & parallel index with live progress tracking & auto-backup."""
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
        INDEX_STATE["current_file"] = "Creating safety backup & scanning folder..."
        INDEX_STATE["status_message"] = "Scanning folder..."

    def _worker():
        global INDEX_STATE
        try:
            # 1. Automatic safety snapshot before starting major index
            backup_database()

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
                return

            conn = sqlite3.connect(DB_PATH)
            try:
                indexer_engine.init_db(conn)
                total_records = 0

                completed = 0
                for fpath in files_to_scan:
                    fname = os.path.basename(fpath)
                    completed += 1
                    INDEX_STATE["current"] = completed
                    INDEX_STATE["current_file"] = fname
                    INDEX_STATE["percent"] = int((completed / len(files_to_scan)) * 100)
                    INDEX_STATE["status_message"] = f"Indexing {completed}/{len(files_to_scan)}: {fname}"

                    try:
                        cnt = indexer_engine.process_file(fpath, conn)
                        total_records += cnt
                        INDEX_STATE["records_indexed"] = total_records
                    except Exception as ex:
                        print(f"[INDEX ERROR] {fname}: {ex}")
            finally:
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
<title>OmniSearch | Universal Document & Intelligence Engine</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-primary: #080d1a;
    --bg-secondary: #0f172a;
    --bg-card: #111a2e;
    --bg-card-hover: #16223b;
    --border: #1e293b;
    --border-subtle: #1e293b80;
    --border-hover: #334155;
    --accent: #38bdf8;
    --accent-hover: #0ea5e9;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --text-dim: #64748b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-main);
    padding: 24px 32px;
    min-height: 100vh;
    max-width: 1440px;
    margin: 0 auto;
  }
  .arabic { font-family: 'Cairo', sans-serif; }

  /* SVG Icons */
  .icon-svg {
    width: 17px;
    height: 17px;
    display: inline-block;
    vertical-align: middle;
    flex-shrink: 0;
  }
  .icon-sm { width: 14px; height: 14px; }
  .icon-lg { width: 20px; height: 20px; }
  .icon-cyan { color: #38bdf8; }
  .icon-rose { color: #f43f5e; }
  .icon-emerald { color: #10b981; }
  .icon-amber { color: #f59e0b; }
  .icon-purple { color: #a855f7; }
  .icon-blue { color: #3b82f6; }
  .icon-indigo { color: #818cf8; }
  .icon-pink { color: #ec4899; }
  .icon-teal { color: #14b8a6; }
  .icon-slate { color: #94a3b8; }
  .icon-white { color: #ffffff; }

  /* Clean Minimalist Header */
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 18px;
    margin-bottom: 20px;
    border-bottom: 1px solid var(--border-subtle);
    flex-wrap: wrap;
    gap: 14px;
  }
  .header-brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .header-brand h1 {
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #f8fafc;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .header-brand span.subtitle {
    font-size: 0.8rem;
    color: var(--text-dim);
    font-weight: 400;
    margin-left: 4px;
  }
  .header-actions {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }

  /* Watcher Status Switch Pill */
  .watcher-switch {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #090e1a;
    border: 1px solid var(--border);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    user-select: none;
  }
  .watcher-switch:hover {
    border-color: var(--border-hover);
  }
  .watcher-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    transition: all 0.2s;
  }
  .watcher-dot.active {
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }
  .watcher-dot.paused {
    background: #f43f5e;
    box-shadow: 0 0 6px rgba(244, 63, 94, 0.6);
  }

  .stats-pill {
    font-size: 0.8rem;
    color: var(--text-muted);
    background: #090e1a;
    border: 1px solid var(--border-subtle);
    padding: 6px 12px;
    border-radius: 8px;
  }

  .btn-header {
    background: #090e1a;
    border: 1px solid var(--border);
    color: #cbd5e1;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
  }
  .btn-header:hover {
    background: #1e293b;
    border-color: var(--accent);
    color: #fff;
  }
  .btn-header.primary {
    background: linear-gradient(135deg, #0284c7, #0369a1);
    border-color: #38bdf860;
    color: #fff;
    font-weight: 600;
  }
  .btn-header.primary:hover {
    background: linear-gradient(135deg, #0ea5e9, #0284c7);
  }

  /* Tools Dropdown Menu */
  .dropdown {
    position: relative;
    display: inline-block;
  }
  .dropdown-content {
    display: none;
    position: absolute;
    right: 0;
    top: 100%;
    margin-top: 6px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 10px;
    min-width: 170px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
    z-index: 1000;
    padding: 6px;
  }
  .dropdown.open .dropdown-content { display: block; }
  .dropdown-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.82rem;
    color: #cbd5e1;
    cursor: pointer;
    background: transparent;
    border: none;
    width: 100%;
    text-align: left;
    transition: background 0.15s;
  }
  .dropdown-item:hover {
    background: #1e293b;
    color: #fff;
  }

  /* Navigation Tabs */
  .nav-tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 20px;
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: 0px;
  }
  .nav-tab-btn {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-muted);
    padding: 10px 18px;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    transition: all 0.2s;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
  }
  .nav-tab-btn:hover {
    color: #f8fafc;
  }
  .nav-tab-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
    font-weight: 600;
  }
  .nav-tab-badge {
    background: rgba(56, 189, 248, 0.12);
    color: #38bdf8;
    border-radius: 9999px;
    font-size: 0.7rem;
    padding: 1px 7px;
    font-weight: 600;
  }

  /* Hero Search Container */
  .search-container {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 22px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
  }
  .search-bar-row {
    display: flex;
    gap: 10px;
    position: relative;
    align-items: center;
  }
  .search-icon-inside {
    position: absolute;
    left: 14px;
    pointer-events: none;
  }
  input[type="text"] {
    flex: 1;
    background: #090e1a;
    border: 1px solid var(--border);
    color: #fff;
    padding: 12px 42px 12px 42px;
    border-radius: 8px;
    font-size: 0.98rem;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  input[type="text"]:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
  }
  .clear-btn {
    position: absolute;
    right: 120px;
    background: none;
    border: none;
    color: #64748b;
    cursor: pointer;
    display: none;
    padding: 4px;
  }
  .clear-btn:hover { color: #f43f5e; }
  .btn-search {
    background: linear-gradient(135deg, #38bdf8, #0ea5e9);
    color: #0b1120;
    border: none;
    padding: 11px 24px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.92rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
  }
  .btn-search:hover {
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.4);
    transform: translateY(-1px);
  }

  /* Search Mode Switcher */
  .search-mode-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-subtle);
    flex-wrap: wrap;
    gap: 8px;
  }
  .search-mode-pills {
    display: flex;
    gap: 4px;
    background: #090e1a;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 3px;
  }
  .mode-pill {
    background: transparent;
    border: none;
    color: var(--text-muted);
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s ease;
  }
  .mode-pill:hover {
    color: #f8fafc;
  }
  .mode-pill.active {
    background: var(--accent);
    color: #080d1a;
    box-shadow: 0 2px 8px rgba(56, 189, 248, 0.35);
  }
  .mode-pill.telecom-mode.active {
    background: linear-gradient(135deg, #10b981, #059669);
    color: #fff;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.35);
  }
  .mode-desc-text {
    font-size: 0.78rem;
    color: var(--text-dim);
  }

  /* Segmented Category Filter Tabs */
  .filter-tabs-row {
    display: flex;
    gap: 6px;
    margin-top: 12px;
    flex-wrap: wrap;
    align-items: center;
  }
  .filter-pill {
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-muted);
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
  }
  .filter-pill:hover {
    color: #f8fafc;
    background: #1e293b40;
  }
  .filter-pill.active {
    background: rgba(56, 189, 248, 0.12);
    border-color: rgba(56, 189, 248, 0.4);
    color: #38bdf8;
    font-weight: 600;
  }

  /* Custom Shortcuts Bar */
  .quick-chips {
    display: flex;
    gap: 6px;
    margin-top: 10px;
    align-items: center;
    font-size: 0.78rem;
    color: var(--text-dim);
    flex-wrap: wrap;
    border-top: 1px solid #1e293b40;
    padding-top: 10px;
  }
  .chip {
    background: #090e1a;
    border: 1px solid var(--border-subtle);
    padding: 3px 8px;
    border-radius: 5px;
    cursor: pointer;
    color: #cbd5e1;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.78rem;
    transition: all 0.15s;
  }
  .chip:hover {
    border-color: var(--accent);
    color: #fff;
  }
  .btn-add-chip {
    background: transparent;
    border: 1px dashed var(--border);
    color: var(--text-dim);
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn-add-chip:hover {
    border-color: var(--accent);
    color: #fff;
  }

  /* Status Bar */
  .status-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    font-size: 0.84rem;
    color: var(--text-muted);
    flex-wrap: wrap;
    gap: 8px;
  }
  .view-toggle {
    display: flex;
    background: #090e1a;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }
  .view-btn {
    background: none;
    border: none;
    color: #94a3b8;
    padding: 5px 12px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s;
  }
  .view-btn.active {
    background: var(--accent);
    color: #090e1a;
    font-weight: 600;
  }

  /* Cards Results */
  .cards-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .result-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease;
  }
  .result-card:hover {
    background: var(--bg-card-hover);
    border-color: rgba(56, 189, 248, 0.4);
    transform: translateY(-1px);
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }
  .file-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.94rem;
    font-weight: 600;
    color: #f8fafc;
    word-break: break-all;
  }
  .file-type-pill {
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    text-transform: uppercase;
  }
  .pill-pdf { background: #dc262615; border: 1px solid #dc262650; color: #f87171; }
  .pill-xlsx, .pill-xls, .pill-csv { background: #05966915; border: 1px solid #05966950; color: #34d399; }
  .pill-docx, .pill-doc, .pill-odt { background: #2563eb15; border: 1px solid #2563eb50; color: #60a5fa; }
  .pill-image { background: #a855f715; border: 1px solid #a855f750; color: #c084fc; }
  .pill-txt { background: #14b8a615; border: 1px solid #14b8a650; color: #2dd4bf; }

  .card-actions {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
  }
  .btn-action {
    background: #090e1a;
    border: 1px solid var(--border);
    color: #cbd5e1;
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s;
  }
  .btn-action:hover {
    border-color: var(--accent);
    color: #fff;
    background: #1e293b;
  }
  .btn-image-preview {
    background: rgba(168, 85, 247, 0.15);
    border: 1px solid #a855f770;
    color: #d8b4fe;
    padding: 5px 11px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.2s;
  }
  .btn-image-preview:hover {
    background: #a855f7;
    color: #fff;
  }

  .card-pill-group {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 10px;
  }
  .info-pill {
    background: #090e1a;
    border: 1px solid var(--border-subtle);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #cbd5e1;
    cursor: pointer;
    user-select: none;
    transition: all 0.15s;
  }
  .info-pill:hover {
    border-color: var(--accent);
    color: #fff;
  }
  .general-card-meta {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-bottom: 10px;
  }
  .meta-tag {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .snippet-box {
    background: #080d1a;
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    line-height: 1.6;
    color: #cbd5e1;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .snippet-box mark, .match-hl {
    background: rgba(56, 189, 248, 0.28);
    border-bottom: 2px solid var(--accent);
    color: #fff;
    padding: 1px 4px;
    border-radius: 3px;
    font-weight: 600;
  }

  /* Table Grid */
  .table-container {
    overflow-x: auto;
    border: 1px solid var(--border);
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    margin-bottom: 20px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.83rem;
    text-align: left;
  }
  th {
    background: #090e1a;
    padding: 10px 12px;
    font-weight: 600;
    color: var(--accent);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  td {
    padding: 9px 12px;
    border-bottom: 1px solid #1e293b50;
    color: #e2e8f0;
    vertical-align: middle;
  }
  tr:hover td { background: #1e293b40; }

  /* Custom Dark Scrollbar */
  ::-webkit-scrollbar {
    width: 9px;
    height: 9px;
  }
  ::-webkit-scrollbar-track {
    background: #080d1a;
  }
  ::-webkit-scrollbar-thumb {
    background: #1e293b;
    border-radius: 6px;
    border: 2px solid #080d1a;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: #334155;
  }

  /* Pagination Bar (Top & Bottom) */
  .pagination-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 16px;
    margin-bottom: 16px;
    font-size: 0.82rem;
    color: var(--text-muted);
  }
  .pagination-bar.top-bar {
    margin-top: 8px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-subtle);
  }
  .pagination-btns {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .page-btn {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    color: #cbd5e1;
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }
  .page-btn:hover:not(:disabled) {
    background: #1e293b;
    border-color: var(--accent);
    color: #fff;
  }
  .page-btn:disabled { opacity: 0.35; cursor: not-allowed; }

  /* Floating Scroll Navigation Buttons */
  .scroll-nav-container {
    position: fixed;
    right: 24px;
    bottom: 28px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    z-index: 999;
  }
  .scroll-nav-btn {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    color: #cbd5e1;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    transition: all 0.2s ease;
    user-select: none;
  }
  .scroll-nav-btn:hover {
    background: #1e293b;
    border-color: var(--accent);
    color: var(--accent);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(56, 189, 248, 0.25);
  }

  /* Scoped Folder Picker Tab */
  .scoped-config-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
  }
  .scoped-methods {
    display: grid;
    grid-template-columns: 1.1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
  }
  @media (max-width: 860px) {
    .scoped-methods { grid-template-columns: 1fr; }
  }
  .scoped-box {
    background: #090e1a;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .scoped-box h4 {
    font-size: 0.94rem;
    color: #f8fafc;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .scoped-box p {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 12px;
    line-height: 1.4;
  }
  .folder-picker-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: auto;
  }
  .btn-folder-pick {
    background: linear-gradient(135deg, #d97706, #b45309);
    color: #fff;
    border: 1px solid #f59e0b80;
    padding: 9px 16px;
    border-radius: 7px;
    font-weight: 600;
    font-size: 0.84rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    transition: all 0.2s;
  }
  .btn-folder-pick:hover {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    transform: translateY(-1px);
  }
  .btn-file-pick {
    background: #1e293b;
    color: #cbd5e1;
    border: 1px solid var(--border);
    padding: 9px 12px;
    border-radius: 7px;
    font-weight: 500;
    font-size: 0.82rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
  }
  .btn-file-pick:hover {
    background: #334155;
    color: #fff;
  }
  .btn-folder-subtle {
    background: transparent;
    color: var(--text-dim);
    border: 1px dashed var(--border);
    padding: 9px 10px;
    border-radius: 7px;
    font-size: 0.78rem;
    cursor: pointer;
  }
  .btn-folder-subtle:hover { color: #fff; border-color: var(--accent); }

  .drop-zone {
    border: 2px dashed #38bdf850;
    border-radius: 8px;
    padding: 20px 14px;
    text-align: center;
    cursor: pointer;
    background: #090e1a80;
    transition: all 0.2s;
  }
  .drop-zone:hover, .drop-zone.dragover {
    border-color: var(--accent);
    background: rgba(56, 189, 248, 0.08);
  }
  .drop-zone p { margin-bottom: 0; color: #cbd5e1; font-size: 0.82rem; }

  .active-scope-banner {
    background: rgba(56, 189, 248, 0.08);
    border: 1px solid #0284c760;
    border-radius: 8px;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.84rem;
    color: #f8fafc;
    margin-bottom: 16px;
  }
  .scope-name-tag {
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent);
    font-weight: 600;
    word-break: break-all;
  }
  .btn-clear-scope {
    background: #ef444420;
    border: 1px solid #ef444450;
    color: #f87171;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
  }
  .btn-clear-scope:hover { background: #ef4444; color: #fff; }

  /* Live Progress Banner */
  .progress-banner {
    display: none;
    background: var(--bg-secondary);
    border: 1px solid var(--accent);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 18px;
  }
  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.84rem;
    margin-bottom: 6px;
  }
  .progress-bar-bg {
    width: 100%;
    height: 8px;
    background: #090e1a;
    border-radius: 4px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #38bdf8, #10b981);
    transition: width 0.3s ease;
  }

  /* Modals */
  .modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.8);
    z-index: 10000;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(8px);
  }
  .modal-overlay.active { display: flex; }
  .modal-content {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    padding: 22px;
    border-radius: 12px;
    width: 92%;
    max-width: 540px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.7);
  }
  .modal-content h3 {
    margin-bottom: 10px;
    color: var(--accent);
    font-size: 1.15rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .modal-content p {
    font-size: 0.84rem;
    color: var(--text-muted);
    margin-bottom: 14px;
    line-height: 1.45;
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 18px;
  }

  /* Image & Selectable OCR Split Inspector Modal */
  .image-modal-wide {
    max-width: 1280px;
    width: 96%;
    height: 90vh;
    max-height: 92vh;
    display: flex;
    flex-direction: column;
    padding: 18px 22px;
  }
  .image-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-subtle);
    flex-wrap: wrap;
    gap: 8px;
  }
  .image-modal-title {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .image-modal-controls {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .image-ocr-notice {
    font-size: 0.82rem;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.25);
    padding: 6px 12px;
    border-radius: 6px;
    margin-top: 10px;
  }
  .image-inspector-split {
    flex: 1;
    display: grid;
    grid-template-columns: 1.3fr 1fr;
    gap: 16px;
    min-height: 0;
    overflow: hidden;
    margin-top: 10px;
  }
  @media (max-width: 920px) {
    .image-inspector-split {
      grid-template-columns: 1fr;
      grid-template-rows: 1.2fr 1fr;
    }
  }
  .image-scroll-wrapper {
    flex: 1;
    overflow: auto;
    background: #050811;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    position: relative;
    min-height: 0;
  }
  .ocr-preview-container {
    position: relative;
    display: inline-block;
    max-width: 100%;
    margin: 0 auto;
  }

  /* OCR Word Highlight Boxes on Image */
  .ocr-highlight-box {
    position: absolute;
    box-sizing: border-box;
    border: 1.5px solid rgba(168, 85, 247, 0.45);
    background: rgba(168, 85, 247, 0.12);
    pointer-events: auto;
    border-radius: 2px;
    transition: all 0.15s ease;
    cursor: text;
    z-index: 10;
    display: flex;
    align-items: center;
    overflow: hidden;
  }
  .ocr-highlight-box:hover {
    background: rgba(168, 85, 247, 0.4);
    border-color: #a855f7;
    box-shadow: 0 0 8px rgba(168, 85, 247, 0.8);
    z-index: 25;
  }
  .ocr-highlight-box.active-match {
    border: 2.5px solid #38bdf8 !important;
    background: rgba(56, 189, 248, 0.4) !important;
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.95) !important;
    z-index: 50;
    animation: matchPulse 1.5s infinite alternate;
  }
  @keyframes matchPulse {
    0% { transform: scale(1); box-shadow: 0 0 8px rgba(56, 189, 248, 0.7); }
    100% { transform: scale(1.05); box-shadow: 0 0 16px rgba(56, 189, 248, 1); }
  }

  /* Transparent Live Text Layer for Direct Mouse Dragging Selection */
  .ocr-live-text {
    font-size: 11px;
    line-height: 1;
    color: transparent;
    user-select: text;
    -webkit-user-select: text;
    width: 100%;
    height: 100%;
    display: block;
    overflow: hidden;
    pointer-events: auto;
    cursor: text;
  }
  ::selection {
    background: rgba(56, 189, 248, 0.45);
    color: #fff;
  }

  /* OCR Extracted Text Inspector Sidebar */
  .ocr-text-inspector {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #090e1a;
    border: 1px solid var(--border);
    border-radius: 10px;
    min-height: 0;
    overflow: hidden;
  }
  .ocr-inspector-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border-subtle);
    background: #0d1424;
    flex-wrap: wrap;
    gap: 8px;
  }
  .ocr-panel-pill {
    font-size: 0.74rem;
    font-weight: 700;
    background: #0284c725;
    border: 1px solid #0284c760;
    color: #38bdf8;
    padding: 2px 8px;
    border-radius: 4px;
    text-transform: uppercase;
  }
  .ocr-count-badge {
    font-size: 0.76rem;
    color: var(--text-muted);
  }
  .ocr-inspector-hint {
    padding: 6px 14px;
    background: #090e1a;
    font-size: 0.74rem;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border-subtle);
  }
  .ocr-text-container {
    flex: 1;
    overflow-y: auto;
    padding: 14px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.86rem;
    line-height: 1.65;
    color: #f1f5f9;
    user-select: text;
    -webkit-user-select: text;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .ocr-line {
    padding: 3px 6px;
    border-radius: 4px;
    transition: background 0.15s;
    display: flex;
    gap: 10px;
    align-items: flex-start;
    cursor: text;
  }
  .ocr-line:hover { background: rgba(56, 189, 248, 0.08); }
  .ocr-line-num {
    color: #475569;
    font-size: 0.75rem;
    user-select: none;
    width: 24px;
    text-align: right;
    flex-shrink: 0;
  }
  .ocr-line-content { flex: 1; user-select: text; -webkit-user-select: text; }
  .ocr-mark {
    background: #f59e0b;
    color: #000;
    padding: 1px 4px;
    border-radius: 3px;
    font-weight: 700;
  }
  .image-modal-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--border-subtle);
  }

  .toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #0f172a;
    border: 1px solid var(--accent);
    color: #fff;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 0.86rem;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
    z-index: 100000;
    opacity: 0;
    transform: translateY(10px);
    transition: all 0.25s ease;
    pointer-events: none;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .toast.show { opacity: 1; transform: translateY(0); }
</style>
</head>
<body>

  <!-- Set Folder Dialog Modal -->
  <div id="folderModal" class="modal-overlay">
    <div class="modal-content">
      <h3><span class="icon-amber" id="folderModalIcon"></span> Set Folder to Index</h3>
      <p>Choose any directory path to scan, OCR, and index all documents (<code>.xlsx</code>, <code>.docx</code>, <code>.pdf</code>, <code>.png</code>, <code>.jpg</code>, <code>.csv</code>). Subfolders will be indexed with multi-core OCR and continuously watched.</p>
      <div style="display:flex; flex-direction:column; gap:10px; margin-bottom:14px;">
        <div style="display:flex; gap:8px;">
          <button class="btn-folder-pick" style="flex:1;" onclick="pickFolderModalNative()">
            <span class="icon-white" id="folderModalBtnIcon"></span> Browse Folder (Native Chooser)...
          </button>
          <input type="file" id="modalWebkitFolderInput" webkitdirectory directory multiple style="display:none;" onchange="handleModalWebkitFolder(event)">
          <button class="btn-folder-subtle" onclick="document.getElementById('modalWebkitFolderInput').click()" title="Select via browser file picker">
            Browser Chooser
          </button>
        </div>
        <input type="text" id="folderPathInput" style="width:100%;" placeholder="Selected path will appear here...">
      </div>
      <div class="modal-actions">
        <button class="btn-header" onclick="closeFolderModal()">Cancel</button>
        <button class="btn-header primary" onclick="submitFolderIndex()">Start Indexing</button>
      </div>
    </div>
  </div>

  <!-- Add Quick Filter Modal -->
  <div id="filterModal" class="modal-overlay">
    <div class="modal-content">
      <h3><span class="icon-pink" id="filterModalIcon"></span> Add Quick Filter</h3>
      <p>Create a custom shortcut saved in the database for instant one-click searches.</p>
      <div style="margin-bottom: 10px;">
        <label style="display:block; font-size:0.78rem; color:var(--text-muted); margin-bottom:4px;">Filter Label:</label>
        <input type="text" id="filterNameInput" style="width:100%;" placeholder="e.g. VIP Target, Cairo Cases, Scanned Invoices">
      </div>
      <div style="margin-bottom: 14px;">
        <label style="display:block; font-size:0.78rem; color:var(--text-muted); margin-bottom:4px;">Search Query:</label>
        <input type="text" id="filterQueryInput" style="width:100%;" placeholder="e.g. 01012345678 or سوزان or Contract...">
      </div>
      <div class="modal-actions">
        <button class="btn-header" onclick="closeFilterModal()">Cancel</button>
        <button class="btn-header primary" onclick="submitFilter()">Save Filter</button>
      </div>
    </div>
  </div>

  <!-- Bookmark Modal -->
  <div id="bookmarkModal" class="modal-overlay">
    <div class="modal-content">
      <h3><span class="icon-pink" id="bookmarkModalIcon"></span> Bookmark / Tag Record</h3>
      <p id="bookmarkTargetLabel" style="font-family:'JetBrains Mono', monospace; color:#38bdf8;"></p>
      <input type="hidden" id="bmFilePath">
      <input type="hidden" id="bmSheetName">
      <input type="hidden" id="bmRowIdx">
      <div style="margin-bottom: 10px;">
        <label style="display:block; font-size:0.78rem; color:var(--text-muted); margin-bottom:4px;">Tag / Classification:</label>
        <select id="bmTagInput" style="width:100%; padding:8px; border-radius:6px; background:#090e1a; color:#fff; border:1px solid var(--border);">
          <option value="Lead">🌟 Key Lead</option>
          <option value="Suspect">🚨 Target / Suspect</option>
          <option value="Reviewed">✅ Reviewed</option>
          <option value="False Positive">❌ False Positive</option>
        </select>
      </div>
      <div style="margin-bottom: 14px;">
        <label style="display:block; font-size:0.78rem; color:var(--text-muted); margin-bottom:4px;">Notes / Annotation:</label>
        <textarea id="bmNotesInput" rows="3" style="width:100%; padding:8px; border-radius:6px; background:#090e1a; color:#fff; border:1px solid var(--border);" placeholder="Add investigative note or reference..."></textarea>
      </div>
      <div class="modal-actions">
        <button class="btn-header" onclick="closeBookmarkModal()">Cancel</button>
        <button class="btn-header primary" onclick="submitBookmark()">Save Bookmark</button>
      </div>
    </div>
  </div>

  <!-- Context Preview Modal -->
  <div id="contextModal" class="modal-overlay">
    <div class="modal-content" style="max-width: 700px;">
      <h3><span class="icon-purple" id="contextModalIcon"></span> Context Window (±3 Lines)</h3>
      <p id="contextFileLabel" style="font-size:0.8rem; color:var(--text-muted); word-break:break-all;"></p>
      <div id="contextLinesBox" style="background:#090e1a; border:1px solid var(--border); border-radius:8px; padding:12px; max-height:360px; overflow-y:auto; font-family:'JetBrains Mono', monospace; font-size:0.84rem; line-height:1.6;">
        Loading context...
      </div>
      <div class="modal-actions">
        <button class="btn-header primary" onclick="document.getElementById('contextModal').classList.remove('active')">Close</button>
      </div>
    </div>
  </div>

  <!-- Image & Selectable OCR Visual Split Inspector Modal -->
  <div id="imagePreviewModal" class="modal-overlay">
    <div class="modal-content image-modal-wide">
      <div class="image-modal-header">
        <div class="image-modal-title">
          <span class="icon-purple icon-lg" id="imageModalIcon"></span>
          <div>
            <h3 style="margin:0 0 2px 0;">Image Preview & OCR Inspector</h3>
            <p id="imagePreviewFileLabel" style="font-size:0.78rem; color:var(--text-muted); margin:0; word-break:break-all;"></p>
          </div>
        </div>
        <div class="image-modal-controls">
          <button class="btn-header" onclick="toggleOcrBoxes()" id="ocrToggleBtn" title="Toggle OCR Word Highlight Boxes">
            <span class="icon-cyan" id="ocrToggleIcon"></span> Boxes: ON
          </button>
          <button class="btn-header" onclick="zoomImage(0.2)" title="Zoom In"><span class="icon-slate" id="zoomInIcon"></span></button>
          <button class="btn-header" onclick="zoomImage(-0.2)" title="Zoom Out"><span class="icon-slate" id="zoomOutIcon"></span></button>
          <button class="btn-header" onclick="resetImageZoom()" title="Reset Zoom"><span class="icon-slate" id="resetZoomIcon"></span></button>
          <button class="btn-header" onclick="closeImagePreview()" title="Close"><span class="icon-rose" id="closeModalIcon"></span></button>
        </div>
      </div>

      <div id="imageOcrNotice" class="image-ocr-notice" style="display:none;"></div>

      <div class="image-inspector-split">
        <!-- Visual Canvas with OCR Overlay & Transparent Selectable Text Layer -->
        <div id="imageScrollWrapper" class="image-scroll-wrapper">
          <div id="ocrPreviewContainer" class="ocr-preview-container">
            <img id="imagePreviewElement" src="" alt="OCR Preview" style="display:block; max-width:100%; height:auto; border-radius:4px; transform-origin: top center; transition: transform 0.15s ease;" />
            <div id="ocrBoxesOverlay" style="position:absolute; top:0; left:0; width:100%; height:100%;"></div>
          </div>
        </div>

        <!-- Full Extracted Text Inspector Sidebar with Copy Actions -->
        <div class="ocr-text-inspector">
          <div class="ocr-inspector-top">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="ocr-panel-pill">Extracted Text</span>
              <span id="ocrWordsCountBadge" class="ocr-count-badge">0 words</span>
            </div>
            <div style="display:flex; gap:6px;">
              <button class="btn-header primary" onclick="copyAllOcrText()" title="Copy entire extracted text">
                <span class="icon-white" id="copyAllIcon"></span> Copy All Text
              </button>
              <button class="btn-header" onclick="copySelectedOcrText()" title="Copy text currently highlighted with mouse">
                ✂️ Copy Selection
              </button>
            </div>
          </div>
          <div class="ocr-inspector-hint">
            💡 Select any text with your mouse or drag across words on the image to copy directly.
          </div>
          <div id="ocrTextContainer" class="ocr-text-container" tabindex="0">
            <div style="color:#64748b; padding:20px; text-align:center;">Loading extracted text...</div>
          </div>
        </div>
      </div>

      <div class="image-modal-footer">
        <span id="ocrStatusDetails" style="font-size:0.78rem; color:var(--text-muted); margin-right:auto; align-self:center;"></span>
        <button class="btn-header primary" onclick="closeImagePreview()">Done</button>
      </div>
    </div>
  </div>

  <!-- Hidden File Input for Importing DB -->
  <input type="file" id="dbFileInput" accept=".db,.sqlite,.sqlite3" style="display:none;" onchange="handleImportFile(event)">

  <!-- Header -->
  <div class="header">
    <div class="header-brand">
      <h1>
        <span class="icon-cyan icon-lg" id="appLogoIcon"></span>
        OmniSearch
      </h1>
      <span class="subtitle">Universal Archive & Intelligence Explorer</span>
    </div>

    <div class="header-actions">
      <!-- Minimalist Watcher Toggle Switch -->
      <div class="watcher-switch" id="watcherBadge" onclick="toggleWatcher()" title="Click to toggle continuous file monitoring">
        <span class="watcher-dot active" id="watcherDot"></span>
        <span id="watcherLabel" style="color:#10b981;">Watcher Active</span>
      </div>

      <span class="stats-pill" id="statsBadge">Loading...</span>

      <button class="btn-header primary" onclick="openFolderModal()">
        <span class="icon-white" id="headerFolderIcon"></span> + Index Folder
      </button>

      <!-- Tools Dropdown Menu to prevent UI clutter -->
      <div class="dropdown" id="toolsDropdown">
        <button class="btn-header" onclick="toggleToolsDropdown(event)">
          <span class="icon-slate" id="toolsIcon"></span> Tools ▾
        </button>
        <div class="dropdown-content">
          <button class="dropdown-item" onclick="viewBookmarks()">
            <span class="icon-pink" id="menuBookmarkIcon"></span> Bookmarks (<span id="bmCountBadge">0</span>)
          </button>
          <button class="dropdown-item" onclick="triggerBackup()">
            <span class="icon-emerald" id="menuBackupIcon"></span> Snapshot Backup
          </button>
          <button class="dropdown-item" onclick="exportIndex()">
            <span class="icon-blue" id="menuExportIcon"></span> Export Index (.db)
          </button>
          <button class="dropdown-item" onclick="document.getElementById('dbFileInput').click()">
            <span class="icon-cyan" id="menuImportIcon"></span> Import Index (.db)
          </button>
          <button class="dropdown-item" onclick="exportCSV()">
            <span class="icon-emerald" id="menuCsvIcon"></span> Export Results CSV
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Top Navigation Tabs -->
  <div class="nav-tabs">
    <button id="tabBtnGlobal" class="nav-tab-btn active" onclick="switchMainTab('global')">
      <span class="icon-cyan" id="tabGlobalIcon"></span>
      Universal Archive
      <span class="nav-tab-badge">Full</span>
    </button>
    <button id="tabBtnScoped" class="nav-tab-btn" onclick="switchMainTab('scoped')">
      <span class="icon-indigo" id="tabScopedIcon"></span>
      Scoped Target Search
      <span class="nav-tab-badge" id="scopedTargetBadge">Folder or File</span>
    </button>
  </div>

  <!-- TAB 1: GLOBAL ARCHIVE SEARCH -->
  <div id="tabGlobalPane">
    <!-- Progress Banner -->
    <div id="progressBanner" class="progress-banner">
      <div class="progress-info">
        <span id="progressStatus" style="font-weight: 600; color: #f8fafc;">Indexing documents...</span>
        <span id="progressPercent" style="font-weight: 700; color: var(--accent);">0%</span>
      </div>
      <div class="progress-bar-bg">
        <div id="progressBarFill" class="progress-bar-fill"></div>
      </div>
      <div style="display:flex; justify-content:space-between; margin-top:6px; font-size:0.76rem; color:var(--text-muted);">
        <span id="progressCurrentFile">Scanning...</span>
        <span id="progressRecords">0 records indexed</span>
      </div>
    </div>

    <!-- Search Hero Box -->
    <div class="search-container">
      <!-- Search Mode Switcher (General Search default vs Telecom/CDR) -->
      <div class="search-mode-row">
        <div class="search-mode-pills">
          <button id="modeBtnGeneral" class="mode-pill active" onclick="setSearchMode('general')" title="Universal full-text document search">
            <span class="icon-cyan" id="modeGeneralIcon"></span> General Search
          </button>
          <button id="modeBtnTelecom" class="mode-pill telecom-mode" onclick="setSearchMode('telecom')" title="Investigative phone & CDR records explorer">
            <span class="icon-emerald" id="modeTelecomIcon"></span> Telecom / CDR Mode
          </button>
        </div>
        <span class="mode-desc-text" id="modeDescText">📄 Universal search across documents, PDFs, OCR, sheets & text</span>
      </div>

      <div class="search-bar-row">
        <span class="search-icon-inside icon-cyan" id="searchHeroIcon"></span>
        <input type="text" id="queryInput" placeholder="Search keywords, Egyptian/EN names, phones, IDs, snippets, OCR images..." oninput="handleInput(event)" onkeydown="if(event.key==='Enter') doSearch(0)" autofocus>
        <button id="clearSearchBtn" class="clear-btn" onclick="clearSearch()" title="Clear">
          <span class="icon-rose" id="clearSearchIcon"></span>
        </button>
        <button class="btn-search" onclick="doSearch(0)">
          <span class="icon-slate" id="btnSearchIcon"></span> Search
        </button>
      </div>

      <!-- Segmented Category Filters -->
      <div class="filter-tabs-row">
        <button class="filter-pill active" onclick="setTypeFilter('all', this)">
          <span class="icon-amber" id="filterAllIcon"></span> All
        </button>
        <button class="filter-pill" onclick="setTypeFilter('doc', this)">
          <span class="icon-rose" id="filterDocIcon"></span> Documents
        </button>
        <button class="filter-pill" onclick="setTypeFilter('sheet', this)">
          <span class="icon-emerald" id="filterSheetIcon"></span> Spreadsheets
        </button>
        <button class="filter-pill" onclick="setTypeFilter('image', this)">
          <span class="icon-purple" id="filterImageIcon"></span> Images & OCR
        </button>
        <button class="filter-pill" onclick="setTypeFilter('phone', this)">
          <span class="icon-teal" id="filterPhoneIcon"></span> Phone & CDR
        </button>
      </div>

      <!-- Saved Quick Shortcuts -->
      <div class="quick-chips" id="quickChipsContainer">
        <span style="color:var(--text-dim);">Shortcuts:</span>
        <div id="quickChipsList" style="display:inline-flex; flex-wrap:wrap; gap:5px; align-items:center;">
          <!-- Populated from DB -->
        </div>
        <button class="btn-add-chip" onclick="openFilterModal()" title="Save custom search filter">+ Add</button>
      </div>
    </div>

    <!-- Results Status Bar & View Toggle -->
    <div class="status-bar">
      <div>
        <span id="resultsCount" style="font-weight:600; color:#f8fafc;">Ready</span>
        <span style="margin-left:6px; opacity:0.6;" id="timing">0ms</span>
      </div>
      <div class="view-toggle">
        <button id="btnViewCard" class="view-btn active" onclick="switchView('card')">
          <span class="icon-indigo" id="viewCardIcon"></span> Cards
        </button>
        <button id="btnViewTable" class="view-btn" onclick="switchView('table')">
          <span class="icon-slate" id="viewTableIcon"></span> Dense Grid
        </button>
      </div>
    </div>

    <!-- Top Pagination Bar -->
    <div id="topPaginationBar" class="pagination-bar top-bar" style="display:none;">
      <span id="topPageInfo">Showing 0-0 of 0</span>
      <div class="pagination-btns">
        <button id="topPrevBtn" class="page-btn" onclick="changePage(-1)">← Prev</button>
        <span id="topPageNumberBadge" style="font-weight:600; color:var(--accent);">Page 1</span>
        <button id="topNextBtn" class="page-btn" onclick="changePage(1)">Next →</button>
      </div>
    </div>

    <!-- Results Containers -->
    <div id="cardsContainer" class="cards-container">
      <div style="text-align:center; padding: 48px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle);">
        Enter any keyword, name, or phone number above to search across the entire archive.
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

    <!-- Pagination -->
    <div id="paginationBar" class="pagination-bar" style="display:none;">
      <span id="pageInfo">Showing 0-0 of 0</span>
      <div class="pagination-btns">
        <button id="prevBtn" class="page-btn" onclick="changePage(-1)">← Prev</button>
        <span id="pageNumberBadge" style="font-weight:600; color:var(--accent);">Page 1</span>
        <button id="nextBtn" class="page-btn" onclick="changePage(1)">Next →</button>
      </div>
    </div>
  </div>

  <!-- TAB 2: SCOPED / TARGET SEARCH -->
  <div id="tabScopedPane" style="display:none;">
    <div class="scoped-config-card">
      <div class="scoped-methods">
        <!-- Option 1: Native Folder Chooser -->
        <div class="scoped-box">
          <h4>
            <span class="icon-amber" id="scopedFolderBoxIcon"></span>
            Target Folder or Document
          </h4>
          <p>Choose any directory or single file on your system to isolate and search exclusively within it.</p>
          <div class="folder-picker-actions">
            <button class="btn-folder-pick" onclick="pickFolderNative()">
              <span class="icon-white" id="scopedPickBtnIcon"></span> Browse Folder...
            </button>
            <button class="btn-file-pick" onclick="pickFileNative()" title="Select single file or image">
              <span class="icon-blue" id="scopedPickFileIcon"></span> Choose File...
            </button>
            <input type="file" id="webkitFolderInput" webkitdirectory directory multiple style="display:none;" onchange="handleWebkitFolderSelect(event)">
            <button class="btn-folder-subtle" onclick="document.getElementById('webkitFolderInput').click()" title="Select directory in browser">
              Browser Chooser
            </button>
          </div>
        </div>

        <!-- Option 2: Upload File / Image -->
        <div class="scoped-box">
          <h4>
            <span class="icon-cyan" id="scopedUploadBoxIcon"></span>
            Drop File or Image
          </h4>
          <p>Drop any spreadsheet (<code>.xlsx</code>, <code>.csv</code>), PDF, or image (<code>.png</code>, <code>.jpg</code>) for instant OCR & scoped lookup.</p>
          <div class="drop-zone" id="scopedDropZone" onclick="document.getElementById('scopedFileInput').click()">
            <input type="file" id="scopedFileInput" style="display:none;" onchange="handleScopedFileUpload(event)" accept=".xlsx,.xls,.csv,.tsv,.docx,.odt,.txt,.pdf,.png,.jpg,.jpeg,.tiff,.bmp,.webp">
            <div style="margin-bottom:4px;">
              <span class="icon-purple icon-lg" id="scopedDropIcon"></span>
            </div>
            <p><b>Click or Drag & Drop</b> document or picture</p>
          </div>
        </div>
      </div>

      <!-- Active Scope Banner -->
      <div id="activeScopeBanner" class="active-scope-banner" style="display:none;">
        <div style="display:flex; align-items:center; gap:10px;">
          <span class="icon-amber icon-lg" id="activeScopeIcon"></span>
          <div>
            <span style="font-size:0.75rem; color:var(--text-muted); display:block;">Active Scope Target:</span>
            <span class="scope-name-tag" id="activeScopeLabel">None</span>
          </div>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          <button class="btn-header" onclick="document.getElementById('scopedQueryInput').focus()">Search Scope</button>
          <button class="btn-clear-scope" onclick="clearScopedTarget()">✕ Clear</button>
        </div>
      </div>

      <!-- Scoped Search Mode Switcher -->
      <div class="search-mode-row" style="margin-bottom:8px;">
        <div class="search-mode-pills">
          <button id="scopedModeBtnGeneral" class="mode-pill active" onclick="setScopedSearchMode('general')" title="Universal full-text document search">
            <span class="icon-cyan" id="scopedModeGeneralIcon"></span> General Search
          </button>
          <button id="scopedModeBtnTelecom" class="mode-pill telecom-mode" onclick="setScopedSearchMode('telecom')" title="Investigative phone & CDR records explorer">
            <span class="icon-emerald" id="scopedModeTelecomIcon"></span> Telecom / CDR Mode
          </button>
        </div>
        <span class="mode-desc-text" id="scopedModeDescText">Target document lookup</span>
      </div>

      <!-- Scoped Search Input -->
      <div class="search-bar-row" style="background:#090e1a; padding:12px; border-radius:8px; border:1px solid var(--border);">
        <span class="search-icon-inside icon-cyan" id="searchScopedHeroIcon" style="left:24px;"></span>
        <input type="text" id="scopedQueryInput" placeholder="Search exclusively inside the locked target above..." oninput="handleScopedInput(event)" onkeydown="if(event.key==='Enter') doScopedSearch(0)" style="padding-left:42px;">
        <button id="clearScopedSearchBtn" class="clear-btn" onclick="clearScopedSearch()" title="Clear">
          <span class="icon-rose" id="clearScopedIcon"></span>
        </button>
        <button class="btn-search" onclick="doScopedSearch(0)">Search Target</button>
      </div>
    </div>

    <!-- Scoped Status & View Toggle -->
    <div class="status-bar">
      <div>
        <span id="scopedResultsCount">Choose a folder or drop a file above to begin.</span>
        <span style="margin-left:6px; opacity:0.6;" id="scopedTiming">0ms</span>
      </div>
      <div class="view-toggle">
        <button id="btnScopedViewCard" class="view-btn active" onclick="switchScopedView('card')">
          <span class="icon-indigo" id="scopedViewCardIcon"></span> Cards
        </button>
        <button id="btnScopedViewTable" class="view-btn" onclick="switchScopedView('table')">
          <span class="icon-slate" id="scopedViewTableIcon"></span> Tabular
        </button>
      </div>
    </div>

    <!-- Scoped Top Pagination Bar -->
    <div id="scopedTopPaginationBar" class="pagination-bar top-bar" style="display:none;">
      <span id="scopedTopPageInfo">Showing 0-0 of 0</span>
      <div class="pagination-btns">
        <button id="scopedTopPrevBtn" class="page-btn" onclick="changeScopedPage(-1)">← Prev</button>
        <span id="scopedTopPageNumberBadge" style="font-weight:600; color:var(--accent);">Page 1</span>
        <button id="scopedTopNextBtn" class="page-btn" onclick="changeScopedPage(1)">Next →</button>
      </div>
    </div>

    <div id="scopedCardsContainer" class="cards-container">
      <div style="text-align:center; padding: 48px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle);">
        No target selected yet. Choose a folder or file above.
      </div>
    </div>

    <div id="scopedTableContainer" class="table-container" style="display:none;">
      <table id="scopedResultsTable">
        <thead>
          <tr id="scopedTableHead">
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
        <tbody id="scopedTableBody">
          <tr>
            <td colspan="9" style="text-align:center; padding: 40px; color:#64748b;">No records loaded.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div id="scopedPaginationBar" class="pagination-bar" style="display:none;">
      <span id="scopedPageInfo">Showing 0-0 of 0</span>
      <div class="pagination-btns">
        <button id="scopedPrevBtn" class="page-btn" onclick="changeScopedPage(-1)">← Prev</button>
        <span id="scopedPageNumberBadge" style="font-weight:600; color:var(--accent);">Page 1</span>
        <button id="scopedNextBtn" class="page-btn" onclick="changeScopedPage(1)">Next →</button>
      </div>
    </div>
  </div>

  <!-- Floating Scroll To Top / Bottom Buttons -->
  <div class="scroll-nav-container">
    <button class="scroll-nav-btn" onclick="scrollToTop()" title="Scroll to top">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width:18px; height:18px;"><polyline points="18 15 12 9 6 15"></polyline></svg>
    </button>
    <button class="scroll-nav-btn" onclick="scrollToBottom()" title="Scroll to bottom">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width:18px; height:18px;"><polyline points="6 9 12 15 18 9"></polyline></svg>
    </button>
  </div>

  <div id="toast" class="toast">Opening file...</div>

<script>
/* SVG Icon Set */
const SVG_RAW = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>',
  pdf: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="9" y1="15" x2="15" y2="15"></line></svg>',
  excel: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="3" y1="15" x2="21" y2="15"></line><line x1="9" y1="3" x2="9" y2="21"></line><line x1="15" y1="3" x2="15" y2="21"></line></svg>',
  doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>',
  image: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>',
  text: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><line x1="17" y1="10" x2="3" y2="10"></line><line x1="21" y1="6" x2="3" y2="6"></line><line x1="21" y1="14" x2="3" y2="14"></line><line x1="17" y1="18" x2="3" y2="18"></line></svg>',
  phone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>',
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>',
  cross: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
  open: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>',
  context: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>',
  target: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>',
  zoomIn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  zoomOut: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
  cardView: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>',
  tableView: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="3" y1="15" x2="21" y2="15"></line><line x1="3" y1="21" x2="21" y2="21"></line><line x1="9" y1="3" x2="9" y2="21"></line></svg>',
  globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
  upload: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>',
  database: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>',
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>',
  sparkles: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>'
};

function injectStaticIcons() {
  const setIcon = (id, svgHtml) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = svgHtml;
  };
  setIcon('appLogoIcon', SVG_RAW.globe);
  setIcon('headerFolderIcon', SVG_RAW.folder);
  setIcon('toolsIcon', SVG_RAW.settings);
  setIcon('menuBookmarkIcon', SVG_RAW.tag);
  setIcon('menuBackupIcon', SVG_RAW.database);
  setIcon('menuExportIcon', SVG_RAW.download);
  setIcon('menuImportIcon', SVG_RAW.upload);
  setIcon('menuCsvIcon', SVG_RAW.excel);

  setIcon('tabGlobalIcon', SVG_RAW.globe);
  setIcon('tabScopedIcon', SVG_RAW.target);

  setIcon('modeGeneralIcon', SVG_RAW.search);
  setIcon('modeTelecomIcon', SVG_RAW.phone);
  setIcon('scopedModeGeneralIcon', SVG_RAW.search);
  setIcon('scopedModeTelecomIcon', SVG_RAW.phone);

  setIcon('searchHeroIcon', SVG_RAW.search);
  setIcon('clearSearchIcon', SVG_RAW.cross);
  setIcon('btnSearchIcon', SVG_RAW.search);

  setIcon('filterAllIcon', SVG_RAW.sparkles);
  setIcon('filterDocIcon', SVG_RAW.pdf);
  setIcon('filterSheetIcon', SVG_RAW.excel);
  setIcon('filterImageIcon', SVG_RAW.image);
  setIcon('filterPhoneIcon', SVG_RAW.phone);

  setIcon('viewCardIcon', SVG_RAW.cardView);
  setIcon('viewTableIcon', SVG_RAW.tableView);

  setIcon('scopedFolderBoxIcon', SVG_RAW.folder);
  setIcon('scopedPickBtnIcon', SVG_RAW.folder);
  setIcon('scopedPickFileIcon', SVG_RAW.doc);
  setIcon('scopedUploadBoxIcon', SVG_RAW.upload);
  setIcon('scopedDropIcon', SVG_RAW.image);
  setIcon('activeScopeIcon', SVG_RAW.folder);
  setIcon('searchScopedHeroIcon', SVG_RAW.search);
  setIcon('clearScopedIcon', SVG_RAW.cross);
  setIcon('scopedViewCardIcon', SVG_RAW.cardView);
  setIcon('scopedViewTableIcon', SVG_RAW.tableView);

  setIcon('folderModalIcon', SVG_RAW.folder);
  setIcon('folderModalBtnIcon', SVG_RAW.folder);
  setIcon('filterModalIcon', SVG_RAW.tag);
  setIcon('bookmarkModalIcon', SVG_RAW.tag);
  setIcon('contextModalIcon', SVG_RAW.context);

  setIcon('imageModalIcon', SVG_RAW.image);
  setIcon('ocrToggleIcon', SVG_RAW.eye);
  setIcon('zoomInIcon', SVG_RAW.zoomIn);
  setIcon('zoomOutIcon', SVG_RAW.zoomOut);
  setIcon('resetZoomIcon', SVG_RAW.refresh);
  setIcon('closeModalIcon', SVG_RAW.cross);
  setIcon('copyAllIcon', SVG_RAW.copy);
}

function toggleToolsDropdown(e) {
  e.stopPropagation();
  document.getElementById('toolsDropdown').classList.toggle('open');
}

document.addEventListener('click', () => {
  const dd = document.getElementById('toolsDropdown');
  if (dd) dd.classList.remove('open');
});

let currentPage = 0;
const pageSize = 50;
let currentQuery = '';
let activeTypeFilter = 'all';
let currentSearchMode = 'general';
let totalResults = 0;
let lastResults = [];
let progressPollInterval = null;
let currentViewMode = 'card';
let debounceTimer = null;

function setSearchMode(mode) {
  currentSearchMode = mode;
  const isGeneral = (mode === 'general');
  document.getElementById('modeBtnGeneral').classList.toggle('active', isGeneral);
  document.getElementById('modeBtnTelecom').classList.toggle('active', !isGeneral);

  const desc = document.getElementById('modeDescText');
  const input = document.getElementById('queryInput');
  if (isGeneral) {
    desc.innerText = '📄 Universal search across documents, PDFs, OCR, sheets & text';
    input.placeholder = 'Search keywords, document text, topics, Egyptian/EN names, OCR images...';
  } else {
    desc.innerText = '📞 CDR caller, callee, tower cell, duration & phone intelligence';
    input.placeholder = 'Search phone numbers (e.g. 010..., 2012...), caller/callee, IMEI/IMSI, cell towers...';
  }

  if (currentQuery) {
    doSearch(0);
  }
}

function showToast(msg, duration = 3000) {
  const toast = document.getElementById('toast');
  toast.innerHTML = msg;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

function copyToClipboard(text, label = 'Copied') {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    showToast(`📋 ${label}: ${escapeHtml(text.slice(0, 35))}${text.length > 35 ? '...' : ''}`);
  }).catch(() => {
    showToast(`📋 Copied to clipboard`);
  });
}

function switchView(mode) {
  currentViewMode = mode;
  document.getElementById('btnViewCard').classList.toggle('active', mode === 'card');
  document.getElementById('btnViewTable').classList.toggle('active', mode === 'table');
  document.getElementById('cardsContainer').style.display = (mode === 'card') ? 'flex' : 'none';
  document.getElementById('tableContainer').style.display = (mode === 'table') ? 'block' : 'none';
  if (lastResults && lastResults.length > 0) {
    renderFilteredResults();
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

function setTypeFilter(type, btnEl) {
  activeTypeFilter = type;
  document.querySelectorAll('.filter-tabs-row .filter-pill').forEach(el => el.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  renderFilteredResults();
}

function renderFilteredResults() {
  if (!lastResults) return;
  let filtered = lastResults;
  if (activeTypeFilter === 'doc') {
    filtered = lastResults.filter(r => {
      const ext = (r.file || '').split('.').pop().toLowerCase();
      return ['pdf', 'docx', 'doc', 'odt', 'txt'].includes(ext);
    });
  } else if (activeTypeFilter === 'sheet') {
    filtered = lastResults.filter(r => {
      const ext = (r.file || '').split('.').pop().toLowerCase();
      return ['xlsx', 'xls', 'csv', 'tsv'].includes(ext);
    });
  } else if (activeTypeFilter === 'image') {
    filtered = lastResults.filter(r => isImageFile(r.file));
  } else if (activeTypeFilter === 'phone') {
    filtered = lastResults.filter(r => (r.target && r.target !== '—') || (r.other && r.other !== '—') || r.phone);
  }

  document.getElementById('resultsCount').innerText = `${filtered.length.toLocaleString()} result(s)`;
  renderCards(filtered);
  renderTableRows(filtered);

  // If user specifically filtered by image and results exist, preview first image
  if (activeTypeFilter === 'image' && filtered.length > 0) {
    const firstImg = filtered[0];
    showImagePreview(firstImg.path, firstImg.sheet, currentQuery);
  }
}

async function refreshStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('statsBadge').innerText = `${(data.files || 0).toLocaleString()} files • ${(data.records || 0).toLocaleString()} entries`;
    if (typeof data.watcher !== 'undefined') {
      updateWatcherUI(data.watcher);
    }
  } catch (e) {
    console.error(e);
  }
}

async function refreshWatcherStatus() {
  try {
    const res = await fetch('/api/watch/status');
    const data = await res.json();
    updateWatcherUI(data.active);
  } catch (e) {
    console.error(e);
  }
}

function updateWatcherUI(isActive) {
  const dot = document.getElementById('watcherDot');
  const label = document.getElementById('watcherLabel');
  if (isActive) {
    dot.className = 'watcher-dot active';
    label.innerText = 'Watcher Active';
    label.style.color = '#10b981';
  } else {
    dot.className = 'watcher-dot paused';
    label.innerText = 'Watcher Paused';
    label.style.color = '#94a3b8';
  }
}

async function toggleWatcher() {
  try {
    const res = await fetch('/api/watch/toggle', { method: 'POST' });
    const data = await res.json();
    updateWatcherUI(data.active);
    showToast(data.message || (data.active ? "Watcher turned ON" : "Watcher turned OFF"));
  } catch (e) {
    showToast("❌ Network error toggling watcher");
  }
}

function openFolderModal() {
  document.getElementById('folderModal').classList.add('active');
}

function closeFolderModal() {
  document.getElementById('folderModal').classList.remove('active');
}

async function pickFolderModalNative() {
  try {
    const res = await fetch('/api/dialog/pick-folder');
    const data = await res.json();
    if (data.ok && data.path) {
      document.getElementById('folderPathInput').value = data.path;
      showToast(`Selected: ${data.path}`);
    }
  } catch (err) {
    showToast("❌ Could not open folder chooser");
  }
}

function handleModalWebkitFolder(e) {
  const files = e.target.files;
  if (files && files.length > 0) {
    const firstFile = files[0];
    const path = firstFile.webkitRelativePath ? firstFile.webkitRelativePath.split('/')[0] : firstFile.name;
    document.getElementById('folderPathInput').value = path;
    showToast(`Selected: ${path}`);
  }
}

async function submitFolderIndex() {
  const folder = document.getElementById('folderPathInput').value.trim();
  if (!folder) {
    alert("Please choose or enter a folder path!");
    return;
  }
  closeFolderModal();
  showToast(`⚡ Starting indexing for ${folder}...`);
  try {
    const res = await fetch(`/api/index/start?folder=${encodeURIComponent(folder)}`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast("Indexing launched! Watching progress...");
      pollProgress();
    } else {
      alert(data.error || "Failed to start indexing.");
    }
  } catch (e) {
    showToast("❌ Network error starting indexing");
  }
}

function pollProgress() {
  if (progressPollInterval) clearInterval(progressPollInterval);
  const banner = document.getElementById('progressBanner');
  banner.style.display = 'block';

  progressPollInterval = setInterval(async () => {
    try {
      const res = await fetch('/api/progress');
      const data = await res.json();
      
      const pct = Math.round(data.percent || 0);
      document.getElementById('progressBarFill').style.width = pct + '%';
      document.getElementById('progressPercent').innerText = pct + '%';
      document.getElementById('progressStatus').innerText = data.status || 'Indexing...';
      document.getElementById('progressCurrentFile').innerText = data.current_file || '';
      document.getElementById('progressRecords').innerText = `${(data.records_indexed || 0).toLocaleString()} records indexed`;

      if (!data.in_progress && pct >= 100) {
        clearInterval(progressPollInterval);
        setTimeout(() => {
          banner.style.display = 'none';
          refreshStats();
          showToast("✅ Indexing completed!");
        }, 1800);
      }
    } catch (e) {
      console.error(e);
    }
  }, 1000);
}

function openFilterModal() {
  document.getElementById('filterNameInput').value = '';
  document.getElementById('filterQueryInput').value = '';
  document.getElementById('filterModal').classList.add('active');
}

function closeFilterModal() {
  document.getElementById('filterModal').classList.remove('active');
}

async function submitFilter() {
  const name = document.getElementById('filterNameInput').value.trim();
  const query = document.getElementById('filterQueryInput').value.trim();
  if (!name || !query) {
    alert("Please fill in both name and query!");
    return;
  }
  closeFilterModal();
  try {
    const res = await fetch('/api/filters/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, query })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ Added filter "${name}"`);
      loadQuickFilters();
    } else {
      alert("Failed to save filter.");
    }
  } catch (e) {
    showToast("❌ Network error saving filter");
  }
}

async function loadQuickFilters() {
  try {
    const res = await fetch('/api/filters');
    const data = await res.json();
    const list = document.getElementById('quickChipsList');
    list.innerHTML = '';
    data.filters.forEach(f => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.innerHTML = `${SVG_RAW.tag} ${escapeHtml(f.name)}`;
      chip.title = `Query: ${f.query} (Right click to delete)`;
      chip.onclick = () => {
        document.getElementById('queryInput').value = f.query;
        document.getElementById('clearSearchBtn').style.display = 'block';
        doSearch(0);
      };
      chip.oncontextmenu = async (e) => {
        e.preventDefault();
        if (confirm(`Delete filter "${f.name}"?`)) {
          await deleteQuickFilter(f.id);
        }
      };
      list.appendChild(chip);
    });
  } catch (e) {
    console.error(e);
  }
}

async function deleteQuickFilter(id) {
  try {
    const res = await fetch('/api/filters/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    const data = await res.json();
    if (data.ok) {
      showToast("Filter removed");
      loadQuickFilters();
    }
  } catch (e) {
    showToast("❌ Network error removing filter");
  }
}

function openBookmarkModal(file, sheet, row, targetPhone) {
  document.getElementById('bmFilePath').value = file;
  document.getElementById('bmSheetName').value = sheet;
  document.getElementById('bmRowIdx').value = row;
  document.getElementById('bmNotesInput').value = '';
  document.getElementById('bookmarkTargetLabel').innerText = `${file.split('/').pop()} • ${sheet} • Row ${row} ${targetPhone ? '(' + targetPhone + ')' : ''}`;
  document.getElementById('bookmarkModal').classList.add('active');
}

function closeBookmarkModal() {
  document.getElementById('bookmarkModal').classList.remove('active');
}

async function submitBookmark() {
  const file = document.getElementById('bmFilePath').value;
  const sheet = document.getElementById('bmSheetName').value;
  const row = parseInt(document.getElementById('bmRowIdx').value, 10);
  const tag = document.getElementById('bmTagInput').value;
  const notes = document.getElementById('bmNotesInput').value.trim();

  closeBookmarkModal();
  try {
    const res = await fetch('/api/bookmarks/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file, sheet, row, tag, notes })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`🔖 Bookmarked as [${tag}]`);
      refreshBookmarkCount();
    } else {
      alert("Failed to bookmark record.");
    }
  } catch (e) {
    showToast("❌ Network error bookmarking record");
  }
}

async function refreshBookmarkCount() {
  try {
    const res = await fetch('/api/bookmarks');
    const data = await res.json();
    document.getElementById('bmCountBadge').innerText = data.bookmarks.length;
  } catch (e) {}
}

async function viewBookmarks() {
  try {
    const res = await fetch('/api/bookmarks');
    const data = await res.json();
    if (data.bookmarks.length === 0) {
      showToast("No bookmarks saved yet");
      return;
    }
    const fakeRows = data.bookmarks.map(b => ({
      file: b.file_path.split('/').pop(),
      path: b.file_path,
      sheet: b.sheet_name,
      row: b.row_idx,
      target: b.tag,
      other: b.notes || '—',
      name: '—',
      time: b.created_at || '—',
      dir: '—',
      snippet: `[${b.tag}] ${b.notes || 'No annotation'}`
    }));
    totalResults = fakeRows.length;
    lastResults = fakeRows;
    renderCards(fakeRows);
    document.getElementById('resultsCount').innerText = `${fakeRows.length} Bookmarks loaded`;
  } catch (e) {
    showToast("❌ Network error fetching bookmarks");
  }
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
    const res = await fetch(`/api/search?q=${encodeURIComponent(currentQuery)}&limit=${pageSize}&offset=${offset}&mode=${encodeURIComponent(currentSearchMode)}`);
    const data = await res.json();
    const t1 = performance.now();
    document.getElementById('timing').innerText = `${Math.round(t1 - t0)}ms`;

    renderViewData(data);
  } catch (e) {
    console.error(e);
    document.getElementById('resultsCount').innerText = "Search error";
  }
}

function changePage(delta) {
  const newPage = currentPage + delta;
  if (newPage >= 0 && (newPage * pageSize) < totalResults) {
    doSearch(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function scrollToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
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

function highlightMatch(text, query) {
  if (!text) return '';
  const escaped = escapeHtml(text);
  if (!query) return escaped;

  const cleanQuery = query.trim().replace(/"/g, '');
  if (!cleanQuery) return escaped;

  const terms = cleanQuery.split(/\s+/).filter(t => t.length > 0);
  if (terms.length === 0) return escaped;

  const pattern = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  const regex = new RegExp(`(${pattern})`, 'gi');
  return escaped.replace(regex, '<mark class="match-hl">$1</mark>');
}

function getFileExtBadge(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  if (ext === 'pdf') {
    return `<span class="file-type-pill pill-pdf">${SVG_RAW.pdf} PDF</span>`;
  } else if (['xlsx', 'xls', 'csv', 'tsv'].includes(ext)) {
    return `<span class="file-type-pill pill-xlsx">${SVG_RAW.excel} ${ext.toUpperCase()}</span>`;
  } else if (['docx', 'doc', 'odt'].includes(ext)) {
    return `<span class="file-type-pill pill-docx">${SVG_RAW.doc} ${ext.toUpperCase()}</span>`;
  } else if (['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'].includes(ext)) {
    return `<span class="file-type-pill pill-image">${SVG_RAW.image} ${ext.toUpperCase()}</span>`;
  } else {
    return `<span class="file-type-pill pill-txt">${SVG_RAW.text} ${ext.toUpperCase() || 'FILE'}</span>`;
  }
}

function renderViewData(data) {
  lastResults = data.rows || [];
  totalResults = data.total || 0;
  const paginationBar = document.getElementById('paginationBar');
  const topPaginationBar = document.getElementById('topPaginationBar');

  if (totalResults > pageSize) {
    const start = currentPage * pageSize + 1;
    const end = Math.min((currentPage + 1) * pageSize, totalResults);
    const infoText = `Showing ${start.toLocaleString()}-${end.toLocaleString()} of ${totalResults.toLocaleString()} records`;
    const pageBadgeText = `Page ${currentPage + 1} of ${Math.ceil(totalResults / pageSize)}`;
    const isPrevDisabled = (currentPage === 0);
    const isNextDisabled = ((currentPage + 1) * pageSize >= totalResults);

    paginationBar.style.display = 'flex';
    document.getElementById('pageInfo').innerText = infoText;
    document.getElementById('pageNumberBadge').innerText = pageBadgeText;
    document.getElementById('prevBtn').disabled = isPrevDisabled;
    document.getElementById('nextBtn').disabled = isNextDisabled;

    if (topPaginationBar) {
      topPaginationBar.style.display = 'flex';
      document.getElementById('topPageInfo').innerText = infoText;
      document.getElementById('topPageNumberBadge').innerText = pageBadgeText;
      document.getElementById('topPrevBtn').disabled = isPrevDisabled;
      document.getElementById('topNextBtn').disabled = isNextDisabled;
    }
  } else if (totalResults > 0) {
    paginationBar.style.display = 'flex';
    document.getElementById('pageInfo').innerText = `${totalResults.toLocaleString()} records`;
    document.getElementById('pageNumberBadge').innerText = `Page 1 of 1`;
    document.getElementById('prevBtn').disabled = true;
    document.getElementById('nextBtn').disabled = true;

    if (topPaginationBar) {
      topPaginationBar.style.display = 'flex';
      document.getElementById('topPageInfo').innerText = `${totalResults.toLocaleString()} records`;
      document.getElementById('topPageNumberBadge').innerText = `Page 1 of 1`;
      document.getElementById('topPrevBtn').disabled = true;
      document.getElementById('topNextBtn').disabled = true;
    }
  } else {
    paginationBar.style.display = 'none';
    if (topPaginationBar) topPaginationBar.style.display = 'none';
  }

  renderFilteredResults();
}

function formatFileSize(bytes) {
  if (!bytes || bytes <= 0) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function renderCards(rows) {
  const container = document.getElementById('cardsContainer');
  container.innerHTML = '';

  if (!rows || rows.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 48px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle);">
        No matching records found for "${escapeHtml(currentQuery)}".
      </div>
    `;
    return;
  }

  const isGeneral = (currentSearchMode === 'general');

  rows.forEach(r => {
    const card = document.createElement('div');
    card.className = 'result-card';
    const escapedPath = (r.path || '').replace(/'/g, "\\'");
    const escapedSheet = (r.sheet || '').replace(/'/g, "\\'");
    const isImage = isImageFile(r.file);

    let metaRowHtml = '';
    if (isGeneral) {
      const folderDisplay = r.folder ? escapeHtml(r.folder) : '';
      const sizeDisplay = r.size ? formatFileSize(r.size) : '';
      metaRowHtml = `
        <div class="general-card-meta">
          ${folderDisplay ? `<span class="meta-tag" title="${folderDisplay}">${SVG_RAW.folder} ${folderDisplay.length > 55 ? '...' + folderDisplay.slice(-52) : folderDisplay}</span>` : ''}
          ${r.sheet ? `<span class="meta-tag">${SVG_RAW.context} ${escapeHtml(r.sheet)} (Row ${r.row})</span>` : ''}
          ${sizeDisplay ? `<span class="meta-tag">💾 ${sizeDisplay}</span>` : ''}
          ${r.indexed_at && r.indexed_at !== '—' ? `<span class="meta-tag">📅 ${escapeHtml(r.indexed_at)}</span>` : ''}
        </div>
      `;
    } else {
      let pillsHtml = '';
      if (r.target && r.target !== '—') {
        pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.target}', 'Target Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.target, currentQuery)}</b></span>`;
      }
      if (r.other && r.other !== '—') {
        pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.other}', 'Party Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.other, currentQuery)}</b></span>`;
      }
      if (r.name && r.name !== '—') {
        pillsHtml += `<span class="info-pill arabic" onclick="copyToClipboard('${r.name}', 'Name')">👤 <b>${highlightMatch(r.name, currentQuery)}</b></span>`;
      }
      if (r.time && r.time !== '—') {
        pillsHtml += `<span class="info-pill">📅 ${escapeHtml(r.time)}</span>`;
      }
      if (r.dir && r.dir !== '—') {
        pillsHtml += `<span class="info-pill">🔄 ${escapeHtml(r.dir)}</span>`;
      }
      if (r.address && r.address !== '—') {
        pillsHtml += `<span class="info-pill arabic">📍 ${highlightMatch(r.address, currentQuery)}</span>`;
      }
      if (pillsHtml) {
        metaRowHtml = `<div class="card-pill-group">${pillsHtml}</div>`;
      }
    }

    card.innerHTML = `
      <div class="card-header">
        <div class="file-meta">
          ${getFileExtBadge(r.file)}
          <span title="${escapeHtml(r.path || '')}">${escapeHtml(r.file)}</span>
        </div>
        <div class="card-actions">
          ${isImage ? `<button class="btn-image-preview" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(currentQuery || '')}')" title="Inspect Image & OCR Highlights">${SVG_RAW.eye} Preview & Text</button>` : ''}
          <button class="btn-action" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})" title="View ±3 lines context">
            ${SVG_RAW.context} Context
          </button>
          <button class="btn-action" onclick="openBookmarkModal('${escapedPath}', '${escapedSheet}', ${r.row}, '${escapeHtml(r.name || r.other || r.target || '')}')" title="Tag record">
            ${SVG_RAW.tag} Tag
          </button>
          <button class="btn-action" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})">
            ${SVG_RAW.open} Open
          </button>
          <button class="btn-action" onclick="revealFolder('${escapedPath}')" title="Open containing folder">
            ${SVG_RAW.folder} Folder
          </button>
        </div>
      </div>
      ${metaRowHtml}
      <div class="snippet-box" ${isImage ? `style="cursor:pointer;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(currentQuery || '')}')"` : ''}>
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

  const isGeneral = (currentSearchMode === 'general');

  if (isGeneral) {
    thead.innerHTML = `
      <th>File</th>
      <th>Folder / Section</th>
      <th>Snippet / Matched Content</th>
      <th>Indexed</th>
      <th>Actions</th>
    `;
  } else {
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
  }

  if (!rows || rows.length === 0) {
    const colspan = isGeneral ? 5 : 9;
    tbody.innerHTML = `<tr><td colspan="${colspan}" style="text-align:center; padding: 40px; color:#64748b;">No records match your query.</td></tr>`;
    return;
  }

  rows.forEach(r => {
    const tr = document.createElement('tr');
    const escapedPath = (r.path || '').replace(/'/g, "\\'");
    const escapedSheet = (r.sheet || '').replace(/'/g, "\\'");
    const isImage = isImageFile(r.file);

    if (isGeneral) {
      const folderName = r.folder ? r.folder.split('/').slice(-2).join('/') : '';
      tr.innerHTML = `
        <td title="${escapeHtml(r.path)}">
          ${getFileExtBadge(r.file)}
          <span style="margin-left:5px; font-weight:600;">${escapeHtml(r.file)}</span>
        </td>
        <td style="color:#94a3b8; font-size:0.8rem;" title="${escapeHtml(r.folder || '')}">
          <div>📁 ${escapeHtml(folderName || 'Root')}</div>
          ${r.sheet ? `<div style="color:var(--text-dim); font-size:0.75rem;">${escapeHtml(r.sheet)} (Row ${r.row})</div>` : ''}
        </td>
        <td style="max-width: 520px; font-family:'JetBrains Mono', monospace; font-size:0.8rem; line-height:1.45;">
          ${highlightMatch(r.snippet, currentQuery)}
        </td>
        <td style="white-space:nowrap; color:#94a3b8; font-size:0.78rem;">
          ${escapeHtml(r.indexed_at || r.time || '—')}
        </td>
        <td>
          <div style="display:flex; gap:4px;">
            ${isImage ? `<button class="btn-action" style="padding:2px 6px; color:#a855f7;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(currentQuery || '')}')" title="Preview Image">${SVG_RAW.eye}</button>` : ''}
            <button class="btn-action" style="padding:2px 6px;" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})" title="Open File">${SVG_RAW.open}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})" title="Context">${SVG_RAW.context}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="revealFolder('${escapedPath}')" title="Folder">${SVG_RAW.folder}</button>
          </div>
        </td>
      `;
    } else {
      tr.innerHTML = `
        <td title="${escapeHtml(r.path)}">${getFileExtBadge(r.file)} <span style="margin-left:4px;">${escapeHtml(r.file)}</span></td>
        <td>${escapeHtml(r.time)}</td>
        <td>${escapeHtml(r.dir)}</td>
        <td style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.target}', 'Target Phone')">${highlightMatch(r.target, currentQuery)}</td>
        <td style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.other}', 'Party Phone')">${highlightMatch(r.other, currentQuery)}</td>
        <td class="arabic" style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.name}', 'Name')">${highlightMatch(r.name, currentQuery)}</td>
        <td>${escapeHtml(r.duration)}</td>
        <td class="arabic">${highlightMatch(r.address || r.sheet, currentQuery)}</td>
        <td>
          <div style="display:flex; gap:4px;">
            ${isImage ? `<button class="btn-action" style="padding:2px 6px; color:#a855f7;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(currentQuery || '')}')" title="Preview Image">${SVG_RAW.eye}</button>` : ''}
            <button class="btn-action" style="padding:2px 6px;" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})" title="Open">${SVG_RAW.open}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})" title="Context">${SVG_RAW.context}</button>
          </div>
        </td>
      `;
    }
    tbody.appendChild(tr);
  });
}

async function openFile(filePath, sheetName, rowIdx) {
  showToast(`🚀 Opening ${filePath.split('/').pop()} at row ${rowIdx}...`);
  try {
    const res = await fetch(`/api/open?file=${encodeURIComponent(filePath)}&sheet=${encodeURIComponent(sheetName)}&row=${rowIdx}`);
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message}`);
    } else {
      showToast(`❌ Error: ${data.error}`);
    }
  } catch (err) {
    showToast(`❌ Network error launching app`);
  }
}

async function revealFolder(filePath) {
  showToast(`📂 Opening folder...`);
  try {
    const res = await fetch(`/api/reveal?file=${encodeURIComponent(filePath)}`);
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message}`);
    } else {
      showToast(`❌ Error: ${data.error}`);
    }
  } catch (err) {
    showToast(`❌ Network error opening folder`);
  }
}

async function showContextWindow(filePath, sheetName, rowIdx) {
  const modal = document.getElementById('contextModal');
  const label = document.getElementById('contextFileLabel');
  const box = document.getElementById('contextLinesBox');
  label.innerText = `${filePath} (${sheetName}, around Row ${rowIdx})`;
  box.innerHTML = 'Loading ±3 lines context...';
  modal.classList.add('active');

  try {
    const res = await fetch(`/api/context?file=${encodeURIComponent(filePath)}&sheet=${encodeURIComponent(sheetName)}&row=${rowIdx}`);
    const data = await res.json();
    if (data.ok && data.lines && data.lines.length > 0) {
      let html = '';
      data.lines.forEach(l => {
        const isTarget = (l.row === rowIdx);
        html += `<div style="padding: 4px 8px; border-radius: 4px; ${isTarget ? 'background: rgba(56, 189, 248, 0.2); font-weight: bold; border-left: 3px solid var(--accent);' : ''}">
          <span style="color:#64748b; margin-right: 8px;">[Row ${l.row}]</span>
          ${highlightMatch(l.content, currentQuery)}
        </div>`;
      });
      box.innerHTML = html;
    } else {
      box.innerHTML = '<span style="color:#64748b;">No surrounding context available.</span>';
    }
  } catch (err) {
    box.innerHTML = '<span style="color:#ef4444;">Error loading context.</span>';
  }
}

/* Image & Selectable OCR Text Inspector */
let currentImageBoxes = [];
let currentImageLines = [];
let originalImgWidth = 0;
let originalImgHeight = 0;
let currentImageScale = 1.0;
let showBoxesEnabled = true;

function isImageFile(filename) {
  if (!filename) return false;
  const ext = filename.split('.').pop().toLowerCase();
  return ['png', 'jpg', 'jpeg', 'tiff', 'bmp', 'webp'].includes(ext);
}

async function showImagePreview(filePath, sheetName, searchTerm) {
  const modal = document.getElementById('imagePreviewModal');
  const img = document.getElementById('imagePreviewElement');
  const overlay = document.getElementById('ocrBoxesOverlay');
  const label = document.getElementById('imagePreviewFileLabel');
  const notice = document.getElementById('imageOcrNotice');
  const details = document.getElementById('ocrStatusDetails');
  const textContainer = document.getElementById('ocrTextContainer');

  currentImageScale = 1.0;
  const container = document.getElementById('ocrPreviewContainer');
  if (container) container.style.transform = 'scale(1)';
  overlay.innerHTML = '';
  currentImageBoxes = [];
  currentImageLines = [];
  originalImgWidth = 0;
  originalImgHeight = 0;

  label.innerText = `${filePath} (${sheetName || 'Image'})`;
  notice.style.display = 'none';
  details.innerText = 'Analyzing image & loading OCR text layer...';
  textContainer.innerHTML = '<div style="color:#64748b; padding:24px; text-align:center;">Detecting text & coordinates...</div>';
  modal.classList.add('active');

  const encodedFile = encodeURIComponent(filePath);
  const encodedSheet = encodeURIComponent(sheetName || 'Image');

  const updateBoxesAndText = () => {
    if (!originalImgWidth || !originalImgHeight) {
      originalImgWidth = img.naturalWidth || 800;
      originalImgHeight = img.naturalHeight || 600;
    }
    renderOcrBoxes(searchTerm || currentQuery);
    renderOcrTextInspector(searchTerm || currentQuery);
    details.innerText = `${originalImgWidth} × ${originalImgHeight} px | ${currentImageBoxes.length} detected words`;
  };

  // Set img load handler FIRST before src
  img.onload = () => {
    updateBoxesAndText();
  };

  img.onerror = () => {
    details.innerText = '❌ Failed to load image file.';
    textContainer.innerHTML = '<div style="color:#ef4444; padding:20px;">Failed to load image file.</div>';
  };

  img.src = `/api/image/view?file=${encodedFile}`;

  // Fetch bounding boxes & lines
  try {
    const res = await fetch(`/api/image/boxes?file=${encodedFile}&sheet=${encodedSheet}`);
    const resData = await res.json();
    if (resData.ok && resData.data) {
      originalImgWidth = resData.data.width || img.naturalWidth || 0;
      originalImgHeight = resData.data.height || img.naturalHeight || 0;
      currentImageBoxes = resData.data.boxes || [];
      currentImageLines = resData.data.lines || [];
      updateBoxesAndText();
    }
  } catch (err) {
    console.error("Failed to fetch OCR boxes:", err);
  }

  if (img.complete && img.naturalWidth > 0) {
    updateBoxesAndText();
  }
}

function renderOcrTextInspector(searchTerm) {
  const container = document.getElementById('ocrTextContainer');
  const wordsBadge = document.getElementById('ocrWordsCountBadge');
  const cleanTerm = (searchTerm || '').trim().toLowerCase();

  let textLines = currentImageLines || [];
  if ((!textLines || textLines.length === 0) && currentImageBoxes && currentImageBoxes.length > 0) {
    textLines = [currentImageBoxes.map(b => b.text).join(' ')];
  }

  if (!textLines || textLines.length === 0) {
    container.innerHTML = '<div style="color:#64748b; padding:20px; text-align:center;">No OCR text detected in this image.</div>';
    if (wordsBadge) wordsBadge.innerText = '0 words';
    return;
  }

  const fullRawText = textLines.join('\n');
  const totalWords = fullRawText.split(/\s+/).filter(Boolean).length;
  if (wordsBadge) wordsBadge.innerText = `${totalWords} words`;

  let html = '';
  textLines.forEach((line, idx) => {
    const escaped = escapeHtml(line);
    let highlighted = escaped;
    if (cleanTerm) {
      const regex = new RegExp(`(${cleanTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      highlighted = escaped.replace(regex, '<mark class="ocr-mark">$1</mark>');
    }
    html += `<div class="ocr-line" onclick="copyToClipboard('${line.replace(/'/g, "\\'")}', 'Line ${idx + 1}')"><span class="ocr-line-num">${idx + 1}</span><span class="ocr-line-content">${highlighted}</span></div>`;
  });

  container.innerHTML = html;
}

function copyAllOcrText() {
  let text = '';
  if (currentImageLines && currentImageLines.length > 0) {
    text = currentImageLines.join('\n');
  } else if (currentImageBoxes && currentImageBoxes.length > 0) {
    text = currentImageBoxes.map(b => b.text).join(' ');
  }
  if (!text) {
    showToast("No text to copy");
    return;
  }
  copyToClipboard(text, 'Full OCR Text');
}

function copySelectedOcrText() {
  const selection = window.getSelection().toString();
  if (selection && selection.trim()) {
    copyToClipboard(selection.trim(), 'Selected Text');
  } else {
    showToast("Highlight text with mouse first to copy selection");
  }
}

function renderOcrBoxes(searchTerm) {
  const overlay = document.getElementById('ocrBoxesOverlay');
  overlay.innerHTML = '';
  if (!showBoxesEnabled || !currentImageBoxes || currentImageBoxes.length === 0) {
    return;
  }

  const imgW = originalImgWidth || document.getElementById('imagePreviewElement').naturalWidth || 800;
  const imgH = originalImgHeight || document.getElementById('imagePreviewElement').naturalHeight || 600;

  const cleanTerm = (searchTerm || '').trim().toLowerCase();
  let matchCount = 0;
  let firstMatchEl = null;

  currentImageBoxes.forEach(b => {
    const word = (b.text || '').trim();
    if (!word) return;

    const leftPct = (b.left / imgW) * 100;
    const topPct = (b.top / imgH) * 100;
    const widthPct = (b.width / imgW) * 100;
    const heightPct = (b.height / imgH) * 100;

    const isMatch = cleanTerm && (
      word.toLowerCase().includes(cleanTerm) ||
      cleanTerm.includes(word.toLowerCase())
    );
    if (isMatch) matchCount++;

    const boxEl = document.createElement('div');
    boxEl.className = 'ocr-highlight-box' + (isMatch ? ' active-match' : '');
    boxEl.style.left = `${leftPct}%`;
    boxEl.style.top = `${topPct}%`;
    boxEl.style.width = `${widthPct}%`;
    boxEl.style.height = `${heightPct}%`;
    boxEl.title = `"${word}" (${Math.round(b.conf || 0)}% conf)\nClick to copy`;

    // Transparent live text layer for mouse dragging selection directly over the image!
    const textSpan = document.createElement('span');
    textSpan.className = 'ocr-live-text';
    textSpan.innerText = word;
    boxEl.appendChild(textSpan);

    boxEl.onclick = (e) => {
      e.stopPropagation();
      copyToClipboard(word, 'OCR Word');
    };

    overlay.appendChild(boxEl);

    if (isMatch && !firstMatchEl) {
      firstMatchEl = boxEl;
    }
  });

  const notice = document.getElementById('imageOcrNotice');
  if (cleanTerm) {
    notice.style.display = 'block';
    if (matchCount > 0) {
      notice.innerHTML = `🎯 Highlighted <b>${matchCount}</b> match(es) for "<b>${escapeHtml(cleanTerm)}</b>" on image & text inspector. Drag mouse across words to select & copy.`;
      if (firstMatchEl) {
        setTimeout(() => {
          firstMatchEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 150);
      }
    } else {
      notice.innerHTML = `ℹ️ Showing all ${currentImageBoxes.length} detected words on image.`;
    }
  } else {
    notice.style.display = 'none';
  }
}

function toggleOcrBoxes() {
  showBoxesEnabled = !showBoxesEnabled;
  const btn = document.getElementById('ocrToggleBtn');
  btn.innerHTML = `<span class="icon-cyan">${SVG_RAW.eye}</span> Boxes: ${showBoxesEnabled ? 'ON' : 'OFF'}`;
  const overlay = document.getElementById('ocrBoxesOverlay');
  overlay.style.display = showBoxesEnabled ? 'block' : 'none';
}

function zoomImage(delta) {
  currentImageScale = Math.max(0.4, Math.min(3.0, currentImageScale + delta));
  const container = document.getElementById('ocrPreviewContainer');
  container.style.transform = `scale(${currentImageScale})`;
  container.style.transformOrigin = 'top center';
}

function resetImageZoom() {
  currentImageScale = 1.0;
  const container = document.getElementById('ocrPreviewContainer');
  container.style.transform = 'scale(1)';
}

function closeImagePreview() {
  document.getElementById('imagePreviewModal').classList.remove('active');
  document.getElementById('imagePreviewElement').src = '';
  document.getElementById('ocrBoxesOverlay').innerHTML = '';
}

async function triggerBackup() {
  showToast("💾 Creating snapshot backup...");
  try {
    const res = await fetch('/api/backup');
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message}`);
    } else {
      showToast(`❌ Backup failed`);
    }
  } catch (err) {
    showToast(`❌ Network error creating backup`);
  }
}

/* Tab Switcher */
let currentMainTab = 'global';

function switchMainTab(tab) {
  currentMainTab = tab;
  document.getElementById('tabBtnGlobal').classList.toggle('active', tab === 'global');
  document.getElementById('tabBtnScoped').classList.toggle('active', tab === 'scoped');
  document.getElementById('tabGlobalPane').style.display = (tab === 'global') ? 'block' : 'none';
  document.getElementById('tabScopedPane').style.display = (tab === 'scoped') ? 'block' : 'none';

  if (tab === 'global') {
    document.getElementById('queryInput').focus();
  } else {
    document.getElementById('scopedQueryInput').focus();
  }
}

/* Scoped Target / Restricted Search Logic with Native Folder Picker */
let scopedState = {
  active: false,
  type: null,
  path: null,
  filename: null,
  mode: 'general',
  currentPage: 0,
  pageSize: 50,
  currentQuery: '',
  totalResults: 0,
  lastResults: [],
  viewMode: 'card',
  debounceTimer: null
};

function setScopedSearchMode(mode) {
  scopedState.mode = mode;
  const isGeneral = (mode === 'general');
  document.getElementById('scopedModeBtnGeneral').classList.toggle('active', isGeneral);
  document.getElementById('scopedModeBtnTelecom').classList.toggle('active', !isGeneral);

  const desc = document.getElementById('scopedModeDescText');
  const input = document.getElementById('scopedQueryInput');
  if (isGeneral) {
    desc.innerText = 'Target document lookup';
    input.placeholder = 'Search keywords, document text, topics, Egyptian/EN names, OCR images...';
  } else {
    desc.innerText = 'Target CDR & phone records';
    input.placeholder = 'Search phone numbers, caller/callee, duration, cell towers...';
  }

  if (scopedState.active && scopedState.currentQuery) {
    doScopedSearch(0);
  }
}

function switchScopedView(mode) {
  scopedState.viewMode = mode;
  document.getElementById('btnScopedViewCard').classList.toggle('active', mode === 'card');
  document.getElementById('btnScopedViewTable').classList.toggle('active', mode === 'table');
  document.getElementById('scopedCardsContainer').style.display = (mode === 'card') ? 'flex' : 'none';
  document.getElementById('scopedTableContainer').style.display = (mode === 'table') ? 'block' : 'none';
  if (scopedState.lastResults && scopedState.lastResults.length > 0) {
    renderScopedViewData({ rows: scopedState.lastResults, total: scopedState.totalResults, type: scopedState.lastResults[0]?.phone ? 'prefix' : 'cdr' });
  }
}

function handleScopedInput(e) {
  const val = e.target.value.trim();
  document.getElementById('clearScopedSearchBtn').style.display = val ? 'block' : 'none';
  if (scopedState.debounceTimer) clearTimeout(scopedState.debounceTimer);
  scopedState.debounceTimer = setTimeout(() => {
    if (val.length >= 2 || val.length === 0) {
      doScopedSearch(0);
    }
  }, 350);
}

function clearScopedSearch() {
  document.getElementById('scopedQueryInput').value = '';
  document.getElementById('clearScopedSearchBtn').style.display = 'none';
  document.getElementById('scopedQueryInput').focus();
  doScopedSearch(0);
}

function setScopedTarget(type, path, label) {
  scopedState.active = true;
  scopedState.type = type;
  scopedState.path = path;
  scopedState.filename = label || path.split('/').pop();

  const banner = document.getElementById('activeScopeBanner');
  banner.style.display = 'flex';
  document.getElementById('activeScopeLabel').innerText = `${type.toUpperCase()}: ${path}`;
  document.getElementById('scopedTargetBadge').innerText = scopedState.filename;
  document.getElementById('scopedTargetBadge').style.background = '#10b98130';
  document.getElementById('scopedTargetBadge').style.color = '#10b981';

  document.getElementById('scopedQueryInput').focus();
  if (document.getElementById('scopedQueryInput').value.trim()) {
    doScopedSearch(0);
  } else {
    document.getElementById('scopedResultsCount').innerText = `Target locked: ${scopedState.filename}. Ready.`;
  }
}

function clearScopedTarget() {
  scopedState.active = false;
  scopedState.type = null;
  scopedState.path = null;
  scopedState.filename = null;
  scopedState.lastResults = [];
  scopedState.totalResults = 0;

  document.getElementById('activeScopeBanner').style.display = 'none';
  document.getElementById('scopedTargetBadge').innerText = 'Folder or File';
  document.getElementById('scopedTargetBadge').style.background = '#0ea5e920';
  document.getElementById('scopedTargetBadge').style.color = '#38bdf8';
  document.getElementById('scopedFileInput').value = '';
  document.getElementById('scopedResultsCount').innerText = 'Choose a folder or drop a file above to begin.';
  document.getElementById('scopedTiming').innerText = '0ms';
  renderScopedCards([]);
  renderScopedTableRows([]);
}

async function pickFolderNative() {
  showToast("📁 Opening folder selector...");
  try {
    const res = await fetch('/api/dialog/pick-folder');
    const data = await res.json();
    if (data.ok && data.path) {
      await executeTargetIndex(data.path);
    }
  } catch (err) {
    showToast("❌ Could not open native folder chooser");
  }
}

async function pickFileNative() {
  showToast("📄 Opening file selector...");
  try {
    const res = await fetch('/api/dialog/pick-file');
    const data = await res.json();
    if (data.ok && data.path) {
      await executeTargetIndex(data.path);
    }
  } catch (err) {
    showToast("❌ Could not open native file chooser");
  }
}

function handleWebkitFolderSelect(e) {
  const files = e.target.files;
  if (files && files.length > 0) {
    const firstFile = files[0];
    const path = firstFile.webkitRelativePath ? firstFile.webkitRelativePath.split('/')[0] : firstFile.name;
    showToast(`Selected folder: ${path}`);
    setScopedTarget('folder', path, path);
  }
}

async function executeTargetIndex(targetPath) {
  showToast(`⚡ Indexing target: ${targetPath.split('/').pop()}...`);
  try {
    const res = await fetch('/api/target/index', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: targetPath })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message}`);
      setScopedTarget(data.is_dir ? 'folder' : 'file', data.target, targetPath.split('/').pop());
      refreshStats();
      if (isImageFile(data.target)) {
        showImagePreview(data.target, 'Image', '');
      }
    } else {
      alert(`❌ Error: ${data.error}`);
    }
  } catch (err) {
    showToast("❌ Network error indexing target");
  }
}

async function handleScopedFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  await uploadScopedFile(file);
}

async function uploadScopedFile(file) {
  showToast(`📤 Uploading and parsing ${file.name}...`);
  const formData = new FormData();
  formData.append('file', file, file.name);

  try {
    const res = await fetch('/api/target/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ Successfully uploaded and indexed ${data.filename}!`);
      setScopedTarget('file', data.path, data.filename);
      refreshStats();
      if (isImageFile(data.filename)) {
        showImagePreview(data.path, 'Image', '');
      }
    } else {
      alert(`❌ Upload failed: ${data.error}`);
    }
  } catch (err) {
    showToast("❌ Network error uploading file");
  }
}

function initDragAndDrop() {
  const dropZone = document.getElementById('scopedDropZone');
  if (!dropZone) return;

  ['dragenter', 'dragover'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('dragover');
    }, false);
  });

  dropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      uploadScopedFile(files[0]);
    }
  }, false);
}

async function doScopedSearch(page = 0) {
  if (!scopedState.active || !scopedState.path) {
    alert("Please choose a target folder or drop a file first!");
    return;
  }
  const q = document.getElementById('scopedQueryInput').value.trim();
  if (!q) {
    scopedState.lastResults = [];
    scopedState.totalResults = 0;
    renderScopedViewData({ rows: [], total: 0 });
    document.getElementById('scopedResultsCount').innerText = `Target locked: ${scopedState.filename}. Ready.`;
    document.getElementById('scopedTiming').innerText = "0ms";
    return;
  }

  scopedState.currentPage = page;
  scopedState.currentQuery = q;
  const offset = scopedState.currentPage * scopedState.pageSize;

  const t0 = performance.now();
  document.getElementById('scopedResultsCount').innerText = "Searching target...";

  try {
    const params = new URLSearchParams({
      q: scopedState.currentQuery,
      limit: scopedState.pageSize,
      offset: offset,
      mode: scopedState.mode || 'general'
    });
    if (scopedState.type === 'file') {
      params.append('file', scopedState.path);
    } else if (scopedState.type === 'folder') {
      params.append('folder', scopedState.path);
    }

    const res = await fetch(`/api/search?${params.toString()}`);
    const data = await res.json();
    const t1 = performance.now();
    document.getElementById('scopedTiming').innerText = `${Math.round(t1 - t0)}ms`;

    renderScopedViewData(data);
  } catch (e) {
    console.error(e);
    document.getElementById('scopedResultsCount').innerText = "Scoped search error";
  }
}

function changeScopedPage(delta) {
  const newPage = scopedState.currentPage + delta;
  if (newPage >= 0 && (newPage * scopedState.pageSize) < scopedState.totalResults) {
    doScopedSearch(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function renderScopedViewData(data) {
  scopedState.lastResults = data.rows || [];
  scopedState.totalResults = data.total || 0;
  const paginationBar = document.getElementById('scopedPaginationBar');
  const topPaginationBar = document.getElementById('scopedTopPaginationBar');

  if (scopedState.totalResults > scopedState.pageSize) {
    const start = scopedState.currentPage * scopedState.pageSize + 1;
    const end = Math.min((scopedState.currentPage + 1) * scopedState.pageSize, scopedState.totalResults);
    const infoText = `Showing ${start.toLocaleString()}-${end.toLocaleString()} of ${scopedState.totalResults.toLocaleString()} records`;
    const pageBadgeText = `Page ${scopedState.currentPage + 1} of ${Math.ceil(scopedState.totalResults / scopedState.pageSize)}`;
    const isPrevDisabled = (scopedState.currentPage === 0);
    const isNextDisabled = ((scopedState.currentPage + 1) * scopedState.pageSize >= scopedState.totalResults);

    paginationBar.style.display = 'flex';
    document.getElementById('scopedPageInfo').innerText = infoText;
    document.getElementById('scopedPageNumberBadge').innerText = pageBadgeText;
    document.getElementById('scopedPrevBtn').disabled = isPrevDisabled;
    document.getElementById('scopedNextBtn').disabled = isNextDisabled;

    if (topPaginationBar) {
      topPaginationBar.style.display = 'flex';
      document.getElementById('scopedTopPageInfo').innerText = infoText;
      document.getElementById('scopedTopPageNumberBadge').innerText = pageBadgeText;
      document.getElementById('scopedTopPrevBtn').disabled = isPrevDisabled;
      document.getElementById('scopedTopNextBtn').disabled = isNextDisabled;
    }
  } else if (scopedState.totalResults > 0) {
    paginationBar.style.display = 'flex';
    document.getElementById('scopedPageInfo').innerText = `${scopedState.totalResults.toLocaleString()} records`;
    document.getElementById('scopedPageNumberBadge').innerText = `Page 1 of 1`;
    document.getElementById('scopedPrevBtn').disabled = true;
    document.getElementById('scopedNextBtn').disabled = true;

    if (topPaginationBar) {
      topPaginationBar.style.display = 'flex';
      document.getElementById('scopedTopPageInfo').innerText = `${scopedState.totalResults.toLocaleString()} records`;
      document.getElementById('scopedTopPageNumberBadge').innerText = `Page 1 of 1`;
      document.getElementById('scopedTopPrevBtn').disabled = true;
      document.getElementById('scopedTopNextBtn').disabled = true;
    }
  } else {
    paginationBar.style.display = 'none';
    if (topPaginationBar) topPaginationBar.style.display = 'none';
  }

  document.getElementById('scopedResultsCount').innerText = `${scopedState.totalResults.toLocaleString()} matches in ${scopedState.filename}`;
  renderScopedCards(scopedState.lastResults);
  renderScopedTableRows(scopedState.lastResults);

  if (scopedState.lastResults.length > 0 && isImageFile(scopedState.lastResults[0].file)) {
    const firstImg = scopedState.lastResults[0];
    showImagePreview(firstImg.path, firstImg.sheet, scopedState.currentQuery);
  }
}

function renderScopedCards(rows) {
  const container = document.getElementById('scopedCardsContainer');
  container.innerHTML = '';

  if (!rows || rows.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 48px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle);">
        ${scopedState.active ? `No records found in "${scopedState.filename}" for "${escapeHtml(scopedState.currentQuery)}".` : 'No target selected yet. Choose a folder or file above.'}
      </div>
    `;
    return;
  }

  const isGeneral = ((scopedState.mode || 'general') === 'general');

  rows.forEach(r => {
    const card = document.createElement('div');
    card.className = 'result-card';
    const escapedPath = (r.path || '').replace(/'/g, "\\'");
    const escapedSheet = (r.sheet || '').replace(/'/g, "\\'");
    const isImage = isImageFile(r.file);

    let metaRowHtml = '';
    if (isGeneral) {
      const folderDisplay = r.folder ? escapeHtml(r.folder) : '';
      const sizeDisplay = r.size ? formatFileSize(r.size) : '';
      metaRowHtml = `
        <div class="general-card-meta">
          ${folderDisplay ? `<span class="meta-tag" title="${folderDisplay}">${SVG_RAW.folder} ${folderDisplay.length > 55 ? '...' + folderDisplay.slice(-52) : folderDisplay}</span>` : ''}
          ${r.sheet ? `<span class="meta-tag">${SVG_RAW.context} ${escapeHtml(r.sheet)} (Row ${r.row})</span>` : ''}
          ${sizeDisplay ? `<span class="meta-tag">💾 ${sizeDisplay}</span>` : ''}
          ${r.indexed_at && r.indexed_at !== '—' ? `<span class="meta-tag">📅 ${escapeHtml(r.indexed_at)}</span>` : ''}
        </div>
      `;
    } else {
      let pillsHtml = '';
      if (r.target && r.target !== '—') {
        pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.target}', 'Target Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.target, scopedState.currentQuery)}</b></span>`;
      }
      if (r.other && r.other !== '—') {
        pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.other}', 'Party Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.other, scopedState.currentQuery)}</b></span>`;
      }
      if (r.name && r.name !== '—') {
        pillsHtml += `<span class="info-pill arabic" onclick="copyToClipboard('${r.name}', 'Name')">👤 <b>${highlightMatch(r.name, scopedState.currentQuery)}</b></span>`;
      }
      if (r.time && r.time !== '—') {
        pillsHtml += `<span class="info-pill">📅 ${escapeHtml(r.time)}</span>`;
      }
      if (pillsHtml) {
        metaRowHtml = `<div class="card-pill-group">${pillsHtml}</div>`;
      }
    }

    card.innerHTML = `
      <div class="card-header">
        <div class="file-meta">
          ${getFileExtBadge(r.file)}
          <span title="${escapeHtml(r.path || '')}">${escapeHtml(r.file)}</span>
        </div>
        <div class="card-actions">
          ${isImage ? `<button class="btn-image-preview" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(scopedState.currentQuery || '')}')">${SVG_RAW.eye} Preview & Text</button>` : ''}
          <button class="btn-action" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})">
            ${SVG_RAW.context} Context
          </button>
          <button class="btn-action" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})">
            ${SVG_RAW.open} Open
          </button>
          <button class="btn-action" onclick="revealFolder('${escapedPath}')">
            ${SVG_RAW.folder} Folder
          </button>
        </div>
      </div>
      ${metaRowHtml}
      <div class="snippet-box" ${isImage ? `style="cursor:pointer;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(scopedState.currentQuery || '')}')"` : ''}>
        ${highlightMatch(r.snippet, scopedState.currentQuery)}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderScopedTableRows(rows) {
  const tbody = document.getElementById('scopedTableBody');
  const thead = document.getElementById('scopedTableHead');
  tbody.innerHTML = '';

  const isGeneral = ((scopedState.mode || 'general') === 'general');

  if (isGeneral) {
    thead.innerHTML = `
      <th>File</th>
      <th>Folder / Section</th>
      <th>Snippet / Matched Content</th>
      <th>Indexed</th>
      <th>Actions</th>
    `;
  } else {
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
  }

  if (!rows || rows.length === 0) {
    const colspan = isGeneral ? 5 : 9;
    tbody.innerHTML = `<tr><td colspan="${colspan}" style="text-align:center; padding: 40px; color:#64748b;">No records match your target search.</td></tr>`;
    return;
  }

  rows.forEach(r => {
    const tr = document.createElement('tr');
    const escapedPath = (r.path || '').replace(/'/g, "\\'");
    const escapedSheet = (r.sheet || '').replace(/'/g, "\\'");
    const isImage = isImageFile(r.file);

    if (isGeneral) {
      const folderName = r.folder ? r.folder.split('/').slice(-2).join('/') : '';
      tr.innerHTML = `
        <td title="${escapeHtml(r.path)}">
          ${getFileExtBadge(r.file)}
          <span style="margin-left:5px; font-weight:600;">${escapeHtml(r.file)}</span>
        </td>
        <td style="color:#94a3b8; font-size:0.8rem;" title="${escapeHtml(r.folder || '')}">
          <div>📁 ${escapeHtml(folderName || 'Root')}</div>
          ${r.sheet ? `<div style="color:var(--text-dim); font-size:0.75rem;">${escapeHtml(r.sheet)} (Row ${r.row})</div>` : ''}
        </td>
        <td style="max-width: 520px; font-family:'JetBrains Mono', monospace; font-size:0.8rem; line-height:1.45;">
          ${highlightMatch(r.snippet, scopedState.currentQuery)}
        </td>
        <td style="white-space:nowrap; color:#94a3b8; font-size:0.78rem;">
          ${escapeHtml(r.indexed_at || r.time || '—')}
        </td>
        <td>
          <div style="display:flex; gap:4px;">
            ${isImage ? `<button class="btn-action" style="padding:2px 6px; color:#a855f7;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(scopedState.currentQuery || '')}')" title="Preview Image">${SVG_RAW.eye}</button>` : ''}
            <button class="btn-action" style="padding:2px 6px;" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})" title="Open File">${SVG_RAW.open}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})" title="Context">${SVG_RAW.context}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="revealFolder('${escapedPath}')" title="Folder">${SVG_RAW.folder}</button>
          </div>
        </td>
      `;
    } else {
      tr.innerHTML = `
        <td title="${escapeHtml(r.path)}">${getFileExtBadge(r.file)} <span style="margin-left:4px;">${escapeHtml(r.file)}</span></td>
        <td>${escapeHtml(r.time)}</td>
        <td>${escapeHtml(r.dir)}</td>
        <td style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.target}', 'Target Phone')">${highlightMatch(r.target, scopedState.currentQuery)}</td>
        <td style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.other}', 'Party Phone')">${highlightMatch(r.other, scopedState.currentQuery)}</td>
        <td class="arabic" style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.name}', 'Name')">${highlightMatch(r.name, scopedState.currentQuery)}</td>
        <td>${escapeHtml(r.duration)}</td>
        <td class="arabic">${highlightMatch(r.address || r.sheet, scopedState.currentQuery)}</td>
        <td>
          <div style="display:flex; gap:4px;">
            ${isImage ? `<button class="btn-action" style="padding:2px 6px; color:#a855f7;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(scopedState.currentQuery || '')}')">${SVG_RAW.eye}</button>` : ''}
            <button class="btn-action" style="padding:2px 6px;" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})">${SVG_RAW.open}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})">${SVG_RAW.context}</button>
          </div>
        </td>
      `;
    }
    tbody.appendChild(tr);
  });
}

function exportIndex() {
  window.location.href = '/api/index/export';
}

function exportCSV() {
  if (!currentQuery) {
    alert("Please enter a search query before exporting CSV!");
    return;
  }
  window.location.href = `/api/search/csv?q=${encodeURIComponent(currentQuery)}`;
}

async function handleImportFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  if (!confirm(`Are you sure you want to restore/import "${file.name}"? Existing index will be backed up.`)) {
    return;
  }
  showToast("📥 Uploading and verifying database...");
  const formData = new FormData();
  formData.append('dbfile', file, file.name);

  try {
    const res = await fetch('/api/index/import', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.ok) {
      showToast("✅ Database restored! Reloading stats...");
      refreshStats();
      doSearch(0);
    } else {
      alert(`❌ Import error: ${data.error}`);
    }
  } catch (err) {
    showToast("❌ Network error importing database");
  }
}

window.onload = () => {
  injectStaticIcons();
  refreshStats();
  refreshWatcherStatus();
  loadQuickFilters();
  refreshBookmarkCount();
  initDragAndDrop();
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
            chosen = None
            zenity_bin = shutil.which("zenity")
            if zenity_bin:
                try:
                    res = subprocess.run(
                        [zenity_bin, "--file-selection", "--directory", "--title=Select Folder to Index or Search"],
                        capture_output=True, text=True, timeout=120, env=os.environ
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        chosen = res.stdout.strip()
                except Exception as e:
                    print(f"[ZENITY PICK FOLDER ERROR] {e}")
            if not chosen and shutil.which("kdialog"):
                try:
                    res = subprocess.run(
                        ["kdialog", "--getexistingdirectory", os.path.expanduser("~"), "--title", "Select Folder to Index"],
                        capture_output=True, text=True, timeout=120, env=os.environ
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        chosen = res.stdout.strip()
                except Exception:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": bool(chosen), "path": chosen or ""}).encode("utf-8"))
        elif parsed.path == "/api/dialog/pick-file":
            chosen = None
            zenity_bin = shutil.which("zenity")
            if zenity_bin:
                try:
                    res = subprocess.run(
                        [zenity_bin, "--file-selection", "--title=Select File or Image to Index",
                         "--file-filter=Supported Documents & Images | *.pdf *.docx *.xlsx *.xls *.png *.jpg *.jpeg *.webp *.txt *.csv",
                         "--file-filter=All Files | *"],
                        capture_output=True, text=True, timeout=120, env=os.environ
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        chosen = res.stdout.strip()
                except Exception as e:
                    print(f"[ZENITY PICK FILE ERROR] {e}")
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
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/bookmarks/add":
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
