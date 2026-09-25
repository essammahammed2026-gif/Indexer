#!/usr/bin/env python3
"""
CDR & Excel Records Browser - Lightweight Web GUI (Built-in http.server + SQLite)
Supports:
- Unified search (Phones, Names, National ID, Cell IDs, arbitrary sheet values)
- Quick action to open matched row in LibreOffice Calc or default app
- Set Folder to Index with real-time Progress Bar
- Export & Import entire index database
- Live folder watcher automatically indexing newly added/updated sheets
Zero external dependencies (Python standard library only).
"""

import sys
import threading
from services import load_config, folder_watcher_loop
from web import run_server

PORT = 8088

def main():
    # 1. Initialize configuration with empty starting database
    load_config(startup=True)

    # 2. Start live directory watcher in background daemon thread
    watcher_thread = threading.Thread(target=folder_watcher_loop, daemon=True)
    watcher_thread.start()

    # 3. Start web server
    run_server(port=PORT)

if __name__ == "__main__":
    main()
