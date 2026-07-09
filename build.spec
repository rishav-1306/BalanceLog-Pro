# -*- mode: python ; coding: utf-8 -*-
"""
BalanceLog Pro - PyInstaller Build Specification

Produces a self-contained Windows executable — no Python, no internet required
on the target machine.

Before building, run prepare_easyocr.py once to download the OCR model:
    python prepare_easyocr.py

Build command:
    pyinstaller build.spec --clean

Output: dist\BalanceLogPro\
Copy the entire dist\BalanceLogPro\ folder to the target machine and run
BalanceLogPro.exe.
"""

import sys
import os
from pathlib import Path

block_cipher = None

# ── Locate bundled EasyOCR model files ─────────────────────────────────────
# EasyOCR normally downloads models to ~/.EasyOCR/model/ on first run.
# We pre-download them (via prepare_easyocr.py) and bundle them here so the
# app works offline.
easyocr_model_dir = Path.home() / ".EasyOCR" / "model"
easyocr_datas = []
if easyocr_model_dir.exists():
    for f in easyocr_model_dir.iterdir():
        if f.is_file():
            easyocr_datas.append((str(f), "EasyOCR/model"))

# ── Analysis ────────────────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('src/assets',  'src/assets'),
        ('src/config',  'src/config'),
        ('src/ui',      'src/ui'),
        *easyocr_datas,
    ],
    hiddenimports=[
        # Qt
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtPrintSupport',
        # Computer vision
        'cv2',
        'numpy',
        # OCR
        'easyocr',
        'easyocr.config',
        'easyocr.detection',
        'easyocr.recognition',
        'easyocr.utils',
        'pytesseract',
        # Image
        'PIL',
        'PIL.Image',
        'PIL.ImageOps',
        # Screen capture
        'mss',
        'mss.windows',
        # Windows API
        'win32gui',
        'win32con',
        'win32process',
        'pywintypes',
        # Data / export
        'pandas',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        # PDF
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        # Standard library
        'sqlite3',
        'json',
        'pathlib',
        'logging',
        'logging.handlers',
        # PyTorch CPU-only (used by EasyOCR) — needed for offline model loading
        'torch',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'PyQt5',
        'PyQt6',
        'wx',
        # GPU / CUDA — not needed for CPU-only build
        'torchvision',
        'torch.cuda',
        'torchaudio',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BalanceLogPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No black terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # Add an .ico path here if you have one
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python3*.dll',
        'Qt6*.dll',
    ],
    name='BalanceLogPro',
)
