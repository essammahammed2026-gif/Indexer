"""
OS-level desktop integration: file openers, folder reveals, and native GUI dialogs.
Zero external pip dependencies.
"""

import os
import shutil
import subprocess
import urllib.parse

def open_in_app(file_path, sheet_name=None, row_idx=None):
    """Launch file in LibreOffice Calc positioned at row_idx or default system app."""
    if not file_path or not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    ext = os.path.splitext(file_path)[1].lower()
    env = os.environ.copy()
    abs_p = os.path.abspath(file_path)
    
    # Try LibreOffice Calc for spreadsheet files
    if ext in ('.xlsx', '.xls', '.csv', '.ods'):
        quoted_path = urllib.parse.quote(abs_p)
        if sheet_name and row_idx:
            uri = f"file://{quoted_path}#{sheet_name}.A{row_idx}"
        elif row_idx:
            uri = f"file://{quoted_path}#A{row_idx}"
        else:
            uri = f"file://{quoted_path}"
            
        try:
            subprocess.Popen(
                ['localc', '--norestore', uri],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return True, f"Opening in Calc at Row {row_idx or 1}"
        except Exception:
            pass

    # Fallback to system default application (xdg-open)
    try:
        subprocess.Popen(
            ['xdg-open', abs_p],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True, "Opened with default application"
    except Exception as e:
        return False, str(e)

def reveal_in_folder(file_path):
    """Open containing directory in system file manager via xdg-open."""
    if not file_path:
        return False, "File path is empty"
    abs_p = os.path.abspath(file_path)
    folder = abs_p if os.path.isdir(abs_p) else os.path.dirname(abs_p)
    if not os.path.exists(folder):
        return False, f"Folder not found: {folder}"
    try:
        subprocess.Popen(
            ['xdg-open', folder],
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True, f"Opened folder: {folder}"
    except Exception as e:
        return False, str(e)

def pick_folder_dialog(title="Select Folder to Index or Search"):
    """Open native Linux directory chooser (zenity or kdialog)."""
    chosen = None
    zenity_bin = shutil.which("zenity")
    if zenity_bin:
        try:
            res = subprocess.run(
                [zenity_bin, "--file-selection", "--directory", f"--title={title}"],
                capture_output=True, text=True, timeout=120, env=os.environ
            )
            if res.returncode == 0 and res.stdout.strip():
                chosen = res.stdout.strip()
        except Exception as e:
            print(f"[ZENITY PICK FOLDER ERROR] {e}")

    if not chosen and shutil.which("kdialog"):
        try:
            res = subprocess.run(
                ["kdialog", "--getexistingdirectory", os.path.expanduser("~"), "--title", title],
                capture_output=True, text=True, timeout=120, env=os.environ
            )
            if res.returncode == 0 and res.stdout.strip():
                chosen = res.stdout.strip()
        except Exception as e:
            print(f"[KDIALOG PICK FOLDER ERROR] {e}")

    return chosen

def pick_file_dialog(title="Select File or Image to Index"):
    """Open native Linux file chooser (zenity or kdialog)."""
    chosen = None
    zenity_bin = shutil.which("zenity")
    if zenity_bin:
        try:
            res = subprocess.run(
                [zenity_bin, "--file-selection", f"--title={title}",
                 "--file-filter=Supported Documents & Images | *.pdf *.docx *.xlsx *.xls *.png *.jpg *.jpeg *.webp *.txt *.csv",
                 "--file-filter=All Files | *"],
                capture_output=True, text=True, timeout=120, env=os.environ
            )
            if res.returncode == 0 and res.stdout.strip():
                chosen = res.stdout.strip()
        except Exception as e:
            print(f"[ZENITY PICK FILE ERROR] {e}")
    return chosen
