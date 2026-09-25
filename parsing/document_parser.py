"""
Document parsing module for Word (.docx), OpenDocument (.odt), Text (.txt/.log/.json/.sql),
and PDF files (via pdftotext with automatic scanned-document OCR fallback).
Zero external pip dependencies.
"""

import os
import zipfile
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from .ocr_parser import run_ocr_detailed, get_image_dimensions

def parse_docx(fpath):
    """Parse text paragraphs from .docx files via internal document.xml."""
    rows_data = []
    try:
        with zipfile.ZipFile(fpath, 'r') as z:
            if 'word/document.xml' in z.namelist():
                tree = ET.fromstring(z.read('word/document.xml'))
                w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                p_idx = 1
                for p in tree.iter(f'{w_ns}p'):
                    texts = [t.text for t in p.iter(f'{w_ns}t') if t.text]
                    if texts:
                        line = "".join(texts).strip()
                        if line:
                            rows_data.append(('Doc', p_idx, [line]))
                            p_idx += 1
    except Exception as e:
        print(f"[DOCX ERROR] {fpath}: {e}")
    return rows_data

def parse_odt(fpath):
    """Parse text paragraphs from OpenDocument .odt files via internal content.xml."""
    rows_data = []
    try:
        with zipfile.ZipFile(fpath, 'r') as z:
            if 'content.xml' in z.namelist():
                tree = ET.fromstring(z.read('content.xml'))
                t_ns = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
                p_idx = 1
                for p in tree.iter(f'{t_ns}p'):
                    line = "".join(p.itertext()).strip()
                    if line:
                        rows_data.append(('Odt', p_idx, [line]))
                        p_idx += 1
    except Exception as e:
        print(f"[ODT ERROR] {fpath}: {e}")
    return rows_data

def parse_txt(fpath):
    """Parse plain text, log, json, or sql lines."""
    rows_data = []
    encodings = ['utf-8', 'cp1256', 'latin-1']
    for enc in encodings:
        try:
            with open(fpath, 'r', encoding=enc, errors='replace') as f:
                for idx, line in enumerate(f, start=1):
                    line_s = line.strip()
                    if line_s:
                        rows_data.append(('Text', idx, [line_s]))
            break
        except Exception:
            continue
    return rows_data

def parse_pdf(fpath):
    """
    Parse PDF file using native pdftotext.
    If extracted text is under 50 characters (e.g. scanned document),
    renders pages via pdftoppm and runs preprocessed OCR.
    Returns: (rows_data, pdf_boxes)
    """
    rows_data = []
    pdf_boxes = {}
    try:
        res = subprocess.run(
            ['pdftotext', '-layout', fpath, '-'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15
        )
        text = res.stdout.decode('utf-8', errors='ignore')
        for idx, line in enumerate(text.splitlines(), start=1):
            line_s = line.strip()
            if line_s:
                rows_data.append(('Page', idx, [line_s]))
    except Exception as e:
        print(f"[PDF ERROR] {fpath}: {e}")

    # Fallback to OCR if pdftotext extracted almost no text (e.g. scanned document)
    total_chars = sum(len(r[2][0]) for r in rows_data)
    if total_chars < 50:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                ppm_cmd = ['pdftoppm', '-png', '-r', '150', '-l', '5', fpath, os.path.join(tmpdir, 'p')]
                subprocess.run(ppm_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
                pngs = sorted([os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith('.png')])
                if pngs:
                    rows_data = []
                    for p_num, png in enumerate(pngs, start=1):
                        sname = f'Page_{p_num}'
                        ocr_txt, boxes = run_ocr_detailed(png)
                        w, h = get_image_dimensions(png)
                        if boxes:
                            pdf_boxes[sname] = (w, h, boxes)
                        for line_idx, line in enumerate(ocr_txt.splitlines(), start=1):
                            line_s = line.strip()
                            if line_s:
                                rows_data.append((sname, line_idx, [line_s]))
        except Exception as e:
            print(f"[PDF OCR ERROR] {fpath}: {e}")

    return rows_data, pdf_boxes

def parse_image(fpath):
    """Run OCR on image file and return formatted row lines."""
    rows_data = []
    text, boxes = run_ocr_detailed(fpath)
    if text:
        for idx, line in enumerate(text.splitlines(), start=1):
            line_s = line.strip()
            if line_s:
                rows_data.append(('Image', idx, [line_s]))
    return rows_data
