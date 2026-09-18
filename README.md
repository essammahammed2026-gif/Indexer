# Universal Document & Records Search Engine (Indexer)

A lightweight, zero-external-pip-dependency desktop search platform and web GUI built using Python's standard library (`http.server`, `sqlite3`, `zipfile`, `xml.etree`) and native system utilities (`pdftotext`, `pdftoppm`, `tesseract`, `LibreOffice`).

Designed for rapid investigative discovery across mixed collections: Telecom CDR spreadsheets (`.xlsx`, `.xls`, `.csv`), documents (`.docx`, `.odt`, `.txt`, `.pdf`), and scanned image attachments (`.png`, `.jpg`, `.jpeg`).

---

## 🌟 Key Features

### 1. Dual-Engine Hybrid Search
- **Structured CDR Records Search:** Normalized search across calling/called parties (`target_msisdn`, `other_msisdn`), dates, call direction, durations, tower cell IDs, site addresses, and party names.
- **Universal SQLite FTS5 Full-Text Search:** Full-text indexing of all cells, sentences, paragraphs, and raw streams for generic documents, unmapped sheets, logs, and scanned text.

### 2. Universal Document & OCR Ingestion
- **Formats Supported:** `.xlsx`, `.xls`, `.csv`, `.tsv`, `.docx`, `.odt`, `.txt`, `.log`, `.json`, `.sql`, `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp`.
- **Scanned PDF Fallback:** Automatically detects scanned PDFs via `pdftotext`; if text content is sparse (< 50 characters), renders pages via `pdftoppm` and runs Tesseract OCR (`ara+eng`).
- **Context Window Preview (±3 Lines):** In-app popup (`📄 Context`) that displays surrounding rows/lines with the matched keyword highlighted in real time.

### 3. Egyptian & Arabic Phonetic Normalization
- Normalizes compound names and prefixes: `عبد الرحمن` $\leftrightarrow$ `عبدالرحمن`, `أبو الفتوح` $\leftrightarrow$ `ابوالفتوح`.
- Unifies Hamza variations (`أ`, `إ`, `آ` $\rightarrow$ `ا`), Teh Marbuta (`ة` $\rightarrow$ `ه`), Alef Maksura (`ى` $\rightarrow$ `ي`), strips Tashkeel, and handles Egyptian phonetic tokens (`عمرو` $\rightarrow$ `عمر`).
- Full normalization on phone numbers: Handles `+20`, `20`, leading `0`, floating decimals (`.0`), and dashes/spaces.

### 4. Live Background Directory Watcher & Parallel Indexing
- Continuously scans and indexes new or modified files dropped into the selected folder (`folder_watcher_loop`).
- Multi-core indexing using Python's `ThreadPoolExecutor` for parallel document parsing with sequential transactional SQLite commits.

### 5. Custom Quick Filters & Bookmarking
- **User-Defined Filters:** Saved directly in `sheets_index.db` in the `quick_filters` table—no hardcoded default filters.
- **Record Bookmarks & Leads:** Classify records as 🌟 *Key Lead*, 🚨 *Target / Suspect*, ✅ *Reviewed*, or ❌ *False Positive* with custom investigative notes.

### 6. Interactive Web GUI & Direct File Launch
- Single-page responsive interface at `http://localhost:8088`.
- **`🚀 Open Row`**: Directly launches LibreOffice Calc or default app positioned at the exact sheet and row matched.
- **`📂 Folder`**: Reveals containing directory in file manager (`xdg-open`).
- Database Export / Import and CSV export directly from the browser.
- Rotating daily safety snapshots (`sheets_index.db.snap_YYYYMMDD`).

---

## 🏛️ Architecture & File Structure

```
Indexer/
├── app.py               # Main web application, HTTP server, REST API, GUI & watcher thread
├── indexer_engine.py    # Document parsing engine, FTS5 indexer, OCR runner & DB schema
├── index_sheets.py      # Standalone CLI batch indexing script
├── search.py            # Standalone CLI query utility
├── config.json          # Persistent user configuration (watched folder & active status)
├── sheets_index.db      # SQLite WAL database (FTS5 + CDR + Filters + Bookmarks)
├── tessdata/            # Local Tesseract traineddata language models (ara, eng, osd)
└── .gitignore           # Excludes databases, WAL files, backups, and large traineddata
```

### Database Schema (`sheets_index.db`)
- **`files`**: `(file_id, file_path, filename, folder, indexed_at)`
- **`cdr_records`**: `(id, file_id, sheet_name, row_idx, target_msisdn, target_norm, other_msisdn, other_norm, other_name, other_name_norm, event_time, duration, direction, other_id, other_address, cell_id, cell_address, raw_row)`
- **`universal_search` (FTS5)**: `(file_path UNINDEXED, sheet_name UNINDEXED, row_idx UNINDEXED, content)`
- **`quick_filters`**: `(id, name, query, created_at)`
- **`bookmarks`**: `(id, file_path, sheet_name, row_idx, tag, notes, created_at)`

---

## 🚀 Running the App

### Start Web Server:
```bash
python3 -u app.py
```
Open browser at: **`http://localhost:8088`**

### CLI Search:
```bash
python3 search.py "01002407192"
python3 search.py "سوزان" --open
```

### CLI Batch Index:
```bash
python3 index_sheets.py /path/to/documents
```
