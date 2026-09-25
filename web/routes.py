"""
Web route registry and router factory for the Indexer application.
Zero external pip dependencies.
"""

from .router import Router
from .handlers.static_handlers import handle_index_html, handle_static_asset
from .handlers.search_handlers import (
    handle_stats,
    handle_search,
    handle_search_csv,
    handle_context,
    handle_get_filters,
    handle_add_filter,
    handle_delete_filter,
    handle_export
)
from .handlers.database_handlers import (
    handle_list_databases,
    handle_switch_database,
    handle_rename_database,
    handle_create_database,
    handle_delete_database,
    handle_import_database
)
from .handlers.settings_handlers import handle_get_settings, handle_save_settings
from .handlers.bookmark_handlers import (
    handle_get_bookmarks,
    handle_add_bookmark,
    handle_delete_bookmark
)
from .handlers.image_handlers import handle_image_view, handle_image_boxes
from .handlers.system_handlers import (
    handle_open,
    handle_reveal,
    handle_pick_folder_dialog,
    handle_pick_file_dialog,
    handle_backup,
    handle_watch_status,
    handle_watch_toggle,
    handle_index_status,
    handle_get_notifications,
    handle_read_notifications,
    handle_clear_notifications,
    handle_index_start,
    handle_index_refresh,
    handle_index_reindex,
    handle_target_index,
    handle_target_upload
)

def create_router():
    """Build and register all application routes onto the Router instance."""
    router = Router()

    # Static Assets & Templates
    router.add_route("GET", "/", handle_index_html)
    router.add_route("GET", "/index.html", handle_index_html)
    router.add_prefix_route("GET", "/static/", handle_static_asset)

    # Core Stats & Search
    router.add_route("GET", "/api/stats", handle_stats)
    router.add_route("GET", "/api/search", handle_search)
    router.add_route("GET", "/api/search/csv", handle_search_csv)
    router.add_route("GET", "/api/context", handle_context)
    router.add_route("GET", "/api/filters", handle_get_filters)
    router.add_route("POST", "/api/filters/add", handle_add_filter)
    router.add_route("POST", "/api/filters/delete", handle_delete_filter)
    router.add_route("GET", "/api/index/export", handle_export)

    # Multi-Database Management
    router.add_route("GET", "/api/databases", handle_list_databases)
    router.add_route("POST", "/api/databases/switch", handle_switch_database)
    router.add_route("POST", "/api/databases/rename", handle_rename_database)
    router.add_route("POST", "/api/databases/create", handle_create_database)
    router.add_route("POST", "/api/databases/delete", handle_delete_database)
    router.add_route("POST", "/api/index/import", handle_import_database)

    # Settings
    router.add_route("GET", "/api/settings", handle_get_settings)
    router.add_route("POST", "/api/settings/save", handle_save_settings)

    # Bookmarks
    router.add_route("GET", "/api/bookmarks", handle_get_bookmarks)
    router.add_route("POST", "/api/bookmarks/add", handle_add_bookmark)
    router.add_route("POST", "/api/bookmarks/delete", handle_delete_bookmark)

    # Images & OCR
    router.add_route("GET", "/api/image/view", handle_image_view)
    router.add_route("GET", "/api/image/boxes", handle_image_boxes)

    # System Interop, Watcher & Indexing
    router.add_route("GET", "/api/open", handle_open)
    router.add_route("GET", "/api/reveal", handle_reveal)
    router.add_route("GET", "/api/dialog/pick-folder", handle_pick_folder_dialog)
    router.add_route("GET", "/api/dialog/pick-file", handle_pick_file_dialog)
    router.add_route("GET", "/api/backup", handle_backup)
    router.add_route("GET", "/api/watch/status", handle_watch_status)
    router.add_route("POST", "/api/watch/toggle", handle_watch_toggle)
    router.add_route("GET", "/api/index/status", handle_index_status)
    router.add_route("GET", "/api/progress", handle_index_status)
    router.add_route("GET", "/api/notifications", handle_get_notifications)
    router.add_route("POST", "/api/notifications/read", handle_read_notifications)
    router.add_route("POST", "/api/notifications/clear", handle_clear_notifications)
    router.add_route("POST", "/api/index/start", handle_index_start)
    router.add_route("POST", "/api/index/refresh", handle_index_refresh)
    router.add_route("POST", "/api/index/reindex", handle_index_reindex)
    router.add_route("POST", "/api/target/index", handle_target_index)
    router.add_route("POST", "/api/target/upload", handle_target_upload)

    return router
