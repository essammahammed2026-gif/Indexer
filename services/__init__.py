"""
Background services for Indexer: state management, indexing engine, and filesystem watcher.
Zero external pip dependencies.
"""

from .state import (
    BASE_DIR,
    CONFIG_PATH,
    UPLOADS_DIR,
    INDEX_LOCK,
    INDEX_STATE,
    APP_CONFIG,
    WATCHER_CONFIG,
    get_active_db_path,
    sync_active_db_vars,
    load_config,
    save_config
)

from .indexer_service import (
    SUPPORTED_EXTENSIONS,
    index_single_target,
    start_indexing_thread
)

from .watcher_service import (
    folder_watcher_loop
)

__all__ = [
    "BASE_DIR",
    "CONFIG_PATH",
    "UPLOADS_DIR",
    "INDEX_LOCK",
    "INDEX_STATE",
    "APP_CONFIG",
    "WATCHER_CONFIG",
    "get_active_db_path",
    "sync_active_db_vars",
    "load_config",
    "save_config",
    "SUPPORTED_EXTENSIONS",
    "index_single_target",
    "start_indexing_thread",
    "folder_watcher_loop"
]
