"""
Unified document and file ingestion parsing package.
Supports spreadsheets, word docs, text files, PDFs, and OCR scanned images.
"""

import os
from .spreadsheet_parser import parse_xlsx, parse_csv, parse_xls, col_letters_to_num
from .document_parser import parse_docx, parse_odt, parse_txt, parse_pdf, parse_image
from .ocr_parser import run_ocr, run_ocr_detailed, get_image_dimensions, preprocess_image

def parse_document(fpath):
    """
    Route any supported document, spreadsheet, or image file to its dedicated parser.
    Returns: list of tuples: (sheet_or_section_name, row_idx, row_values_list)
    """
    ext = os.path.splitext(fpath)[1].lower()
    if ext == '.xlsx':
        return parse_xlsx(fpath)
    elif ext in ('.csv', '.tsv'):
        return parse_csv(fpath)
    elif ext == '.xls':
        return parse_xls(fpath)
    elif ext == '.docx':
        return parse_docx(fpath)
    elif ext == '.odt':
        return parse_odt(fpath)
    elif ext in ('.txt', '.log', '.json', '.sql'):
        return parse_txt(fpath)
    elif ext == '.pdf':
        res = parse_pdf(fpath)
        if isinstance(res, tuple):
            return res[0]
        return res
    elif ext in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'):
        return parse_image(fpath)
    return []

# Backward compatible alias
parse_workbook = parse_document

__all__ = [
    "col_letters_to_num",
    "parse_xlsx",
    "parse_csv",
    "parse_xls",
    "parse_docx",
    "parse_odt",
    "parse_txt",
    "parse_pdf",
    "parse_image",
    "run_ocr",
    "run_ocr_detailed",
    "get_image_dimensions",
    "preprocess_image",
    "parse_document",
    "parse_workbook"
]
