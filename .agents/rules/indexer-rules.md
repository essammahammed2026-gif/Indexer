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
- The web interface (`templates/index.html`) is a Single-Page Application (SPA) in pure vanilla HTML5, CSS3 (`static/css/app.css`), and modern JavaScript (`static/js/app.js`).
- Avoid bulky external CSS/JS frameworks (no Bootstrap, no jQuery, no React).
- **Restrained Slate & Precision Accent Aesthetic**:
  - Maintain a clean, professional, dark-slate background palette (`#0b0f17`, `#111827`, `#151e2e`).
  - Do NOT re-introduce saturated rainbow colors for everyday UI elements. Keep standard navigation, action, and category icons in neutral monochrome (`#94a3b8` / `icon-slate`).
  - Restrict saturated semantic colors strictly to real system statuses: Emerald (`#10b981`) for live background sync/watcher, Amber (`#fbbf24`) for warnings/unreads, and Rose (`#ef4444`) for destructive deletions.
- **De-cluttered Layouts**:
  - Keep primary action buttons focused (e.g. `+ Index Folder`, `Settings`, `Tools ▾`). Consolidate maintenance and destructive operations (Re-Index, Snapshot Backup, Export/Import) inside dropdown menus or settings dialogs rather than cluttering top-level viewports.
  - Avoid redundant toggle controls across multiple rows (e.g., maintain single clean entry points for view and grouping modes).
- All image loading in JS must attach `onload` listeners before setting `.src`, and handle `.complete` image states immediately.

## 5. Scope Separation
- **Indexer** (`/home/essam/Projects/Indexer`) is completely independent from any other projects on the system (e.g., `ESSR_PA`). Never mix files, configurations, or schemas between them.

## 6. Modular Package Refactoring & Session Hand-off Guidelines
- When refactoring `app.py` into decoupled submodules (`core/`, `storage/`, `services/`, `web/`, `templates/`, `static/`, `parsing/`), adhere to [`REFACTORING_RUNBOOK.md`](file:///home/essam/Projects/Indexer/REFACTORING_RUNBOOK.md).
- **Zero Token Streaming of Frontend Code**: Extract HTML/CSS/JS via deterministic Python scripts, never via LLM chat generation tokens.
- **Global Window Scope in JS**: Extracted `static/js/app.js` must maintain global scope variables and functions for inline HTML event handlers.
- **Verbatim Migration First**: Relocate working functions verbatim into module files before making any algorithmic changes or optimizations.
- **Milestone Checks**: After every package extraction, compile with `python3 -m py_compile` and verify API endpoints return `200 OK` before checking off tasks.

## 7. Anti-AI-Bloat Lifecycle: Standardized Feature Operations
To prevent multi-stage AI sessions from accumulating redundant functions, duplicated normalizers, or orphaned code:

### 1. How to Add a New Feature
1. **Locate the Single Source of Truth**:
   - File parsing $\rightarrow$ [`parsing/`](file:///home/essam/Projects/Indexer/parsing)
   - String/phone/Arabic normalization $\rightarrow$ [`core/normalizers.py`](file:///home/essam/Projects/Indexer/core/normalizers.py)
   - SQLite queries & schema $\rightarrow$ [`storage/`](file:///home/essam/Projects/Indexer/storage)
   - Concurrency & threads $\rightarrow$ [`services/`](file:///home/essam/Projects/Indexer/services)
   - HTTP routes & serialization $\rightarrow$ [`web/routes.py`](file:///home/essam/Projects/Indexer/web/routes.py) & [`web/http_utils.py`](file:///home/essam/Projects/Indexer/web/http_utils.py)
2. **Never inline domain logic**: Never define private helper normalizers, raw SQL queries, or nested parser loops inside endpoint handlers or ingestion scripts. Import existing domain functions.
3. **Register Route**: Add the endpoint to [`web/routes.py`](file:///home/essam/Projects/Indexer/web/routes.py) mapping cleanly to a handler in [`web/handlers/`](file:///home/essam/Projects/Indexer/web/handlers).
4. **Add Unit Test**: Add test coverage to [`tests/`](file:///home/essam/Projects/Indexer/tests) and verify with `python3 -m unittest discover tests/`.

### 2. How to Edit an Existing Feature
1. **Search for Existing Implementations**: Grep the codebase before adding new code. If modifying behavior, modify the shared module directly (e.g. `core/normalizers.py` or `storage/search_repository.py`), not callers.
2. **Maintain Interface Contracts**: Keep function signatures backward-compatible so CLI utilities (`search.py`, `index_sheets.py`) and background services continue functioning seamlessly.
3. **Run Regression Tests**: Always execute `python3 -m unittest discover tests/` before completing an edit.

### 3. How to Remove a Feature
1. **Remove Route Entry**: Delete endpoint registration in [`web/routes.py`](file:///home/essam/Projects/Indexer/web/routes.py).
2. **Remove Controller Logic**: Delete corresponding method in `web/handlers/*.py`.
3. **Prune Dead Storage Methods**: Remove unused queries from `storage/`. Do not leave "commented out" or "deprecated" dead code.
4. **Prune Frontend Assets**: Remove related buttons, event handlers, and modals from `templates/index.html` and `static/js/app.js`.
5. **Verify Clean Syntax**: Run `python3 -m py_compile app.py` and run tests.


