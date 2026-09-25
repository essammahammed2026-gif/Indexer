# Indexer Project - Agent Rules & Architecture Guidelines

## 1. Zero External Pip Dependencies (CRITICAL RULE)
- **NEVER** introduce third-party Python pip packages (e.g. `fastapi`, `flask`, `pydantic`, `pandas`, `openpyxl`, `pytesseract`, `cv2`, `requests`).
- Strictly adhere to Python's standard library:
  - Web Server & REST: `http.server`, `urllib.parse`, `json`
  - Database: `sqlite3`
  - File Parsers: `zipfile`, `xml.etree.ElementTree`, `csv`, `tarfile`
  - Concurrency: `threading`, `concurrent.futures`, `multiprocessing`
  - System Subprocesses: `subprocess`, `shutil`, `tempfile`
- System tasks (OCR, PDF text extraction, desktop dialogues) MUST use native Linux binaries via `subprocess`:
  - `pdftotext`, `pdftoppm` (poppler)
  - `tesseract` (with `-c tessedit_create_tsv=1`)
  - `magick` (ImageMagick)
  - `zenity` (with fallback to web file pickers)
  - `localc`, `xdg-open`

## 2. Arabic & Phone Normalization Conventions
- **Arabic Text Normalization**:
  - Always route Arabic text comparisons through `normalize_arabic()`.
  - Unify Hamzas (`أ`, `إ`, `آ` $\rightarrow$ `ا`), Alef Maksura (`ى` $\rightarrow$ `ي`), Teh Marbuta (`ة` $\rightarrow$ `ه`).
  - Strip Tashkeel diacritics (`[\u064B-\u0652\u0640]`).
  - Merge prefixes like `عبد الرحمن` to `عبدالرحمن`.
- **Phone Number Normalization**:
  - Always route phone queries and indexed cell values through `normalize_phone()`.
  - Handle Egyptian international format (`+20`, `0020`, `20`), floating `.0`, and trim to uniform 11-digit mobile strings (`01xxxxxxxxx`).

## 3. SQLite Database Guidelines
- Database: `sheets_index.db`.
- Always ensure `PRAGMA journal_mode = WAL;` and `PRAGMA synchronous = NORMAL;`.
- Use explicit transactions or context managers. Ensure connections opened in request handlers are always closed (`try...finally: conn.close()`).
- Keep tables backwards-compatible:
  - `files`, `cdr_records`, `universal_search` (FTS5), `quick_filters`, `bookmarks`, `ocr_boxes`.
- Do NOT perform writes concurrently from multiple arbitrary threads without holding appropriate locks or funneling through sequential SQLite commits.

## 4. Frontend & UI/UX Standards
- The web interface (`app.py`) is a Single-Page Application (SPA) in pure vanilla HTML5, CSS3, and modern JavaScript.
- Avoid bulky external CSS/JS frameworks (no Bootstrap, no jQuery, no React).
- Keep the UI clean, modern, dark-mode focused, and un-cluttered.
- Use vector SVG icons with consistent color-coding (e.g. Cyan for search, Emerald for success, Rose for danger/targets, Amber for notes/warnings, Indigo/Purple for records).
- All image loading in JS must attach `onload` listeners before setting `.src`, and handle `.complete` image states immediately.

## 5. Scope Separation
- **Indexer** (`/home/essam/Projects/Indexer`) is completely independent from any other projects on the system (e.g., `ESSR_PA`). Never mix files, configurations, or schemas between them.

## 6. Modular Package Refactoring & Session Hand-off Guidelines
- When refactoring `app.py` into decoupled submodules (`core/`, `storage/`, `services/`, `web/`, `templates/`, `static/`), adhere to [`REFACTORING_RUNBOOK.md`](file:///home/essam/Projects/Indexer/REFACTORING_RUNBOOK.md).
- **Zero Token Streaming of Frontend Code**: Extract HTML/CSS/JS via deterministic Python scripts, never via LLM chat generation tokens.
- **Global Window Scope in JS**: Extracted `static/js/app.js` must maintain global scope variables and functions for inline HTML event handlers.
- **Verbatim Migration First**: Relocate working functions verbatim into module files before making any algorithmic changes or optimizations.
- **Milestone Checks**: After every package extraction, compile with `python3 -m py_compile` and verify API endpoints return `200 OK` before checking off tasks.

