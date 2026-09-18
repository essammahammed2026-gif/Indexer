#!/usr/bin/env python3
"""
Indexer Engine - Zero external dependencies.
Supports .xlsx (via zipfile + xml.etree), .csv, and standard telecom CDR parsing.
"""
import os
import re
import csv
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheets_index.db")
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

def normalize_phone(val):
    if val is None:
        return None
    if isinstance(val, float) and val.is_integer():
        val = int(val)
    s = str(val).strip()
    if s.endswith('.0') and s[:-2].replace('-', '').replace('+', '').isdigit():
        s = s[:-2]
    digits = re.sub(r'\D', '', s)
    if digits.startswith('20') and len(digits) in (12, 13, 14):
        if len(digits) == 12:
            return '0' + digits[2:]
    if len(digits) == 10 and digits[0] == '1':
        return '0' + digits
    if len(digits) == 11 and digits.startswith('01'):
        return digits
    return None

def normalize_arabic(text):
    if not text:
        return ""
    text = re.sub(r'[إأآا]', 'ا', str(text))
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'ى', 'ي', text)
    return text.strip()

def init_db(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")
    
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

    cur.execute("CREATE INDEX IF NOT EXISTS idx_cdr_target_norm ON cdr_records(target_norm);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cdr_other_norm ON cdr_records(other_norm);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cdr_other_name ON cdr_records(other_name_norm);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cdr_other_id ON cdr_records(other_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cdr_event_time ON cdr_records(event_time);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cdr_file_sheet_row ON cdr_records(file_id, sheet_name, row_idx);")

    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS universal_search USING fts5(
        file_path UNINDEXED,
        sheet_name UNINDEXED,
        row_idx UNINDEXED,
        content,
        tokenize='unicode61'
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
    conn.commit()

def col_letters_to_num(col_str):
    num = 0
    for c in col_str:
        if 'A' <= c.upper() <= 'Z':
            num = num * 26 + (ord(c.upper()) - ord('A')) + 1
    return num

def parse_xlsx(fpath):
    """
    Parse .xlsx workbook using standard library zipfile + xml.etree.ElementTree.
    Returns generator/list of (sheet_name, row_idx, row_values).
    """
    rows_data = []
    try:
        with zipfile.ZipFile(fpath, 'r') as z:
            namelist = z.namelist()
            # 1. Load shared strings
            shared_strings = []
            if 'xl/sharedStrings.xml' in namelist:
                tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
                for si in tree.iter(f'{NS}si'):
                    text_parts = [t.text for t in si.iter(f'{NS}t') if t.text]
                    shared_strings.append(''.join(text_parts))

            # 2. Get sheet names and targets
            wb_tree = ET.fromstring(z.read('xl/workbook.xml'))
            sheet_map = [] # [(name, path_in_zip)]
            
            # Map rIds from rels
            rels_map = {}
            if 'xl/_rels/workbook.xml.rels' in namelist:
                rels_tree = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
                rel_ns = '{http://schemas.openxmlformats.org/package/2006/relationships}'
                for rel in rels_tree.iter(f'{rel_ns}Relationship'):
                    r_id = rel.attrib.get('Id')
                    target = rel.attrib.get('Target', '')
                    if not target.startswith('xl/'):
                        target = 'xl/' + target.lstrip('/')
                    rels_map[r_id] = target

            for sheet_elem in wb_tree.iter(f'{NS}sheet'):
                name = sheet_elem.attrib.get('name')
                r_id = sheet_elem.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                sheet_target = rels_map.get(r_id, f'xl/worksheets/sheet{len(sheet_map)+1}.xml')
                sheet_map.append((name, sheet_target))

            # 3. Parse each sheet
            for sheet_name, sheet_xml_path in sheet_map:
                if sheet_xml_path not in namelist:
                    continue
                with z.open(sheet_xml_path) as sheet_file:
                    row_counter = 0
                    for event, elem in ET.iterparse(sheet_file, events=('end',)):
                        if elem.tag.endswith('row'):
                            r_idx = int(elem.attrib.get('r', row_counter + 1))
                            row_counter = r_idx
                            cell_dict = {}
                            max_col = 0
                            for c in elem.findall(f'{NS}c'):
                                r_ref = c.attrib.get('r', '')
                                col_letters = ''.join([ch for ch in r_ref if ch.isalpha()])
                                col_idx = col_letters_to_num(col_letters) if col_letters else (max_col + 1)
                                max_col = max(max_col, col_idx)
                                
                                cell_type = c.attrib.get('t')
                                v = c.find(f'{NS}v')
                                val = None
                                if cell_type == 's' and v is not None and v.text and v.text.isdigit():
                                    idx = int(v.text)
                                    if 0 <= idx < len(shared_strings):
                                        val = shared_strings[idx]
                                elif cell_type == 'inlineStr':
                                    t = c.find(f'{NS}is/{NS}t')
                                    if t is not None:
                                        val = t.text
                                elif v is not None and v.text:
                                    val = v.text
                                
                                if val is not None:
                                    cell_dict[col_idx] = val
                            
                            if cell_dict:
                                row_list = [cell_dict.get(i, '') for i in range(1, max_col + 1)]
                                if any(str(x).strip() for x in row_list):
                                    rows_data.append((sheet_name, r_idx, row_list))
                            elem.clear()
    except Exception as e:
        print(f"Error reading xlsx {fpath}: {e}")
    return rows_data

def parse_csv(fpath):
    rows_data = []
    encodings = ['utf-8', 'cp1256', 'latin-1']
    for enc in encodings:
        try:
            with open(fpath, 'r', encoding=enc, errors='replace') as f:
                reader = csv.reader(f)
                for r_idx, row in enumerate(reader, start=1):
                    if any(c and str(c).strip() for c in row):
                        rows_data.append(('Sheet1', r_idx, row))
            break
        except Exception:
            continue
    return rows_data

def parse_docx(fpath):
    rows_data = []
    try:
        with zipfile.ZipFile(fpath, 'r') as z:
            if 'word/document.xml' in z.namelist():
                tree = ET.fromstring(z.read('word/document.xml'))
                w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                p_idx = 1
                for p in tree.iter(f'{w_ns}p'):
                    texts = [t.text for t in p.iter(f'{w_ns}t') if t.text]
                    if texts:
                        line = "".join(texts).strip()
                        if line:
                            rows_data.append(('Doc', p_idx, [line]))
                            p_idx += 1
    except Exception as e:
        print(f"[DOCX ERROR] {fpath}: {e}")
    return rows_data

def parse_odt(fpath):
    rows_data = []
    try:
        with zipfile.ZipFile(fpath, 'r') as z:
            if 'content.xml' in z.namelist():
                tree = ET.fromstring(z.read('content.xml'))
                text_ns = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
                p_idx = 1
                for p in tree.iter(f'{text_ns}p'):
                    txt = "".join(list(p.itertext())).strip()
                    if txt:
                        rows_data.append(('Doc', p_idx, [txt]))
                        p_idx += 1
    except Exception as e:
        print(f"[ODT ERROR] {fpath}: {e}")
    return rows_data

def parse_txt(fpath):
    rows_data = []
    encodings = ['utf-8', 'cp1256', 'latin-1']
    for enc in encodings:
        try:
            with open(fpath, 'r', encoding=enc, errors='replace') as f:
                for line_idx, line in enumerate(f, start=1):
                    line_s = line.strip()
                    if line_s:
                        rows_data.append(('Text', line_idx, [line_s]))
            break
        except Exception:
            continue
    return rows_data

def parse_pdf(fpath):
    rows_data = []
    try:
        import subprocess
        res = subprocess.run(
            ['pdftotext', '-layout', fpath, '-'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15
        )
        text = res.stdout.decode('utf-8', errors='ignore')
        for idx, line in enumerate(text.splitlines(), start=1):
            line_s = line.strip()
            if line_s:
                rows_data.append(('Page', idx, [line_s]))
    except Exception as e:
        print(f"[PDF ERROR] {fpath}: {e}")
    return rows_data

def parse_xls(fpath):
    # 1. Try xlrd if installed
    try:
        import xlrd
        wb = xlrd.open_workbook(fpath, formatting_info=False)
        rows_data = []
        for sname in wb.sheet_names():
            sheet = wb.sheet_by_name(sname)
            for r_idx in range(sheet.nrows):
                row = sheet.row_values(r_idx)
                if any(c is not None and str(c).strip() for c in row):
                    rows_data.append((sname, r_idx + 1, row))
        return rows_data
    except Exception:
        pass

    # 2. Try headless LibreOffice conversion to CSV
    try:
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = ["libreoffice", "--headless", "--convert-to", "csv", "--outdir", tmpdir, fpath]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            outfiles = [f for f in os.listdir(tmpdir) if f.endswith('.csv')]
            if outfiles:
                csv_p = os.path.join(tmpdir, outfiles[0])
                return parse_csv(csv_p)
    except Exception as e:
        print(f"[XLS CONVERT ERROR] {fpath}: {e}")

    # 3. Fallback: Raw string extraction from binary XLS stream
    rows_data = []
    try:
        with open(fpath, "rb") as fp:
            raw = fp.read()
        extracted = []
        # Find printable ascii or arabic-like utf-16/ascii sequences
        import re
        for m in re.finditer(b"[ -~]{4,}", raw):
            s = m.group(0).decode("ascii", errors="ignore").strip()
            if s and not s.startswith("Microsoft"):
                extracted.append(s)
        if extracted:
            for idx, text_seg in enumerate(extracted, start=1):
                rows_data.append(('RawStream', idx, [text_seg]))
    except Exception:
        pass
    return rows_data

def parse_document(fpath):
    ext = os.path.splitext(fpath)[1].lower()
    if ext == '.xlsx':
        return parse_xlsx(fpath)
    elif ext in ('.csv', '.tsv'):
        return parse_csv(fpath)
    elif ext == '.xls':
        return parse_xls(fpath)
    elif ext == '.docx':
        return parse_docx(fpath)
    elif ext == '.odt':
        return parse_odt(fpath)
    elif ext in ('.txt', '.log', '.json', '.sql'):
        return parse_txt(fpath)
    elif ext == '.pdf':
        return parse_pdf(fpath)
    return []

# Backward compatible alias
parse_workbook = parse_document

def process_file(fpath, conn):
    cur = conn.cursor()
    folder, filename = os.path.split(fpath)
    cur.execute("INSERT OR IGNORE INTO files (file_path, filename, folder) VALUES (?, ?, ?);", (fpath, filename, folder))
    cur.execute("SELECT file_id FROM files WHERE file_path = ?;", (fpath,))
    file_id = cur.fetchone()[0]

    # Delete previous entries if any
    cur.execute("DELETE FROM cdr_records WHERE file_id = ?;", (file_id,))
    cur.execute("DELETE FROM universal_search WHERE file_path = ?;", (fpath,))

    all_rows = parse_document(fpath)
    if not all_rows:
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
                def get_c(key):
                    for k, idx in header_map.items():
                        if key in k and idx < len(row):
                            val = row[idx]
                            if val is not None and str(val).strip():
                                return val
                    return None

                target_msisdn = get_c('target_msisdn') or get_c('target') or get_c('msisdn') or get_c('a number') or get_c('dial:')
                other_msisdn = get_c('other_msisdn') or get_c('called number') or get_c('b number') or get_c('dialed') or get_c('party') or get_c('contact')
                other_name = get_c('other_name') or get_c('name') or get_c('first_name')
                event_time = get_c('event_start_time') or get_c('call date') or get_c('full date') or get_c('date') or get_c('time')
                duration = get_c('call_duration') or get_c('duration') or get_c('volume')
                direction = get_c('event_direction') or get_c('call type') or get_c('direction') or get_c('call identity')
                other_id = get_c('other_id') or get_c('sub_id_val') or get_c('id no') or get_c('national')
                other_address = get_c('other_address') or get_c('street') or get_c('neighborhood') or get_c('district')
                cell_id = get_c('cell_nid') or get_c('cell location') or get_c('cell')
                cell_address = get_c('cell_address') or get_c('site') or get_c('governorate')

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

    conn.commit()
    return len(fts_batch)

