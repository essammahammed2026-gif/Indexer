#!/usr/bin/env python3
"""
Indexer Engine - High-throughput document and spreadsheet indexer.
Integrates parsing/ pipelines, core normalizers, and storage DAL.
Zero external dependencies (Python standard library only).
"""

import os
import re
import json
import sqlite3
from core.normalizers import normalize_phone, normalize_arabic
import storage
import parsing

# Backward-compatibility exports
col_letters_to_num = parsing.col_letters_to_num
parse_xlsx = parsing.parse_xlsx
parse_csv = parsing.parse_csv
parse_docx = parsing.parse_docx
parse_odt = parsing.parse_odt
parse_txt = parsing.parse_txt
parse_pdf = parsing.parse_pdf
parse_image = parsing.parse_image
parse_xls = parsing.parse_xls
parse_document = parsing.parse_document
parse_workbook = parsing.parse_document
run_ocr = parsing.run_ocr
run_ocr_detailed = parsing.run_ocr_detailed
get_image_dimensions = parsing.get_image_dimensions
preprocess_image = parsing.preprocess_image

# Delegate schema initialization & change logging to storage DAL
init_db = storage.init_tables

def record_change_event(conn, event_type, file_path, old_path=None, records_count=0, details=""):
    """Compatibility bridge for logging change events with an active connection."""
    try:
        cur = conn.cursor()
        fname = os.path.basename(file_path) if file_path else ""
        cur.execute("""
        INSERT INTO change_events (event_type, file_path, old_path, filename, records_count, details, is_read)
        VALUES (?, ?, ?, ?, ?, ?, 0);
        """, (event_type, file_path, old_path, fname, records_count, details))
        conn.commit()
        return True
    except Exception as e:
        print(f"[CHANGE EVENT LOG ERROR] {e}")
        return False

def _extract_cell_value(header_map, row, key):
    """Efficient cell extraction without per-row nested function closures."""
    for k, idx in header_map.items():
        if key in k and idx < len(row):
            val = row[idx]
            if val is not None and str(val).strip():
                return val
    return None

def process_file(fpath, conn):
    """
    Ingest a single document/spreadsheet/image into the active database.
    Updates files, cdr_records, universal_search, and ocr_boxes tables in a transaction.
    """
    cur = conn.cursor()
    folder, filename = os.path.split(fpath)
    cur.execute("INSERT OR IGNORE INTO files (file_path, filename, folder) VALUES (?, ?, ?);", (fpath, filename, folder))
    cur.execute("SELECT file_id FROM files WHERE file_path = ?;", (fpath,))
    file_id = cur.fetchone()[0]

    # Delete previous entries if any
    cur.execute("DELETE FROM cdr_records WHERE file_id = ?;", (file_id,))
    cur.execute("DELETE FROM universal_search WHERE file_path = ?;", (fpath,))
    cur.execute("DELETE FROM ocr_boxes WHERE file_path = ?;", (fpath,))

    all_rows = []
    ext = os.path.splitext(fpath)[1].lower()

    if ext in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'):
        text, boxes = parsing.run_ocr_detailed(fpath)
        w, h = parsing.get_image_dimensions(fpath)
        if boxes:
            cur.execute("""
            INSERT INTO ocr_boxes (file_path, sheet_name, img_width, img_height, boxes_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_path, sheet_name) DO UPDATE SET
                img_width = excluded.img_width,
                img_height = excluded.img_height,
                boxes_json = excluded.boxes_json;
            """, (fpath, 'Image', w, h, json.dumps(boxes, ensure_ascii=False)))
        if text:
            for idx, line in enumerate(text.splitlines(), start=1):
                line_s = line.strip()
                if line_s:
                    all_rows.append(('Image', idx, [line_s]))
    elif ext == '.pdf':
        pdf_res = parsing.parse_pdf(fpath)
        if isinstance(pdf_res, tuple):
            all_rows, pdf_boxes = pdf_res
            for sname, (w, h, boxes) in pdf_boxes.items():
                if boxes:
                    cur.execute("""
                    INSERT INTO ocr_boxes (file_path, sheet_name, img_width, img_height, boxes_json)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(file_path, sheet_name) DO UPDATE SET
                        img_width = excluded.img_width,
                        img_height = excluded.img_height,
                        boxes_json = excluded.boxes_json;
                    """, (fpath, sname, w, h, json.dumps(boxes, ensure_ascii=False)))
        else:
            all_rows = pdf_res
    else:
        all_rows = parsing.parse_document(fpath)

    if not all_rows:
        conn.commit()
        return 0

    # Group by sheet/section
    sheets = {}
    for sname, r_idx, row in all_rows:
        sheets.setdefault(sname, []).append((r_idx, row))

    cdr_batch = []
    fts_batch = []

    for sname, sheet_rows in sheets.items():
        # Find headers dynamically across first 25 rows
        header_map = {}
        for r_idx, row in sheet_rows[:25]:
            cleaned_row = [str(c).lower().strip() if c is not None else '' for c in row]
            if any('msisdn' in c or 'target' in c or 'call type' in c or 'called' in c or 'dialed' in c or 'sub_id' in c or 'phone' in c for c in cleaned_row):
                for idx, c in enumerate(cleaned_row):
                    if c:
                        header_map[c] = idx
                break

        for r_idx, row in sheet_rows:
            # Build text string for universal FTS
            row_non_empty = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if not row_non_empty:
                continue
            row_str = " | ".join(row_non_empty)
            fts_batch.append((fpath, sname, r_idx, row_str))

            # CDR extraction
            target_msisdn = None
            other_msisdn = None
            other_name = None
            event_time = None
            duration = None
            direction = None
            other_id = None
            other_address = None
            cell_id = None
            cell_address = None

            if header_map:
                target_msisdn = _extract_cell_value(header_map, row, 'target_msisdn') or _extract_cell_value(header_map, row, 'target') or _extract_cell_value(header_map, row, 'msisdn') or _extract_cell_value(header_map, row, 'a number') or _extract_cell_value(header_map, row, 'dial:')
                other_msisdn = _extract_cell_value(header_map, row, 'other_msisdn') or _extract_cell_value(header_map, row, 'called number') or _extract_cell_value(header_map, row, 'b number') or _extract_cell_value(header_map, row, 'dialed') or _extract_cell_value(header_map, row, 'party') or _extract_cell_value(header_map, row, 'contact')
                other_name = _extract_cell_value(header_map, row, 'other_name') or _extract_cell_value(header_map, row, 'name') or _extract_cell_value(header_map, row, 'first_name')
                event_time = _extract_cell_value(header_map, row, 'event_start_time') or _extract_cell_value(header_map, row, 'call date') or _extract_cell_value(header_map, row, 'full date') or _extract_cell_value(header_map, row, 'date') or _extract_cell_value(header_map, row, 'time')
                duration = _extract_cell_value(header_map, row, 'call_duration') or _extract_cell_value(header_map, row, 'duration') or _extract_cell_value(header_map, row, 'volume')
                direction = _extract_cell_value(header_map, row, 'event_direction') or _extract_cell_value(header_map, row, 'call type') or _extract_cell_value(header_map, row, 'direction') or _extract_cell_value(header_map, row, 'call identity')
                other_id = _extract_cell_value(header_map, row, 'other_id') or _extract_cell_value(header_map, row, 'sub_id_val') or _extract_cell_value(header_map, row, 'id no') or _extract_cell_value(header_map, row, 'national')
                other_address = _extract_cell_value(header_map, row, 'other_address') or _extract_cell_value(header_map, row, 'street') or _extract_cell_value(header_map, row, 'neighborhood') or _extract_cell_value(header_map, row, 'district')
                cell_id = _extract_cell_value(header_map, row, 'cell_nid') or _extract_cell_value(header_map, row, 'cell location') or _extract_cell_value(header_map, row, 'cell')
                cell_address = _extract_cell_value(header_map, row, 'cell_address') or _extract_cell_value(header_map, row, 'site') or _extract_cell_value(header_map, row, 'governorate')

            # Fallback heuristic: If columns weren't mapped or header_map didn't match, inspect values directly
            if not target_msisdn or not other_msisdn:
                phones_found = []
                for c in row:
                    p = normalize_phone(c)
                    if p:
                        phones_found.append((str(c), p))
                if len(phones_found) >= 2:
                    if not target_msisdn:
                        target_msisdn, _ = phones_found[0]
                    if not other_msisdn:
                        other_msisdn, _ = phones_found[1]
                elif len(phones_found) == 1 and not other_msisdn:
                    other_msisdn, _ = phones_found[0]

            # Normalize values
            t_norm = normalize_phone(target_msisdn)
            o_norm = normalize_phone(other_msisdn)
            on_norm = normalize_arabic(str(other_name)) if other_name else None

            if t_norm or o_norm or other_name or other_id:
                cdr_batch.append((
                    file_id, sname, r_idx,
                    str(target_msisdn) if target_msisdn is not None else None,
                    t_norm,
                    str(other_msisdn) if other_msisdn is not None else None,
                    o_norm,
                    str(other_name) if other_name is not None else None,
                    on_norm,
                    str(event_time) if event_time is not None else None,
                    str(duration) if duration is not None else None,
                    str(direction) if direction is not None else None,
                    str(other_id) if other_id is not None else None,
                    str(other_address) if other_address is not None else None,
                    str(cell_id) if cell_id is not None else None,
                    str(cell_address) if cell_address is not None else None,
                    row_str
                ))

    if cdr_batch:
        cur.executemany("""
        INSERT INTO cdr_records (
            file_id, sheet_name, row_idx,
            target_msisdn, target_norm, other_msisdn, other_norm,
            other_name, other_name_norm, event_time, duration,
            direction, other_id, other_address, cell_id, cell_address, raw_row
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, cdr_batch)

    if fts_batch:
        cur.executemany("""
        INSERT INTO universal_search (file_path, sheet_name, row_idx, content)
        VALUES (?, ?, ?, ?);
        """, fts_batch)

    cur.execute("UPDATE files SET indexed_at = CURRENT_TIMESTAMP WHERE file_id = ?;", (file_id,))
    conn.commit()
    return len(fts_batch)
