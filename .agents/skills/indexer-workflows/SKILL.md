---
name: indexer-workflows
description: Standard operational workflows for the Indexer search and OCR platform. Covers indexing directories, running queries, debugging OCR, database management, and UI maintenance.
---

# Indexer Workflows & Operational Runbook

This skill provides step-by-step instructions for working on and maintaining the Indexer engine.

## 1. Running the Application
```bash
python3 -u app.py
```
- Available at `http://localhost:8088`.
- Server runs in a single process using `http.server.HTTPServer`.
- Spawns a background daemon thread `folder_watcher_loop` which checks for newly added or modified files every 3 seconds if active.

## 2. Testing & Compiling Code
Before committing or restarting the server, always check Python syntax:
```bash
python3 -m py_compile app.py indexer_engine.py index_sheets.py search.py
```

## 3. Command Line Ingestion & Queries
- **Batch Indexing**:
  ```bash
  python3 index_sheets.py /path/to/folder
  ```
- **CLI Querying**:
  ```bash
  # Search phone number:
  python3 search.py "01002407192"

  # Search Arabic name:
  python3 search.py "سوزان"

  # Universal text search:
  python3 search.py --raw "تقرير"

  # Auto-open first match in LibreOffice Calc:
  python3 search.py "01002407192" --open
  ```

## 4. OCR Troubleshooting
- If OCR returns empty bounding boxes or fails:
  - Check Tesseract version: `tesseract --version`
  - Check ImageMagick: `magick --version`
  - Ensure Tesseract TSV mode uses `-c tessedit_create_tsv=1` and does NOT pass positional `tsv` when `--tessdata-dir` is configured.
  - Verify local tessdata models in `./tessdata/` (`ara.traineddata`, `eng.traineddata`).

## 5. Database Maintenance
- Always run WAL checkpoints and integrity checks if the database grows large:
  ```bash
  sqlite3 sheets_index.db "PRAGMA integrity_check; PRAGMA wal_checkpoint(TRUNCATE);"
  ```
- Backups are stored as `sheets_index.db.snap_YYYYMMDD`.

## 6. Modular Refactoring & Regression Testing Workflow
- Refer to [`REFACTORING_RUNBOOK.md`](file:///home/essam/Projects/Indexer/REFACTORING_RUNBOOK.md) for master checklists and phase execution.
- Run automated unit and regression tests:
  ```bash
  python3 -m unittest discover tests/
  ```
- Verify web endpoints return `200 OK`:
  ```bash
  curl -s http://localhost:8088/api/databases | grep '"ok": true'
  curl -s http://localhost:8088/api/settings | grep '"ok": true'
  curl -s "http://localhost:8088/api/search?q=test" | grep '"ok": true'
  ```

## 7. Operational Workflow for Modifying or Adding Features
Follow these steps whenever a task asks to add, edit, or remove a feature:
1. **Check Existing Modules First**:
   - Do not write new helper functions without inspecting `parsing/`, `core/normalizers.py`, and `storage/`.
2. **Follow the Route Dispatcher Pattern**:
   - Register endpoints in `web/routes.py`.
   - Implement handlers in `web/handlers/` using `web.http_utils.send_json` and `read_json_body`.
3. **Verify with Full Suite**:
   ```bash
   python3 -m py_compile app.py core/*.py storage/*.py parsing/*.py services/*.py web/*.py web/handlers/*.py
   python3 -m unittest discover tests/
   ```
4. **Smoke Test Web GUI**:
   - Ensure the server starts clean (`python3 -u app.py`) and responds to HTTP requests.


