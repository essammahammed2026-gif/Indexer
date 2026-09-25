import unittest
import os
import tempfile
from storage.database import get_connection, init_tables
from storage.search_repository import query_db, get_stats, add_quick_filter, get_quick_filters
from storage.bookmarks import add_bookmark, get_bookmarks, remove_bookmark
from storage.events import record_change_event, get_change_events, mark_change_events_read

class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_index.db")
        conn = get_connection(self.db_path)
        init_tables(conn)
        conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_quick_filters(self):
        ok, msg = add_quick_filter(self.db_path, "VIP Target", "01002407192")
        self.assertTrue(ok)
        filters = get_quick_filters(self.db_path)
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0]["name"], "VIP Target")
        self.assertEqual(filters[0]["query"], "01002407192")

    def test_bookmarks(self):
        ok, msg = add_bookmark(self.db_path, "/test/doc.xlsx", "Sheet1", 10, "Target", "Urgent check")
        self.assertTrue(ok)
        bms = get_bookmarks(self.db_path)
        self.assertEqual(len(bms), 1)
        self.assertEqual(bms[0]["tag"], "Target")
        self.assertEqual(bms[0]["notes"], "Urgent check")
        
        ok_rem, _ = remove_bookmark(self.db_path, "/test/doc.xlsx", "Sheet1", 10)
        self.assertTrue(ok_rem)
        self.assertEqual(len(get_bookmarks(self.db_path)), 0)

    def test_change_events(self):
        ok = record_change_event(self.db_path, "added", "/path/file.pdf", records_count=50, details="Indexed PDF")
        self.assertTrue(ok)
        res = get_change_events(self.db_path)
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["unread_count"], 1)
        self.assertEqual(res["events"][0]["event_type"], "added")

        mark_change_events_read(self.db_path)
        res2 = get_change_events(self.db_path)
        self.assertEqual(res2["unread_count"], 0)

    def test_get_stats_empty(self):
        stats = get_stats(self.db_path)
        self.assertEqual(stats["files"], 0)
        self.assertEqual(stats["records"], 0)

if __name__ == "__main__":
    unittest.main()
