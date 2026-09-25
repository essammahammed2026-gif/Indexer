"""
Storage package initialization and public interface.
"""

from .database import get_connection, init_tables
from .search_repository import (
    query_db,
    get_stats,
    get_quick_filters,
    add_quick_filter,
    delete_quick_filter,
    get_ocr_boxes
)
from .bookmarks import (
    get_bookmarks,
    add_bookmark,
    remove_bookmark,
    get_context_window
)
from .events import (
    record_change_event,
    get_change_events,
    mark_change_events_read,
    clear_all_change_events,
    backup_database
)

__all__ = [
    "get_connection",
    "init_tables",
    "query_db",
    "get_stats",
    "get_quick_filters",
    "add_quick_filter",
    "delete_quick_filter",
    "get_ocr_boxes",
    "get_bookmarks",
    "add_bookmark",
    "remove_bookmark",
    "get_context_window",
    "record_change_event",
    "get_change_events",
    "mark_change_events_read",
    "clear_all_change_events",
    "backup_database"
]

