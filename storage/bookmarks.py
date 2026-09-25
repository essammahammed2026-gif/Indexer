"""
Bookmark CRUD operations and document context window radius queries.
Zero external pip dependencies.
"""

import os
from .database import get_connection

def get_bookmarks(db_path):
    """Retrieve all tagged bookmarks and linked CDR record details."""
    if not db_path or not os.path.exists(db_path):
        return []
    try:
        conn = get_connection(db_path)
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

def add_bookmark(db_path, file_path, sheet_name, row_idx, tag="Lead", notes=""):
    """Insert or update a bookmarked row with custom tag and investigative note."""
    if not db_path:
        return False, "No database path provided"
    try:
        conn = get_connection(db_path)
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

def remove_bookmark(db_path, file_path, sheet_name, row_idx):
    """Delete a bookmarked record."""
    if not db_path or not os.path.exists(db_path):
        return False, "Database not found"
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM bookmarks WHERE file_path = ? AND sheet_name = ? AND row_idx = ?;", (file_path, sheet_name, int(row_idx)))
        conn.commit()
        conn.close()
        return True, "Bookmark removed"
    except Exception as e:
        return False, str(e)

def get_context_window(db_path, file_path, sheet_name, row_idx, window=3):
    """Retrieve up to +/- 3 lines around row_idx for document preview."""
    if not db_path or not os.path.exists(db_path):
        return []
    try:
        conn = get_connection(db_path)
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
