# Universal Document & Records Search Engine (Indexer)

A lightweight, zero-external-pip-dependency desktop investigative search platform, OCR inspection workbench, and web GUI. Built strictly with Python's standard library (`http.server`, `sqlite3`, `zipfile`, `xml.etree`, `multiprocessing`/`concurrent.futures`) and native Linux system utilities (`pdftotext`, `pdftoppm`, `tesseract-ocr`, `ImageMagick`, `zenity`, `LibreOffice`).

Engineered for rapid discovery across massive mixed investigative archives: Telecom CDR spreadsheets (`.xlsx`, `.xls`, `.csv`), formal dossiers (`.docx`, `.odt`, `.txt`, `.pdf`), and scanned image attachments (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp`).

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
                               │  - Native Zenity Dialog Pickers│
                               │  - Background Folder Watcher   │
                               │  - Parallel Batch Dispatcher   │
                               └───────┬────────────────┬───────┘
                                       │                │
                   Direct SQL Queries  │                │ Ingestion & OCR Calls
                                       ▼                ▼
           ┌─────────────────────────────┐    ┌─────────────────────────────┐
           │       sheets_index.db       │    │      indexer_engine.py      │
           │  - SQLite 3 (WAL Mode)      │◄───┤  - Document Stream Parsers  │
           │  - `cdr_records` Table      │    │  - Arabic & Phone Normalizer│
           │  - `universal_search` (FTS5)│    │  - ImageMagick & Tesseract  │
           │  - `ocr_boxes` & Bookmarks  │    │  - Parallel Batch Indexer   │
           └─────────────────────────────┘    └─────────────────────────────┘
                                                              ▲
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

### 1. Dual-Mode Search Architecture (General Document Search & Telecom CDR Mode)
- **General Search Mode (Default):** Document-first discovery across all archives, PDFs, Word documents, text notes, OCR scanned documents, and spreadsheets. Powered by SQLite FTS5 full-text indexing with BM25 relevancy ranking. Presents clean, modern document result cards with file type badges, directory paths, highlighted snippet excerpts, file sizes, and action shortcuts (`Context`, `Tag`, `Open File`, `Folder`, `Preview`).
- **Telecom / CDR Mode (Optional Toggle):** Investigative phone & call records explorer. Provides structured normalized queries across calling/called parties (`target_msisdn`, `other_msisdn`), timestamps, call direction (`Incoming`/`Outgoing`), duration, tower cell IDs, site addresses, and contact names.
- **Dynamic Views:** Instantly toggle between Rich Document Cards and Dense Tabular Grids adapted for both general research and specialized telecom analysis.

### 2. Trigram Substring, Fuzzy & Partial Number Engine
- **Full Substring & Compound Matching (Trigram Tokenizer):** Powered by SQLite FTS5 `trigram` tokenization. Searching for any 3+ letter fragment (such as `manial`) automatically matches inside compound words and joined tokens like `newmanial`, `NEWMANIAL/37460`, and `el-manial`.
- **Partial Phone Number Lookup:** Searching partial digit fragments (e.g. `989378` or `01017`) finds all call records and document mentions regardless of international prefix (`+20`, `0020`, `20`) or placement.
- **Fuzzy / Levenshtein Distance Typo Tolerance:** Built-in standard-library Levenshtein distance fallback allows finding names and keywords even when slightly misspelled or transposed.

### 3. High-Precision Arabic & Phone Normalization
- **Egyptian & Arabic Orthographic & Phonetic Rules:**
  - Unifies Hamza forms (`أ`, `إ`, `آ` $\rightarrow$ `ا`), Teh Marbuta (`ة` $\rightarrow$ `ه`), and Alef Maksura (`ى` $\rightarrow$ `ي`).
  - Strips Arabic Tashkeel/diacritics (`[\u064B-\u0652\u0640]`).
  - Merges compound prefixes (`عبد الرحمن` $\leftrightarrow$ `عبدالرحمن`, `أبو الفتوح` $\leftrightarrow$ `ابوالفتوح`).
  - Reconciles colloquial phonetic tokens (e.g., silent waw in `عمرو` $\leftrightarrow$ `عمر`).
- **Standardized Phone Cleaning:**
  - Cleans Egyptian country codes (`+20`, `0020`, `20`), handles floating point artifacts (`.0`), strips spaces/dashes, and formats standard 11-digit mobile strings (`010...`, `011...`, `012...`, `015...`).

### 3. Universal Document Parsers & Zero-PIP Dependency
- **Pure Python OpenXML Streamer (`.xlsx`):** Parses `sharedStrings.xml` and worksheet XMLs using `zipfile` and `xml.etree.ElementTree.iterparse` without installing `openpyxl`.
- **Legacy Excel (`.xls`):** Headless LibreOffice conversion to CSV, with automatic fallback to raw binary stream string extraction.
- **Word Processing (`.docx`, `.odt`):** Native extraction from XML structures.
- **PDF & Scanned Fallback:** Extracts embedded text via `pdftotext`. When text length is sparse (< 50 characters), automatically triggers page rasterization via `pdftoppm -r 150` followed by Tesseract OCR (`ara+eng`).

### 4. Interactive OCR Image Studio & Coordinate Mapping
- **Image Pre-Processing Pipeline:** Enhances images with ImageMagick (`-colorspace gray`, `-auto-level`, `-contrast-stretch 1%x1%`, `-deskew 40%`, `-sharpen 0x1`) before OCR.
- **Bounding Box Coordinate Extraction:** Runs Tesseract with `-c tessedit_create_tsv=1` to record token positions (`left`, `top`, `width`, `height`, `conf`) in the `ocr_boxes` database table.
- **Visual Overlay Modal (`🖼️ View Image`):** Displays scaled interactive overlays over images, highlights search query matches, provides real-time transparent text selection for direct dragging, and includes a 1-click text inspector panel.

### 5. Desktop Integration & Investigation Tooling
- **Native OS Dialog Pickers:** Select folders or files via native Linux `zenity` (with fallback to `kdialog` and browser file inputs).
- **Direct App Launch (`🚀 Open Row`):** Opens LibreOffice Calc positioned directly at the exact sheet and row matched.
- **Folder Reveal (`📂 Folder`):** Opens the containing directory in the system file manager (`xdg-open`).
- **Live Background Directory Watcher:** Automatic 3-second background polling for added or modified files with live status indicators.
- **Quick Filters & Bookmarking:** Custom saved search filter pills and investigative tagging (🌟 *Key Lead*, 🚨 *Target*, ✅ *Reviewed*, ❌ *False Positive*).
- **Safety Snapshots:** Automated daily rotating database backups (`sheets_index.db.snap_YYYYMMDD`).

---

## 📁 Repository Structure & Roles

| File / Folder | Role & Description |
| :--- | :--- |
| [`app.py`](file:///home/essam/Projects/Indexer/app.py) | **Primary Web Server & GUI**: Hosts `http.server` on port 8088. Provides search APIs, native dialog triggers, bookmarks, quick filters, DB backup/restore, desktop launchers, OCR inspectors, and folder watcher thread. |
| [`indexer_engine.py`](file:///home/essam/Projects/Indexer/indexer_engine.py) | **Extraction & Normalization Engine**: XML streaming parsers for `.xlsx`, `.docx`, `.odt`, text/CSV extractors, PDF extraction, ImageMagick preprocessing, Tesseract TSV OCR coordinate generator, and SQLite schema initialization. |
| [`index_sheets.py`](file:///home/essam/Projects/Indexer/index_sheets.py) | **Batch Ingestion CLI**: Command-line tool to index an entire folder or individual files recursively with progress statistics. |
| [`search.py`](file:///home/essam/Projects/Indexer/search.py) | **Terminal Search CLI**: Fast CLI query utility to search phone numbers, names, IDs, or text keywords directly from bash, with `--open` flag for LibreOffice Calc. |
| [`config.json`](file:///home/essam/Projects/Indexer/config.json) | **Runtime Configuration**: Persists watched folder path and active toggle state. |
| [`sheets_index.db`](file:///home/essam/Projects/Indexer/sheets_index.db) | **SQLite Production Database**: High-performance SQLite database operating in WAL mode. |
| [`tessdata/`](file:///home/essam/Projects/Indexer/tessdata) | Optional local Tesseract language models (`ara.traineddata`, `eng.traineddata`, `osd.traineddata`). |
| [`.agents/`](file:///home/essam/Projects/Indexer/.agents) | AI Agent rules, coding standards, architecture constraints, and skills. |
| [`.gitignore`](file:///home/essam/Projects/Indexer/.gitignore) | Git exclusions for SQLite databases, WAL files, uploads, and large models. |

---

## 🗄️ Database Schema (`sheets_index.db`)

The database runs in WAL (`Write-Ahead Logging`) journal mode with `synchronous = NORMAL` for non-blocking concurrent reads during background commits.

```sql
-- 1. Tracked Files
CREATE TABLE files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE,
    filename TEXT,
    folder TEXT,
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

-- 3. Universal Full-Text Search (FTS5)
CREATE VIRTUAL TABLE universal_search USING fts5(
    file_path UNINDEXED,
    sheet_name UNINDEXED,
    row_idx UNINDEXED,
    content,
    tokenize='unicode61'
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
```

---

## 🚀 Quick Start & Usage

### 1. Launch Web Server & UI
```bash
python3 -u app.py
```
Open your browser at: **`http://localhost:8088`**

### 2. Command-Line Search
```bash
# Search phone number or prefix
python3 search.py "01002407192"
python3 search.py --prefix "015"

# Search Arabic contact name
python3 search.py "سوزان"

# Search and directly launch matched row in LibreOffice Calc
python3 search.py "01123456789" --open
```

### 3. Batch Indexing via CLI
```bash
# Index a directory of spreadsheets and documents
python3 index_sheets.py /path/to/investigative/archive
```

### 4. Database Maintenance
```bash
# Verify integrity and checkpoint WAL
sqlite3 sheets_index.db "PRAGMA integrity_check; PRAGMA wal_checkpoint(TRUNCATE);"
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
