"""
Image view thumbnail, document rendering, and OCR overlay bounding boxes HTTP handlers.
Zero external pip dependencies.
"""

import os
import urllib.parse
import storage
from services import get_active_db_path
from ..http_utils import send_success, send_error

def handle_image_view(handler, parsed):
    qs = urllib.parse.parse_qs(parsed.query)
    file_path = qs.get("file", [""])[0]
    if not file_path or not os.path.exists(file_path):
        handler.send_response(404)
        handler.end_headers()
        handler.wfile.write(b"Image file not found")
        return
    ext = os.path.splitext(file_path)[1].lower()
    mime = "image/png"
    if ext in ('.jpg', '.jpeg'): mime = "image/jpeg"
    elif ext == '.webp': mime = "image/webp"
    elif ext == '.bmp': mime = "image/bmp"
    elif ext == '.tiff': mime = "image/tiff"
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        handler.send_response(200)
        handler.send_header("Content-Type", mime)
        handler.send_header("Content-Length", str(len(data)))
        handler.send_header("Cache-Control", "public, max-age=3600")
        handler.end_headers()
        handler.wfile.write(data)
    except Exception as e:
        send_error(handler, str(e), 500)

def handle_image_boxes(handler, parsed):
    qs = urllib.parse.parse_qs(parsed.query)
    file_path = qs.get("file", [""])[0]
    sheet_name = qs.get("sheet", ["Image"])[0]
    box_data = storage.get_ocr_boxes(get_active_db_path(), file_path, sheet_name=sheet_name)
    send_success(handler, data=box_data)
