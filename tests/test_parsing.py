"""Tests for the pure Python parsing sub-engine."""
import unittest
import tempfile
import os
import zipfile
import csv

from parsing.spreadsheet_parser import parse_csv, parse_xlsx
from parsing.document_parser import parse_txt, parse_docx
from parsing import parse_document


class TestSpreadsheetParser(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_parse_csv(self):
        csv_path = os.path.join(self.test_dir.name, "sample.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Phone", "Notes"])
            writer.writerow(["Ahmed", "01012345678", "VIP Customer"])
            writer.writerow(["Sara", "01198765432", "Follow-up required"])

        rows = parse_csv(csv_path)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][0], "Sheet1")
        self.assertEqual(rows[1][1], 2)
        self.assertIn("01012345678", rows[1][2])
        self.assertIn("Ahmed", rows[1][2])

    def test_parse_xlsx_minimal(self):
        xlsx_path = os.path.join(self.test_dir.name, "sample.xlsx")
        # Build minimal valid xlsx zip structure
        workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets>
        <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
    </sheets>
</workbook>"""
        workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
        shared_strings = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="2" uniqueCount="2">
    <si><t>Caller</t></si>
    <si><t>Receiver</t></si>
</sst>"""
        sheet_data = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheetData>
        <row r="1">
            <c r="A1" t="s"><v>0</v></c>
            <c r="B1" t="s"><v>1</v></c>
        </row>
        <row r="2">
            <c r="A2"><v>01099999999</v></c>
            <c r="B2"><v>01188888888</v></c>
        </row>
    </sheetData>
</worksheet>"""
        with zipfile.ZipFile(xlsx_path, "w") as zf:
            zf.writestr("xl/workbook.xml", workbook_xml)
            zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            zf.writestr("xl/sharedStrings.xml", shared_strings)
            zf.writestr("xl/worksheets/sheet1.xml", sheet_data)

        rows = parse_xlsx(xlsx_path)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "Sheet1")
        self.assertEqual(rows[0][2], ["Caller", "Receiver"])
        self.assertEqual(rows[1][2], ["01099999999", "01188888888"])


class TestDocumentParser(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_parse_txt(self):
        txt_path = os.path.join(self.test_dir.name, "note.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Line 1: Target investigation\nLine 2: Target located at Cairo.")

        rows = parse_txt(txt_path)
        self.assertEqual(len(rows), 2)
        self.assertIn("Target investigation", rows[0][2][0])

    def test_parse_docx_minimal(self):
        docx_path = os.path.join(self.test_dir.name, "doc.docx")
        doc_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p><w:r><w:t>Confidential Report</w:t></w:r></w:p>
        <w:p><w:r><w:t>Case Number: 45091</w:t></w:r></w:p>
    </w:body>
</w:document>"""
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", doc_xml)

        rows = parse_docx(docx_path)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][2][0], "Confidential Report")
        self.assertEqual(rows[1][2][0], "Case Number: 45091")

    def test_extract_file_text_dispatcher(self):
        txt_path = os.path.join(self.test_dir.name, "dispatch.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Unified dispatcher works")

        rows = parse_document(txt_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2][0], "Unified dispatcher works")


if __name__ == "__main__":
    unittest.main()
