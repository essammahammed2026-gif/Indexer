"""
Spreadsheet parsing module for .xlsx, .csv, and legacy .xls files.
Uses Python standard library (zipfile, xml.etree, csv) with zero external pip dependencies.
"""

import os
import csv
import zipfile
import subprocess
import tempfile
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

def col_letters_to_num(col_str):
    """Convert Excel column letters (A, B, ..., Z, AA, ...) to 1-based integer index."""
    num = 0
    for c in col_str:
        if 'A' <= c.upper() <= 'Z':
            num = num * 26 + (ord(c.upper()) - ord('A')) + 1
    return num

def parse_xlsx(fpath):
    """
    Parse .xlsx workbook using standard library zipfile + xml.etree.ElementTree.
    Returns list of tuples: (sheet_name, row_idx, row_values).
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
            sheet_map = []
            
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
        print(f"[XLSX ERROR] {fpath}: {e}")
    return rows_data

def parse_csv(fpath):
    """
    Parse .csv or .tsv file with automatic multi-encoding fallback.
    Returns list of tuples: (sheet_name, row_idx, row_values).
    """
    rows_data = []
    encodings = ['utf-8', 'cp1256', 'latin-1']
    for enc in encodings:
        try:
            with open(fpath, 'r', encoding=enc, errors='replace') as f:
                dialect = csv.excel
                # Detect delimiter (e.g. comma vs tab)
                head = f.read(4096)
                f.seek(0)
                if '\t' in head and head.count('\t') > head.count(','):
                    dialect = csv.excel_tab
                reader = csv.reader(f, dialect=dialect)
                for r_idx, row in enumerate(reader, start=1):
                    if any(c and str(c).strip() for c in row):
                        rows_data.append(('Sheet1', r_idx, row))
            break
        except Exception:
            continue
    return rows_data

def parse_xls(fpath):
    """
    Parse legacy binary .xls file:
    1. Try xlrd if installed in environment
    2. Headless LibreOffice conversion to CSV
    3. Binary string extraction fallback
    """
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
        import re
        extracted = []
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
