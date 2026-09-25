"""
Lead bookmarking and tagging HTTP handlers.
Zero external pip dependencies.
"""

import storage
from services import get_active_db_path
from ..http_utils import read_json_body, send_success, send_error

def handle_get_bookmarks(handler, parsed):
    bookmarks = storage.get_bookmarks(get_active_db_path())
    send_success(handler, bookmarks=bookmarks)

def handle_add_bookmark(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    fpath = (data or {}).get("file", "").strip()
    sname = (data or {}).get("sheet", "").strip()
    row = (data or {}).get("row", 1)
    tag = (data or {}).get("tag", "Lead").strip()
    notes = (data or {}).get("notes", "").strip()
    ok, msg = storage.add_bookmark(get_active_db_path(), fpath, sname, row, tag=tag, notes=notes)
    if ok:
        send_success(handler, msg)
    else:
        send_error(handler, msg, 400)

def handle_delete_bookmark(handler, parsed):
    data, err = read_json_body(handler)
    if err:
        send_error(handler, err, 400)
        return
    fpath = (data or {}).get("file", "").strip()
    sname = (data or {}).get("sheet", "").strip()
    row = (data or {}).get("row", 1)
    ok, msg = storage.remove_bookmark(get_active_db_path(), fpath, sname, row)
    if ok:
        send_success(handler, msg)
    else:
        send_error(handler, msg, 400)
