"""
OCR and image analysis module.
Performs ImageMagick auto-deskewing/enhancement and Tesseract TSV bounding box extraction.
Zero external pip dependencies (delegates to linux native binaries).
"""

import os
import tempfile
import subprocess

def get_image_dimensions(img_path):
    """Retrieve width and height of an image file using magick identify."""
    try:
        res = subprocess.run(['magick', 'identify', '-format', '%w %h', img_path], capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            parts = res.stdout.strip().split()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return None, None

def preprocess_image(input_path, output_path):
    """
    Apply image preprocessing tailored for Arabic and English document OCR:
    - Grayscale conversion
    - Contrast stretch and auto-leveling
    - Automatic deskewing up to 40%
    - Subtle sharpening to restore stroke boundaries
    """
    try:
        cmd = [
            'magick', input_path,
            '-colorspace', 'gray',
            '-auto-level',
            '-contrast-stretch', '1%x1%',
            '-deskew', '40%',
            '-sharpen', '0x1',
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"[PREPROCESS ERROR] {input_path}: {e}")
        return False

def run_ocr(image_path):
    """Run Tesseract OCR on an image file and return extracted plain text."""
    text, _ = run_ocr_detailed(image_path)
    return text

def run_ocr_detailed(image_path):
    """
    Runs preprocessed Tesseract OCR on image_path.
    Returns:
      (plain_text: str, boxes: list of dicts)
      where each box is {"text": str, "left": int, "top": int, "width": int, "height": int, "conf": float}
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tessdata_dir = os.path.join(base_dir, "tessdata")
    base_cmd = ['tesseract']
    if os.path.exists(tessdata_dir):
        base_cmd.extend(['--tessdata-dir', tessdata_dir])

    with tempfile.TemporaryDirectory() as tmpdir:
        prep_img = os.path.join(tmpdir, "preprocessed.png")
        if preprocess_image(image_path, prep_img):
            target_to_ocr = prep_img
        else:
            target_to_ocr = image_path

        # 1. Extract bounding boxes using TSV mode
        tsv_cmd = base_cmd + [target_to_ocr, 'stdout', '-l', 'eng+ara', '--oem', '1', '-c', 'tessedit_create_tsv=1']
        boxes = []
        try:
            res_tsv = subprocess.run(tsv_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30)
            tsv_lines = res_tsv.stdout.decode('utf-8', errors='ignore').splitlines()
            for line in tsv_lines[1:]:
                parts = line.split('\t')
                if len(parts) >= 12:
                    word = parts[11].strip()
                    if word:
                        try:
                            conf = float(parts[10])
                            left = int(parts[6])
                            top = int(parts[7])
                            width = int(parts[8])
                            height = int(parts[9])
                            boxes.append({
                                "text": word,
                                "left": left,
                                "top": top,
                                "width": width,
                                "height": height,
                                "conf": conf
                            })
                        except (ValueError, IndexError):
                            pass
        except Exception as e:
            print(f"[OCR TSV ERROR] {image_path}: {e}")

        # 2. Extract standard plain text
        txt_cmd = base_cmd + [target_to_ocr, 'stdout', '-l', 'eng+ara', '--oem', '1']
        plain_text = ""
        try:
            res_txt = subprocess.run(txt_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30)
            plain_text = res_txt.stdout.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            print(f"[OCR TXT ERROR] {image_path}: {e}")

        return plain_text, boxes
