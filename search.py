import sys
import os
import sqlite3
import argparse
import re
import subprocess
import urllib.parse

try:
    from services.state import load_config, get_active_db_path
    load_config()
    DB_PATH = get_active_db_path()
except Exception:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheets_index.db")

def open_in_app(file_path, sheet_name=None, row_idx=None):
    if not file_path or not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return False
    ext = os.path.splitext(file_path)[1].lower()
    env = os.environ.copy()
    if ext in ('.xlsx', '.xls', '.csv', '.ods'):
        abs_p = os.path.abspath(file_path)
        quoted_path = urllib.parse.quote(abs_p)
        if sheet_name and row_idx:
            uri = f"file://{quoted_path}#{sheet_name}.A{row_idx}"
        elif row_idx:
            uri = f"file://{quoted_path}#A{row_idx}"
        else:
            uri = f"file://{quoted_path}"
        try:
            subprocess.Popen(['localc', '--norestore', uri], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            print(f"🚀 Opened in LibreOffice Calc -> {os.path.basename(file_path)} (Sheet: {sheet_name or 'Default'}, Row: {row_idx or 1})")
            return True
        except Exception:
            pass
    try:
        subprocess.Popen(['xdg-open', file_path], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(f"🚀 Opened in default app -> {os.path.basename(file_path)}")
        return True
    except Exception as e:
        print(f"Error launching viewer: {e}")
        return False



import indexer_engine

def normalize_phone(val):
    norm = indexer_engine.normalize_phone(val)
    if norm:
        return norm
    if not val:
        return ""
    digits = re.sub(r'\D', '', str(val))
    return digits

def normalize_arabic(text):
    return indexer_engine.normalize_arabic(text)

def search_phone(query, limit=50):
    norm = normalize_phone(query)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    sql = """
    SELECT f.filename, c.sheet_name, c.row_idx, c.target_msisdn, c.other_msisdn, c.other_name, c.event_time, c.duration, c.direction, c.cell_address, f.file_path
    FROM cdr_records c
    JOIN files f ON c.file_id = f.file_id
    WHERE c.target_norm = ? OR c.other_norm = ? OR c.target_msisdn LIKE ? OR c.other_msisdn LIKE ? OR c.raw_row LIKE ?
    LIMIT ?;
    """
    pattern = f"%{query}%"
    cur.execute(sql, (norm or query, norm or query, pattern, pattern, pattern, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

def search_name(query, limit=50):
    norm = normalize_arabic(query)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    sql = """
    SELECT f.filename, c.sheet_name, c.row_idx, c.target_msisdn, c.other_msisdn, c.other_name, c.event_time, c.duration, c.direction, c.cell_address, f.file_path
    FROM cdr_records c
    JOIN files f ON c.file_id = f.file_id
    WHERE c.other_name_norm LIKE ? OR c.other_name LIKE ?
    LIMIT ?;
    """
    pattern = f"%{norm}%"
    cur.execute(sql, (pattern, f"%{query}%", limit))
    rows = cur.fetchall()
    conn.close()
    return rows

def search_id(query, limit=50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    sql = """
    SELECT f.filename, c.sheet_name, c.row_idx, c.target_msisdn, c.other_msisdn, c.other_name, c.other_id, c.event_time, f.file_path
    FROM cdr_records c
    JOIN files f ON c.file_id = f.file_id
    WHERE c.other_id LIKE ?
    LIMIT ?;
    """
    cur.execute(sql, (f"%{query}%", limit))
    rows = cur.fetchall()
    conn.close()
    return rows

def search_universal(query, limit=50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    sql = """
    SELECT file_path, sheet_name, row_idx, content
    FROM universal_search
    WHERE universal_search MATCH ?
    LIMIT ?;
    """
    # Safe match query
    safe_q = f'"{query}"'
    try:
        cur.execute(sql, (safe_q, limit))
        rows = cur.fetchall()
    except Exception:
        cur.execute("SELECT file_path, sheet_name, row_idx, content FROM universal_search WHERE content LIKE ? LIMIT ?;", (f"%{query}%", limit))
        rows = cur.fetchall()
    conn.close()
    return rows

def search_prefix(prefix, limit=1000):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    norm = normalize_phone(prefix) if len(prefix) > 2 else prefix
    sql = """
    SELECT DISTINCT c.other_norm, c.other_name, COUNT(*) as cnt
    FROM cdr_records c
    WHERE c.other_norm LIKE ? OR c.target_norm LIKE ?
    GROUP BY c.other_norm
    ORDER BY cnt DESC
    LIMIT ?;
    """
    pattern = f"{norm}%"
    cur.execute(sql, (pattern, pattern, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

def main():
    parser = argparse.ArgumentParser(description="Instant search across indexed CDR and Excel sheets.")
    parser.add_argument("query", nargs="?", help="Search query (phone number, name, ID, or keyword)")
    parser.add_argument("--phone", "-p", help="Search by exact or partial phone number")
    parser.add_argument("--name", "-n", help="Search by contact/party name")
    parser.add_argument("--id", "-i", help="Search by National ID / Sub ID")
    parser.add_argument("--prefix", help="List all phone numbers starting with prefix (e.g. 015, 010)")
    parser.add_argument("--raw", "-r", help="Universal full-text keyword search")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Max results to display")
    parser.add_argument("--open", "-o", action="store_true", help="Automatically open the first matching file at the exact row in Calc/default app")

    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Error: Database index '{DB_PATH}' not found. Please run 'python3 index_sheets.py' first.")
        sys.exit(1)

    if args.prefix:
        print(f"Searching for phone numbers starting with prefix '{args.prefix}'...")
        res = search_prefix(args.prefix, args.limit)
        print(f"\nFound {len(res)} matching numbers:")
        print(f"{'Phone':<15} | {'Occurrences':<12} | {'Name'}")
        print("-" * 55)
        for num, name, cnt in res:
            if num:
                print(f"{num:<15} | {cnt:<12} | {name or '—'}")
        return

    if args.phone:
        res = search_phone(args.phone, args.limit)
        display_cdr_results(res)
        if args.open and res:
            open_in_app(res[0][10], sheet_name=res[0][1], row_idx=res[0][2])
        return

    if args.name:
        res = search_name(args.name, args.limit)
        display_cdr_results(res)
        if args.open and res:
            open_in_app(res[0][10], sheet_name=res[0][1], row_idx=res[0][2])
        return

    if args.id:
        res = search_id(args.id, args.limit)
        print(f"\nFound {len(res)} results matching ID '{args.id}':")
        for row in res:
            print(f"File: {row[0]} [Sheet: {row[1]}, Row: {row[2]}] | ID: {row[6]} | Name: {row[5]} | Phone: {row[4]} | Time: {row[7]}")
        if args.open and res:
            open_in_app(res[0][8], sheet_name=res[0][1], row_idx=res[0][2])
        return

    if args.raw:
        res = search_universal(args.raw, args.limit)
        print(f"\nFound {len(res)} matches for '{args.raw}':")
        for row in res:
            fname = os.path.basename(row[0])
            print(f"File: {fname} [Sheet: {row[1]}, Row: {row[2]}] -> {row[3][:120]}...")
        if args.open and res:
            open_in_app(res[0][0], sheet_name=res[0][1], row_idx=res[0][2])
        return

    if args.query:
        q = args.query.strip()
        # Auto detect type
        if re.search(r'^\+?\d+$', q):
            print(f"Searching phone/numeric records for: {q}")
            res = search_phone(q, args.limit)
            if res:
                display_cdr_results(res)
                if args.open:
                    open_in_app(res[0][10], sheet_name=res[0][1], row_idx=res[0][2])
                return
            res_id = search_id(q, args.limit)
            if res_id:
                for row in res_id:
                    print(f"File: {row[0]} [Sheet: {row[1]}, Row: {row[2]}] | ID: {row[6]} | Name: {row[5]} | Phone: {row[4]}")
                if args.open:
                    open_in_app(res_id[0][8], sheet_name=res_id[0][1], row_idx=res_id[0][2])
                return
        else:
            print(f"Searching names for: {q}")
            res = search_name(q, args.limit)
            if res:
                display_cdr_results(res)
                if args.open:
                    open_in_app(res[0][10], sheet_name=res[0][1], row_idx=res[0][2])
                return

        print(f"Falling back to universal full-text search for '{q}'...")
        res = search_universal(q, args.limit)
        print(f"Found {len(res)} matches:")
        for row in res:
            fname = os.path.basename(row[0])
            print(f"[{fname} | {row[1]}:R{row[2]}] {row[3][:130]}")
        if args.open and res:
            open_in_app(res[0][0], sheet_name=res[0][1], row_idx=res[0][2])
    else:
        parser.print_help()

def display_cdr_results(rows):
    print(f"\nFound {len(rows)} matching CDR records:")
    print(f"{'File':<30} | {'Sheet & Row':<18} | {'Time':<20} | {'Dir':<6} | {'Target':<13} | {'Other':<13} | {'Name'}")
    print("-" * 125)
    for r in rows:
        fname = (r[0][:27] + "...") if len(r[0]) > 30 else r[0]
        sheet_row = f"{str(r[1])[:10]}:R{r[2]}"
        ftime = str(r[6])[:19] if r[6] else "—"
        fdir = str(r[8])[:6] if r[8] else "—"
        ftarget = str(r[3])[:13] if r[3] else "—"
        fother = str(r[4])[:13] if r[4] else "—"
        fname_str = str(r[5])[:25] if r[5] else "—"
        print(f"{fname:<30} | {sheet_row:<18} | {ftime:<20} | {fdir:<6} | {ftarget:<13} | {fother:<13} | {fname_str}")

if __name__ == "__main__":
    main()

