"""
Search repository: FTS5 trigram queries, Telecom CDR matching, fuzzy fallback, and stats metrics.
Zero external pip dependencies.
"""

import os
import re
from core import normalize_phone, normalize_arabic, levenshtein_dist, parse_google_query
from .database import get_connection

def query_db(db_path, query, limit=50, offset=0, scope_file=None, scope_folder=None, mode="general"):
    """
    Execute universal document search or telecom CDR search across SQLite tables.
    Returns: {"rows": [...], "total": int, "limit": limit, "offset": offset, "mode": mode}
    """
    if not db_path or not os.path.exists(db_path):
        return {"rows": [], "total": 0, "limit": limit, "offset": offset, "mode": mode}
        
    conn = get_connection(db_path)
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
                    "snippet": raw_text[:400] if raw_text else "—"
                })
            return {"type": "cdr", "rows": cdr_rows, "total": total_count, "limit": limit, "offset": offset, "mode": mode}

    # MODE B: GENERAL SEARCH (DEFAULT)
    # 1. Parse Google-style search operators
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

    # 4. Short Query / Substring fallback on universal_search if no FTS or CDR matches were found
    if mode == "general" and len(query) >= 1:
        like_pat = f"%{query}%"
        like_count_sql = f"""
        SELECT COUNT(*)
        FROM universal_search u
        JOIN files f ON u.file_path = f.file_path
        WHERE u.content LIKE ? {scope_clause_fts} {filetype_clause_fts};
        """
        try:
            cur.execute(like_count_sql, [like_pat] + scope_params_fts + filetype_params_fts)
            like_total = cur.fetchone()[0] or 0
            if like_total > 0:
                like_sql = f"""
                SELECT u.file_path, u.sheet_name, u.row_idx, u.content,
                       f.folder, f.indexed_at,
                       c.event_time, c.direction, c.target_msisdn, c.other_msisdn, c.other_name, c.duration, c.cell_address
                FROM universal_search u
                JOIN files f ON u.file_path = f.file_path
                LEFT JOIN cdr_records c ON c.file_id = f.file_id AND c.sheet_name = u.sheet_name AND c.row_idx = u.row_idx
                WHERE u.content LIKE ? {scope_clause_fts} {filetype_clause_fts}
                LIMIT ? OFFSET ?;
                """
                cur.execute(like_sql, [like_pat] + scope_params_fts + filetype_params_fts + [limit, offset])
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
                return {"type": "general", "rows": results, "total": like_total, "limit": limit, "offset": offset, "mode": mode}
        except Exception:
            pass

    conn.close()
    return {"type": "general" if mode == "general" else "cdr", "rows": [], "total": 0, "limit": limit, "offset": offset, "mode": mode}

def get_stats(db_path, folder="", active_key="default", nickname="Main Database", storage_dir=""):
    """Retrieve file count, records count, and metadata for a database."""
    if not db_path or not os.path.exists(db_path):
        return {
            "files": 0, "records": 0, "watcher": False,
            "folder": folder, "active_db": active_key, "db_nickname": nickname,
            "db_path": db_path, "db_storage_dir": storage_dir
        }
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM files;")
        total_files = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM cdr_records;")
        total_records = cur.fetchone()[0]
        if not folder:
            cur.execute("SELECT folder FROM files LIMIT 1;")
            row = cur.fetchone()
            if row and row[0]:
                folder = row[0]
        conn.close()
        return {
            "files": total_files, "records": total_records, "watcher": False,
            "folder": folder, "active_db": active_key, "db_nickname": nickname,
            "db_path": db_path, "db_storage_dir": storage_dir
        }
    except Exception:
        return {
            "files": 0, "records": 0, "watcher": False,
            "folder": folder, "active_db": active_key, "db_nickname": nickname,
            "db_path": db_path, "db_storage_dir": storage_dir
        }

def get_quick_filters(db_path):
    if not db_path or not os.path.exists(db_path):
        return []
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS quick_filters (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, query TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        cur.execute("SELECT id, name, query FROM quick_filters ORDER BY id ASC;")
        rows = [{"id": r[0], "name": r[1], "query": r[2]} for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[FILTER ERROR] {e}")
        return []

def add_quick_filter(db_path, name, query):
    if not name or not query:
        return False, "Name and query are required"
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS quick_filters (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, query TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        cur.execute("INSERT INTO quick_filters (name, query) VALUES (?, ?);", (name.strip(), query.strip()))
        conn.commit()
        conn.close()
        return True, "Filter saved"
    except Exception as e:
        return False, str(e)

def delete_quick_filter(db_path, filter_id):
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM quick_filters WHERE id = ?;", (filter_id,))
        conn.commit()
        conn.close()
        return True, "Filter deleted"
    except Exception as e:
        return False, str(e)
