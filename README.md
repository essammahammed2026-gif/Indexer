# OmniSearch (Universal Document & Records Search Platform)

A high-performance, lightweight, zero-external-pip-dependency investigative search platform, OCR inspection studio, and web GUI. Built strictly with Python's standard library (`http.server`, `sqlite3`, `zipfile`, `xml.etree`, `multiprocessing`/`concurrent.futures`) and native Linux system utilities (`pdftotext`, `pdftoppm`, `tesseract-ocr`, `ImageMagick`, `zenity`, `LibreOffice`).

Engineered for rapid, sub-second discovery across massive mixed investigative archives: Telecom CDR call spreadsheets (`.xlsx`, `.xls`, `.csv`), formal dossiers (`.docx`, `.odt`, `.txt`, `.pdf`), and scanned image attachments (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp`).

---

## 🏗️ System Architecture

```
                               ┌────────────────────────────────┐
                               │   Web UI & OCR Studio (8088)   │
                               │   Vanilla JS Single Page App   │
                               └──────────────┬─────────────────┘
                                              │ HTTP / JSON API
                                              ▼
                               ┌────────────────────────────────┐
                               │             app.py             │
                               │  - Custom HTTP & REST Server   │
                               │  - Multi-Database Switching    │
                               │  - Native Zenity Dialog Pickers│
                               │  - Live Folder Watcher Daemon  │
                               │  - Parallel Ingestion Workers  │
                               └───────┬────────────────┬───────┘
                                       │                │
                   Direct SQL Queries  │                │ Ingestion & OCR Calls
                                       ▼                ▼
            ┌─────────────────────────────┐    ┌─────────────────────────────┐
            │   Dedicated Storage Dir     │    │      indexer_engine.py      │
            │  - External / Custom Volume │◄───┤  - Document Stream Parsers  │
            │  - SQLite 3 (WAL Mode)      │    │  - Arabic & Phone Normalizer│
            │  - `cdr_records` Table      │    │  - ImageMagick & Tesseract  │
            │  - `universal_search` (FTS5)│    │  - Parallel Batch Indexer   │
            │  - Point-in-Time Snapshots  │    └─────────────────────────────┘
            └─────────────────────────────┘                   ▲
                                                              │
                                            ┌─────────────────┴─────────────┐
                                            │      Files & Data Sources     │
                                            │  - Excel (.xlsx, .xls)        │
                                            │  - Delimited (.csv, .tsv)     │
                                            │  - Word & Text (.docx, .txt)  │
                                            │  - PDF (text & scanned OCR)   │
                                            │  - Images (png, jpg, tiff)    │
                                            └───────────────────────────────┘
```

---

## 🌟 Key Capabilities

### 1. Multi-Database Architecture & Dedicated Storage Directory
- **Custom / External Volume Storage:** All created index database files (`.db`, `-wal`, `-shm`) and daily snapshots are stored in the user-selected database directory outside the codebase.
- **Dynamic Database Profiles & Switching:** Seamlessly register, nickname, switch, and delete multiple independent indexes directly from the top navigation bar or settings menu.
- **Clean Initial State & Fallback-Free Launch:** The application starts with no database loaded until chosen by the user. If first launch or if the application is reset, the setup wizard prompts the user to select the storage folder.
- **Application Reset Wizard:** Completely clears watcher state, preferences, and database profiles without deleting physical database files on disk.

### 2. Search Modes & Precision Filename Filtering
- **General Search Mode (Default):** Document-first discovery across all archives, PDFs, Word documents, text notes, OCR scanned documents, and spreadsheets. Powered by SQLite FTS5 full-text indexing with BM25 relevancy ranking and compound trigram tokenization.
- **File Names Only Filter:** Instant toggle via the **"📁 File Names Only"** pill or using the `file:` / `filename:` query operator (e.g. `file:Ayman` or `file:"Report 2021" ext:xlsx`) to search exclusively across file paths and filenames while skipping body text.
- **Telecom CDR Mode:** Investigative phone & call records explorer. Provides structured queries across calling/called parties (`target_msisdn`, `other_msisdn`), timestamps, call direction, duration, tower cell IDs, site addresses, and contact names.
- **Dynamic Views:** Instantly toggle between Rich Document Cards, Dense Tabular Grids, and Group-by-File aggregations.

### 3. Trigram Substring, Fuzzy & Partial Number Engine
- **Trigram Tokenizer:** Powered by SQLite FTS5 `trigram` tokenization. Searching for any 3+ letter fragment (such as `manial`) automatically matches inside compound words and joined tokens like `newmanial`, `NEWMANIAL/37460`, and `el-manial`.
- **Partial Phone Number Lookup:** Searching partial digit fragments (e.g. `989378` or `01017`) finds all call records and document mentions regardless of international prefix (`+20`, `0020`, `20`) or placement.
- **Fuzzy / Levenshtein Distance Typo Tolerance:** Built-in standard-library Levenshtein distance fallback allows finding names and keywords even when slightly misspelled or transposed.

### 4. High-Precision Arabic & Phone Normalization
- **Egyptian & Arabic Orthographic & Phonetic Rules:**
  - Unifies Hamza forms (`أ`, `إ`, `آ` $\rightarrow$ `ا`), Teh Marbuta (`ة` $\rightarrow$ `ه`), and Alef Maksura (`ى` $\rightarrow$ `ي`).
  - Strips Arabic Tashkeel/diacritics (`[\u064B-\u0652\u0640]`).
  - Merges compound prefixes (`عبد الرحمن` $\leftrightarrow$ `عبدالرحمن`, `أبو الفتوح` $\leftrightarrow$ `ابوالفتوح`).
  - Reconciles colloquial phonetic tokens (e.g., silent waw in `عمرو` $\leftrightarrow$ `عمر`).
- **Standardized Phone Cleaning:**
  - Cleans Egyptian country codes (`+20`, `0020`, `20`), handles floating point artifacts (`.0`), strips spaces/dashes, and formats standard 11-digit mobile strings (`010...`, `011...`, `012...`, `015...`).

### 5. Universal Document Parsers & Zero-PIP Dependency
- **Pure Python OpenXML Streamer (`.xlsx`):** Parses `sharedStrings.xml` and worksheet XMLs using `zipfile` and `xml.etree.ElementTree.iterparse` without installing `openpyxl`.
- **Legacy Excel (`.xls`):** Headless LibreOffice conversion to CSV, with automatic fallback to raw binary stream string extraction.
- **Word Processing (`.docx`, `.odt`):** Native extraction from XML structures.
- **PDF & Scanned Fallback:** Extracts embedded text via `pdftotext`. When text length is sparse (< 50 characters), automatically triggers page rasterization via `pdftoppm -r 150` followed by Tesseract OCR (`ara+eng`).

### 6. Interactive OCR Image Studio & Coordinate Mapping
- **Image Pre-Processing Pipeline:** Enhances images with ImageMagick (`-colorspace gray`, `-auto-level`, `-contrast-stretch 1%x1%`, `-deskew 40%`, `-sharpen 0x1`) before OCR.
- **Bounding Box Coordinate Extraction:** Runs Tesseract with `-c tessedit_create_tsv=1` to record token positions (`left`, `top`, `width`, `height`, `conf`) in the `ocr_boxes` database table.
- **Visual Overlay Modal (`🖼️ View Image`):** Displays scaled interactive overlays over images, highlights search query matches, provides real-time transparent text selection for direct dragging, and includes a 1-click text inspector panel.

### 7. Database Maintenance, Snapshots & One-Click Compaction
- **Safety Snapshots (`.db.snap_YYYYMMDD`):** Flushes WAL transactions and creates full point-in-time database clones in your storage directory.
- **One-Click Compaction & Optimization:** Flushes WAL transactions, executes SQLite `VACUUM` and `PRAGMA optimize` to reclaim hundreds of megabytes of deleted/freelist pages and defragment search tables directly from the Tools menu and Settings dialog.
- **Live Background Directory Watcher:** Automatic background polling with configurable intervals, settle debouncing, and temporary file filters (`~$*`, `.*`).
- **Skipped Files Diagnostics Log:** Records any unreadable, password-protected, or corrupted files encountered during indexing.

---

## 📁 Repository Structure & Roles

| File / Folder | Role & Description |
| :--- | :--- |
| [`app.py`](file:///home/essam/Projects/Indexer/app.py) | **Minimal Server Entry Point** (< 80 lines): Loads configuration, launches background directory watcher thread, and bootstraps HTTP server with graceful shutdown handlers. |
| [`parsing/`](file:///home/essam/Projects/Indexer/parsing) | **Document & Records Parsers**: Decoupled zero-dependency parsing engine for Excel (`.xlsx`, `.xls`), delimited files (`.csv`, `.tsv`), Word (`.docx`, `.odt`), text/logs (`.txt`), PDFs, and OCR image pipelines. |
| [`core/`](file:///home/essam/Projects/Indexer/core) | **Pure Domain Logic**: Egyptian Arabic normalizer (`normalizers.py`), phone number formatters, Google-style query parser (`query_parser.py`), and Linux OS launchers (`system_interop.py`). |
| [`storage/`](file:///home/essam/Projects/Indexer/storage) | **Data Access Layer**: Multi-database SQLite routing (`database.py`), high-performance FTS5 trigram search queries (`search_repository.py`), bookmarks (`bookmarks.py`), and snapshot/optimization events (`events.py`). |
| [`services/`](file:///home/essam/Projects/Indexer/services) | **Background Services & State**: Thread-safe indexing state manager (`state.py`), parallel directory crawler (`indexer_service.py`), and live file system watcher daemon (`watcher_service.py`). |
| [`web/`](file:///home/essam/Projects/Indexer/web) | **HTTP Transport Layer**: Clean URL router (`router.py`), unified JSON/HTTP serialization helpers (`http_utils.py`), and discrete endpoint handlers in `web/handlers/`. |
| [`templates/`](file:///home/essam/Projects/Indexer/templates) | **Frontend Templates**: Clean HTML5 document shell (`index.html`) linking dark-mode styling, tabbed settings dialog, and single-page application logic. |
| [`static/`](file:///home/essam/Projects/Indexer/static) | **Static UI Assets**: Standalone stylesheet (`css/app.css`) and client-side reactive interface script (`js/app.js`). |
| [`indexer_engine.py`](file:///home/essam/Projects/Indexer/indexer_engine.py) | **Ingestion Coordinator**: Orchestrates file discovery, column mapping, OCR coordinate extraction, and SQLite batch transactions. |
| [`index_sheets.py`](file:///home/essam/Projects/Indexer/index_sheets.py) | **Batch Ingestion CLI**: Command-line tool to index an entire folder or individual files recursively with progress statistics. |
| [`search.py`](file:///home/essam/Projects/Indexer/search.py) | **Terminal Search CLI**: Fast CLI query utility to search phone numbers, names, IDs, or text keywords directly from bash, with `--open` flag for LibreOffice Calc. |
| [`config.json`](file:///home/essam/Projects/Indexer/config.json) | **Runtime Configuration**: Persists active database key, database storage folder, registered databases, nicknames, and fine-tuned watcher settings. |
| [`tessdata/`](file:///home/essam/Projects/Indexer/tessdata) | Optional local Tesseract language models (`ara.traineddata`, `eng.traineddata`, `osd.traineddata`). |

---

## 🗄️ Database Schema & Storage Layout

Database files run in WAL (`Write-Ahead Logging`) mode with `synchronous = NORMAL` for non-blocking concurrent reads during background commits.

```sql
-- 1. Tracked Files Catalog
CREATE TABLE files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE,
    filename TEXT,
    folder TEXT,
    file_mtime REAL DEFAULT 0,
    file_size INTEGER DEFAULT 0,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Structured Telecom Records (CDR)
CREATE TABLE cdr_records (
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
CREATE INDEX idx_cdr_target_norm ON cdr_records(target_norm);
CREATE INDEX idx_cdr_other_norm ON cdr_records(other_norm);
CREATE INDEX idx_cdr_other_name_norm ON cdr_records(other_name_norm);
CREATE INDEX idx_cdr_file_id ON cdr_records(file_id);

-- 3. Universal Full-Text Search (FTS5 with Trigram Tokenizer)
CREATE VIRTUAL TABLE universal_search USING fts5(
    file_path UNINDEXED,
    sheet_name UNINDEXED,
    row_idx UNINDEXED,
    content,
    tokenize = 'trigram'
);

-- 4. User Quick Filters
CREATE TABLE quick_filters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Investigative Bookmarks
CREATE TABLE bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    row_idx INTEGER NOT NULL,
    tag TEXT DEFAULT 'Lead',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_path, sheet_name, row_idx)
);

-- 6. OCR Coordinate Boxes
CREATE TABLE ocr_boxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    img_width INTEGER,
    img_height INTEGER,
    boxes_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_path, sheet_name)
);

-- 7. Audit & Sync Change Events
CREATE TABLE change_events (
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

-- 8. Skipped & Unreadable Files Diagnostic Log
CREATE TABLE skipped_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE,
    filename TEXT,
    folder TEXT,
    reason TEXT,
    error_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🚀 Quick Start & Usage

### 1. Launch Web Server & UI
```bash
python3 -u app.py
```
Open your browser at: **`http://localhost:8088`**

### 2. Search Syntax Examples
You can type search queries freely or combine Google-style operators:
```text
# Exact phrase in quotes
"contract agreement"

# Negative term exclusion
Ayman -Vodafone

# File name only search
file:Ayman
filename:"Audit Report"

# File extension filter
ext:pdf
filetype:xlsx

# Phone number operator
phone:01012345678

# Folder / Directory scope
folder:"Cairo Cases"
```

### 3. Command-Line Search
```bash
# Search phone number or prefix
python3 search.py "01002407192"
python3 search.py --prefix "015"

# Search Arabic contact name
python3 search.py "سوزان"

# Search and directly launch matched row in LibreOffice Calc
python3 search.py "01123456789" --open
```

### 4. Batch Indexing via CLI
```bash
# Index a directory of spreadsheets and documents
python3 index_sheets.py /path/to/investigative/archive
```

### 5. Database Maintenance & Compaction
- **Via UI:** Click **Tools ▾ ➔ Compact & Optimize Database** or use **Settings ➔ Maintenance & Reset**.
- **Via CLI / Terminal:**
  ```bash
  # Check integrity and flush WAL
  sqlite3 "/path/to/database.db" "PRAGMA integrity_check; PRAGMA wal_checkpoint(TRUNCATE); VACUUM; PRAGMA optimize;"
  ```

---

## 🛠️ System Prerequisites

Indexer relies on standard Linux utilities rather than bloated Python libraries:
- **Python 3.10+** (Standard Library only)
- **Tesseract OCR:** `sudo pacman -S tesseract tesseract-data-ara tesseract-data-eng` (or `apt install tesseract-ocr tesseract-ocr-ara`)
- **Poppler Utilities (PDF):** `sudo pacman -S poppler` (for `pdftotext`, `pdftoppm`)
- **ImageMagick:** `sudo pacman -S imagemagick` (for `magick`)
- **Native File Choosers:** `zenity` or `kdialog`
- **Spreadsheet Viewer:** `libreoffice-fresh` or `libreoffice-still`
