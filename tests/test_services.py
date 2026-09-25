"""
Unit tests for background services (state, indexer_service, watcher_service).
Zero external pip dependencies.
"""

import os
import unittest
import tempfile
import json
import shutil
import sqlite3
import services.state as state
from services.state import (
    load_config,
    save_config,
    get_active_db_path,
    sync_active_db_vars
)
from services.indexer_service import index_single_target, SUPPORTED_EXTENSIONS

class TestServices(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_config_path = state.CONFIG_PATH
        state.CONFIG_PATH = os.path.join(self.test_dir, "config.json")
        state.APP_CONFIG["db_storage_dir"] = self.test_dir
        state.APP_CONFIG["active_db"] = "default"
        state.APP_CONFIG["databases"] = {
            "default": {
                "nickname": "Test DB",
                "filename": "test_db.db",
                "watch_folder": self.test_dir,
                "watch_active": False,
                "created_at": "2026-09-25 10:00:00"
            }
        }
        sync_active_db_vars()

    def tearDown(self):
        state.CONFIG_PATH = self.old_config_path
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_active_db_path_and_sync(self):
        db_path = get_active_db_path()
        self.assertEqual(os.path.basename(db_path), "test_db.db")
        self.assertEqual(os.path.dirname(db_path), self.test_dir)
        self.assertEqual(state.WATCHER_CONFIG["folder"], self.test_dir)

    def test_save_and_load_config(self):
        state.WATCHER_CONFIG["active"] = True
        save_config()
        self.assertTrue(os.path.exists(state.CONFIG_PATH))

        # Reset and load back
        state.APP_CONFIG["databases"]["default"]["watch_active"] = False
        load_config()
        self.assertTrue(state.APP_CONFIG["databases"]["default"]["watch_active"])

    def test_index_single_target_empty(self):
        ok, msg, cnt, scanned = index_single_target(self.test_dir, db_path=get_active_db_path())
        self.assertFalse(ok)
        self.assertIn("No supported", msg)

    def test_index_single_csv_file(self):
        csv_file = os.path.join(self.test_dir, "contacts.csv")
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("phone,name,notes\n01012345678,Ahmed,Test note\n01198765432,Mohamed,Officer\n")

        db_path = get_active_db_path()
        ok, msg, cnt, scanned = index_single_target(csv_file, db_path=db_path)
        self.assertTrue(ok)
        self.assertGreater(cnt, 0)
        self.assertEqual(len(scanned), 1)

if __name__ == "__main__":
    unittest.main()
