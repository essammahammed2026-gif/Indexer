#!/usr/bin/env python3
"""
CLI Batch Ingestion Tool for Indexer Engine.
Indexes an entire directory or single file recursively into an SQLite database.
Zero external dependencies (delegates to indexer_engine).
Strictly NO fallbacks to default databases or application directory.
"""
import os
import sys
import sqlite3
import argparse
from datetime import datetime
import indexer_engine
from services.state import load_config, get_active_db_path, APP_CONFIG

def resolve_db_path(db_arg=None):
    load_config()
    db_path = get_active_db_path()
    if db_arg:
        storage_dir = APP_CONFIG.get("db_storage_dir", "")
        found = False
        for k, meta in APP_CONFIG.get("databases", {}).items():
            if db_arg.lower() in (k.lower(), meta.get("filename", "").lower(), meta.get("nickname", "").lower()):
                candidate = os.path.join(storage_dir, meta.get("filename", ""))
                if os.path.exists(candidate):
                    db_path = candidate
                    found = True
                    break
        if not found:
            candidate = os.path.abspath(db_arg)
            if os.path.exists(candidate):
                db_path = candidate
            elif storage_dir and os.path.exists(os.path.join(storage_dir, db_arg)):
                db_path = os.path.join(storage_dir, db_arg)
            elif storage_dir and db_arg.endswith(".db"):
                db_path = os.path.join(storage_dir, db_arg)

    if not db_path:
        print("Error: No database loaded. Please select an active database in the app or specify --db <name/path>.")
        sys.exit(1)
    return db_path

def build_index(target_path, db_path):
    target_path = os.path.abspath(target_path)
    if not os.path.exists(target_path):
        print(f"Error: Target path '{target_path}' does not exist.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        indexer_engine.init_db(conn)

        files_to_scan = []
        supported_exts = {
            '.xlsx', '.xls', '.csv', '.tsv',
            '.docx', '.odt', '.txt', '.log', '.json', '.sql',
            '.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp', '.zip'
        }

        if os.path.isfile(target_path):
            ext = os.path.splitext(target_path)[1].lower()
            if ext in supported_exts:
                files_to_scan.append(target_path)
            else:
                print(f"Warning: File extension '{ext}' is not supported.")
        else:
            for root, _, files in os.walk(target_path):
                if any(part.startswith('.') or part in ('__pycache__',) for part in root.split(os.sep)):
                    continue
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in supported_exts and not f.startswith('~$') and not f.startswith('.'):
                        files_to_scan.append(os.path.join(root, f))

        print(f"Indexing {len(files_to_scan)} files into {db_path}...")
        start_time = datetime.now()
        total_records = 0

        for i, fpath in enumerate(files_to_scan, 1):
            rel = os.path.relpath(fpath, target_path) if os.path.isdir(target_path) else os.path.basename(fpath)
            try:
                count = indexer_engine.process_file(fpath, conn)
                total_records += count
                indexer_engine.record_change_event(
                    conn,
                    event_type="indexed",
                    file_path=fpath,
                    records_count=count,
                    details=f"CLI batch indexed with {count:,} entries"
                )
                print(f"[{i}/{len(files_to_scan)}] Indexed {rel} ({count} entries)")
            except Exception as e:
                print(f"[{i}/{len(files_to_scan)}] Error indexing {rel}: {e}")

        duration = (datetime.now() - start_time).total_seconds()
        print(f"\nDone! Indexed {total_records} searchable entries from {len(files_to_scan)} files in {duration:.1f}s.")
        print(f"Database: {db_path}")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Batch index documents and sheets into Indexer DB.")
    parser.add_argument("path", help="Directory or file path to index")
    parser.add_argument("--db", help="Target database name, ID, or file path")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    build_index(args.path, db_path)

if __name__ == "__main__":
    main()
