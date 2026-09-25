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
        db_path = os.path.join(BASE_DIR, "sheets_index.db")
    
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
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
        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

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
    conn.commit()
