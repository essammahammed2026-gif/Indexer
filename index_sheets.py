#!/usr/bin/env python3
"""
CLI Batch Ingestion Tool for Indexer Engine
Indexes an entire directory or single file recursively into sheets_index.db.
Zero external dependencies (delegates to indexer_engine).
"""
import os
import sys
import sqlite3
import argparse
from datetime import datetime
import indexer_engine

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheets_index.db")

def build_index(target_path=None):
    if not target_path:
        target_path = os.path.dirname(os.path.abspath(__file__))

    target_path = os.path.abspath(target_path)
    if not os.path.exists(target_path):
        print(f"Error: Target path '{target_path}' does not exist.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        indexer_engine.init_db(conn)

        files_to_scan = []
        supported_exts = {
            '.xlsx', '.xls', '.csv', '.tsv',
            '.docx', '.odt', '.txt', '.log', '.json', '.sql',
            '.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'
        }

        if os.path.isfile(target_path):
            ext = os.path.splitext(target_path)[1].lower()
            if ext in supported_exts:
                files_to_scan.append(target_path)
            else:
                print(f"Warning: File extension '{ext}' is not supported.")
        else:
            for root, _, files in os.walk(target_path):
                # Skip git, cache, and uploads
                if any(part.startswith('.') or part in ('uploads', '__pycache__') for part in root.split(os.sep)):
                    continue
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in supported_exts:
                        files_to_scan.append(os.path.join(root, f))

        print(f"Indexing {len(files_to_scan)} files into {DB_PATH}...")
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
        print(f"Database: {DB_PATH}")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Batch index documents and sheets into Indexer DB.")
    parser.add_argument("path", nargs="?", default=None, help="Directory or file path to index (defaults to project dir)")
    args = parser.parse_args()
    build_index(args.path)

if __name__ == "__main__":
    main()

