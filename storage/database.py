"""
Database connection factory, SQLite WAL mode, schema initialization, and multi-DB routing.
Zero external pip dependencies.
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_connection(db_path, readonly=False):
    """
    Open connection to SQLite database with standard pragmas:
    - WAL journal mode
    - synchronous = NORMAL
    - 30-second busy timeout to avoid locked errors
    """
    if not db_path:
        conn = sqlite3.connect(":memory:", timeout=30.0)
        conn.execute("PRAGMA synchronous = NORMAL;")
        init_tables(conn)
        return conn
    
    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA mmap_size = 268435456;")  # 256MB mmap
    return conn

def init_tables(conn):
    """Ensure all core tables exist in the database."""
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS files (
        file_id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE,
        filename TEXT,
        folder TEXT,
        file_mtime REAL DEFAULT 0,
        file_size INTEGER DEFAULT 0,
        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Migration: add file_mtime and file_size if not present
    try:
        cur.execute("ALTER TABLE files ADD COLUMN file_mtime REAL DEFAULT 0;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE files ADD COLUMN file_size INTEGER DEFAULT 0;")
    except Exception:
        pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cdr_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER,
        sheet_name TEXT,
        row_idx INTEGER,
        target_msisdn TEXT,
        target_norm TEXT,
        other_msisdn TEXT,
        other_norm TEXT,
        other_name TEXT,
        other_name_norm TEXT,
        event_time TEXT,
        duration TEXT,
        direction TEXT,
        other_id TEXT,
        other_address TEXT,
        cell_id TEXT,
        cell_address TEXT,
        raw_row TEXT,
        FOREIGN KEY(file_id) REFERENCES files(file_id)
    );
    """)

    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS universal_search USING fts5(
        file_path UNINDEXED,
        sheet_name UNINDEXED,
        row_idx UNINDEXED,
        content,
        tokenize = 'trigram'
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quick_filters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        query TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        sheet_name TEXT NOT NULL,
        row_idx INTEGER NOT NULL,
        tag TEXT DEFAULT 'Lead',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(file_path, sheet_name, row_idx)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ocr_boxes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        sheet_name TEXT NOT NULL,
        img_width INTEGER,
        img_height INTEGER,
        boxes_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(file_path, sheet_name)
    );
    """)

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

    cur.execute("CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cdr_file_id ON cdr_records(file_id);")
    conn.commit()
