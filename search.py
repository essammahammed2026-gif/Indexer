#!/usr/bin/env python3
"""
CLI Instant Search Interface for Indexer Engine.
Delegates directly to storage.query_db for unified FTS5, Telecom CDR, and fuzzy matching.
Zero external dependencies (Python standard library only).
"""

import sys
import os
import argparse
from core.system_interop import open_in_app
from services.state import load_config, get_active_db_path
import storage

def main():
    load_config()
    db_path = get_active_db_path()

    if not os.path.exists(db_path):
        print(f"Error: Database index '{db_path}' not found. Please index documents first.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Instant search across indexed CDR and documents.")
    parser.add_argument("query", nargs="?", help="Search query (phone number, name, ID, or keyword)")
    parser.add_argument("--phone", "-p", help="Search by phone number")
    parser.add_argument("--name", "-n", help="Search by contact name")
    parser.add_argument("--id", "-i", help="Search by National ID / Sub ID")
    parser.add_argument("--prefix", help="List all phone numbers starting with prefix (e.g. 010, 012)")
    parser.add_argument("--raw", "-r", help="Universal full-text keyword search")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Max results to display")
    parser.add_argument("--open", "-o", action="store_true", help="Open first matching result in Calc or default app")

    args = parser.parse_args()

    mode = "general"
    q = ""

    if args.prefix:
        q = f"prefix:{args.prefix}"
        mode = "telecom"
    elif args.phone:
        q = args.phone.strip()
        mode = "telecom"
    elif args.name:
        q = args.name.strip()
        mode = "general"
    elif args.id:
        q = args.id.strip()
        mode = "general"
    elif args.raw:
        q = args.raw.strip()
        mode = "general"
    elif args.query:
        q = args.query.strip()
        # Telecom mode if query is strictly digits/phone format
        if q.isdigit() or q.startswith('+') or q.startswith('01'):
            mode = "telecom"
        else:
            mode = "general"
    else:
        parser.print_help()
        return

    data = storage.query_db(db_path, q, limit=args.limit, mode=mode)
    rows = data.get("rows", [])
    total = data.get("total", len(rows))

    if data.get("type") == "prefix":
        print(f"\nFound {total} distinct numbers starting with '{q.replace('prefix:', '')}':")
        print(f"{'Phone':<16} | {'Occurrences':<12} | {'Name'}")
        print("-" * 55)
        for r in rows:
            print(f"{r.get('phone', ''):<16} | {r.get('count', 0):<12} | {r.get('name') or '—'}")
        return

    if mode == "telecom" and data.get("type") != "general":
        print(f"\nFound {total} matching Telecom CDR records (showing {len(rows)}):")
        print(f"{'File':<30} | {'Sheet & Row':<18} | {'Time':<18} | {'Dir':<6} | {'Target':<13} | {'Other':<13} | {'Name'}")
        print("-" * 125)
        for r in rows:
            fname = (r.get("file", "")[:27] + "...") if len(r.get("file", "")) > 30 else r.get("file", "")
            sheet_row = f"{str(r.get('sheet', ''))[:10]}:R{r.get('row', '')}"
            ftime = str(r.get("time") or "—")[:18]
            fdir = str(r.get("dir") or "—")[:6]
            ftarget = str(r.get("target") or "—")[:13]
            fother = str(r.get("other") or "—")[:13]
            fname_str = str(r.get("name") or "—")[:25]
            print(f"{fname:<30} | {sheet_row:<18} | {ftime:<18} | {fdir:<6} | {ftarget:<13} | {fother:<13} | {fname_str}")

        if args.open and rows:
            first = rows[0]
            open_in_app(first.get("path"), sheet_name=first.get("sheet"), row_idx=first.get("row"))
        return

    # General full text search results
    print(f"\nFound {total} matching documents (showing {len(rows)}):")
    print(f"{'File':<32} | {'Location':<20} | {'Matched Content / Snippet'}")
    print("-" * 120)
    for r in rows:
        fname = (r.get("file", "")[:29] + "...") if len(r.get("file", "")) > 32 else r.get("file", "")
        loc = f"{str(r.get('sheet') or 'Sheet')[:12]}:R{r.get('row', 1)}"
        snippet = (r.get("snippet") or r.get("content") or "").replace('\n', ' ')
        if len(snippet) > 65:
            snippet = snippet[:62] + "..."
        print(f"{fname:<32} | {loc:<20} | {snippet}")

    if args.open and rows:
        first = rows[0]
        open_in_app(first.get("path"), sheet_name=first.get("sheet"), row_idx=first.get("row"))

if __name__ == "__main__":
    main()
