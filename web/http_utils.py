"""
HTTP request and response helper utilities for the Indexer web framework.
Standardizes JSON input reading, JSON response writing, and error handling.
Zero external pip dependencies.
"""

import json

def read_json_body(handler):
    """
    Safely read and parse incoming JSON HTTP request body.
    Returns (data: dict, error_message: str or None).
    """
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length <= 0:
        return {}, None
    try:
        raw_body = handler.rfile.read(content_length)
        return json.loads(raw_body.decode("utf-8")), None
    except Exception as e:
        return None, str(e)

def send_json(handler, data, status_code=200):
    """Serialize and send a JSON response with standard UTF-8 headers."""
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)

def send_error(handler, message, status_code=400):
    """Send a standard JSON error envelope: {"ok": false, "error": message}."""
    send_json(handler, {"ok": False, "error": str(message)}, status_code=status_code)

def send_success(handler, message="", **kwargs):
    """Send a standard JSON success envelope: {"ok": true, "message": message, ...}."""
    payload = {"ok": True}
    if message:
        payload["message"] = message
    payload.update(kwargs)
    send_json(handler, payload, status_code=200)
