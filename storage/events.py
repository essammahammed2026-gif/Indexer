"""
Change events audit log repository and database snapshot backups.
Zero external pip dependencies.
"""

import os
import time
import shutil
from .database import get_connection

def record_change_event(db_path, event_type, file_path, old_path=None, records_count=0, details=""):
    """Log an index/file modification, addition, rename or removal in SQLite change_events."""
    if not db_path:
        return False
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS change_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            old_path TEXT,
            filename TEXT,
            records_count INTEGER DEFAULT 0,
            details TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        fname = os.path.basename(file_path) if file_path else ""
        cur.execute("""
        INSERT INTO change_events (event_type, file_path, old_path, filename, records_count, details, is_read)
        VALUES (?, ?, ?, ?, ?, ?, 0);
        """, (event_type, file_path, old_path, fname, records_count, details))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[CHANGE EVENT LOG ERROR] {e}")
        return False

def get_change_events(db_path, limit=50, offset=0, unread_only=False):
    """Retrieve indexed change notifications and unread badge count."""
    if not db_path or not os.path.exists(db_path):
        return {"events": [], "unread_count": 0, "total": 0}
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS change_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            old_path TEXT,
            filename TEXT,
            records_count INTEGER DEFAULT 0,
            details TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("SELECT COUNT(*) FROM change_events WHERE is_read = 0;")
        unread_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM change_events;")
        total_count = cur.fetchone()[0]

        query = """
        SELECT id, event_type, file_path, old_path, filename, records_count, details, is_read, created_at
        FROM change_events
        """
        params = []
        if unread_only:
            query += " WHERE is_read = 0"
        query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = []
        for r in cur.fetchall():
            rows.append({
                "id": r[0],
                "event_type": r[1],
                "file_path": r[2],
                "old_path": r[3],
                "filename": r[4] or os.path.basename(r[2]),
                "records_count": r[5] or 0,
                "details": r[6] or "",
                "is_read": bool(r[7]),
                "created_at": r[8]
            })
        conn.close()
        return {"events": rows, "unread_count": unread_count, "total": total_count}
    except Exception as e:
        print(f"[GET NOTIFICATIONS ERROR] {e}")
        return {"events": [], "unread_count": 0, "total": 0}

def mark_change_events_read(db_path, event_ids=None):
    """Mark all or specific notification events as read."""
    if not db_path or not os.path.exists(db_path):
        return True, "No database"
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS change_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            old_path TEXT,
            filename TEXT,
            records_count INTEGER DEFAULT 0,
            details TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        if event_ids:
            placeholders = ",".join("?" for _ in event_ids)
            cur.execute(f"UPDATE change_events SET is_read = 1 WHERE id IN ({placeholders});", event_ids)
        else:
            cur.execute("UPDATE change_events SET is_read = 1 WHERE is_read = 0;")
        conn.commit()
        conn.close()
        return True, "Notifications marked as read"
    except Exception as e:
        return False, str(e)

def clear_all_change_events(db_path):
    """Clear notification history log."""
    if not db_path or not os.path.exists(db_path):
        return True, "No database"
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM change_events;")
        conn.commit()
        conn.close()
        return True, "Notification history cleared"
    except Exception as e:
        return False, str(e)

def backup_database(db_path):
    """Create a rotating daily backup snapshot of the database."""
    if not db_path or not os.path.exists(db_path):
        return False, "Database does not exist yet"
    try:
        date_str = time.strftime("%Y%m%d")
        snap_path = f"{db_path}.snap_{date_str}"
        shutil.copy2(db_path, snap_path)
        return True, f"Backup created: {os.path.basename(snap_path)}"
    except Exception as e:
        return False, str(e)
