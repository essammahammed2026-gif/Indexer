import unittest
from core.normalizers import normalize_phone, normalize_arabic, levenshtein_dist
from core.query_parser import parse_google_query

class TestCoreDomain(unittest.TestCase):
    def test_normalize_phone(self):
        # Egyptian international formats
        self.assertEqual(normalize_phone("+201002407192"), "01002407192")
        self.assertEqual(normalize_phone("00201123456789"), "01123456789")
        self.assertEqual(normalize_phone("201234567890"), "01234567890")
        self.assertEqual(normalize_phone("1012345678"), "01012345678")
        self.assertEqual(normalize_phone("01512345678"), "01512345678")
        self.assertEqual(normalize_phone(""), "")

    def test_normalize_arabic(self):
        # Hamzas unification
        self.assertEqual(normalize_arabic("أحمد"), "احمد")
        self.assertEqual(normalize_arabic("إبراهيم"), "ابراهيم")
        self.assertEqual(normalize_arabic("آمنة"), "امنه")
        # Teh Marbuta
        self.assertEqual(normalize_arabic("فاطمة"), "فاطمه")
        # Alef Maksura
        self.assertEqual(normalize_arabic("مستشفى"), "مستشفي")
        # Tashkeel diacritics stripping
        self.assertEqual(normalize_arabic("مُحَمَّدٌ"), "محمد")

    def test_levenshtein_dist(self):
        self.assertEqual(levenshtein_dist("apple", "apple"), 0)
        self.assertEqual(levenshtein_dist("kitten", "sitting"), 3)
        self.assertEqual(levenshtein_dist("محمد", "محمود"), 1)

    def test_parse_google_query(self):
        res = parse_google_query('"cairo tower" filetype:pdf -confidential')
        self.assertEqual(res["filetype"], "pdf")
        self.assertIn("cairo tower", res["exact_phrases"])
        self.assertTrue('NOT ""confidential""' in res["fts_match"])

if __name__ == "__main__":
    unittest.main()
