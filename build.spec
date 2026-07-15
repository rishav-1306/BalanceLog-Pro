# -*- mode: python ; coding: utf-8 -*-
"""
BalanceLog Pro - PyInstaller Build Specification

Produces a self-contained Windows executable — no Python, no internet required
on the target machine.

Before building, run prepare_easyocr.py once to download the OCR model:
    python prepare_easyocr.py

Build command (automated):
    python build.py

Build command (manual):
    pyinstaller build.spec --clean

Output: dist\BalanceLogPro\
Copy the entire dist\BalanceLogPro\ folder to the target machine and run
BalanceLogPro.exe.
"""

import sys
import os
from pathlib import Path

block_cipher = None

# ── Locate Python site-packages ────────────────────────────────────────────
_site_packages = None
for p in sys.path:
    if "site-packages" in p and Path(p).is_dir():
        _site_packages = Path(p)
        break

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

# ── Locate EasyOCR package data ────────────────────────────────────────────
# EasyOCR has internal data files (character dictionaries, configs) that
# PyInstaller doesn't auto-detect because they're loaded at runtime.
easyocr_pkg_datas = []
if _site_packages:
    easyocr_pkg = _site_packages / "easyocr"
    if easyocr_pkg.is_dir():
        # Bundle the character dictionary files (*.txt for each language)
        char_dir = easyocr_pkg / "character"
        if char_dir.is_dir():
            for f in char_dir.iterdir():
                if f.is_file():
                    easyocr_pkg_datas.append((str(f), "easyocr/character"))
        # Bundle DBNet config files
        dbnet_dir = easyocr_pkg / "DBNet"
        if dbnet_dir.is_dir():
            for root, dirs, files in os.walk(str(dbnet_dir)):
                for f in files:
                    src = os.path.join(root, f)
                    rel = os.path.relpath(root, str(easyocr_pkg))
                    easyocr_pkg_datas.append((src, f"easyocr/{rel}"))

# ── App icon ───────────────────────────────────────────────────────────────
app_icon = None
icon_path = Path("src/assets/icon.ico")
if icon_path.exists():
    app_icon = str(icon_path)

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
        *easyocr_pkg_datas,
    ],
    hiddenimports=[
        # ── Qt ──
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtPrintSupport',

        # ── Computer vision ──
        'cv2',
        'numpy',

        # ── OCR ──
        'easyocr',
        'easyocr.config',
        'easyocr.craft',
        'easyocr.craft_utils',
        'easyocr.detection',
        'easyocr.detection_db',
        'easyocr.easyocr',
        'easyocr.export',
        'easyocr.imgproc',
        'easyocr.recognition',
        'easyocr.utils',
        'easyocr.model',
        'easyocr.model.model',
        'easyocr.model.modules',
        'easyocr.model.vgg_model',
        'easyocr.DBNet',
        'easyocr.DBNet.DBNet',

        # Tesseract (optional fallback — gracefully handled if missing)
        'pytesseract',

        # ── Image ──
        'PIL',
        'PIL.Image',
        'PIL.ImageOps',
        'PIL.ImageDraw',
        'PIL.ImageFont',

        # ── Screen capture ──
        'mss',
        'mss.windows',

        # ── Windows API ──
        'win32gui',
        'win32con',
        'win32process',
        'win32api',
        'pywintypes',

        # ── Data / export ──
        'pandas',
        'pandas.io.formats.excel',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.styles.fills',
        'openpyxl.styles.fonts',
        'openpyxl.styles.alignment',
        'openpyxl.styles.borders',
        'openpyxl.styles.numbers',
        'openpyxl.styles.protection',
        'openpyxl.utils',
        'openpyxl.utils.dataframe',
        'openpyxl.workbook',
        'openpyxl.worksheet',

        # ── PDF ──
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.pdfgen.canvas',
        'reportlab.lib',
        'reportlab.lib.colors',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.enums',
        'reportlab.lib.styles',
        'reportlab.platypus',
        'reportlab.platypus.paragraph',
        'reportlab.platypus.tables',
        'reportlab.platypus.frames',
        'reportlab.platypus.doctemplate',

        # ── Standard library ──
        'sqlite3',
        'json',
        'pathlib',
        'logging',
        'logging.handlers',
        'csv',

        # ── PyTorch CPU-only ──
        # EasyOCR imports torch for model inference. These hidden imports
        # ensure PyInstaller captures the needed submodules.
        'torch',
        'torch.nn',
        'torch.nn.functional',
        'torch.nn.modules',
        'torch.nn.modules.activation',
        'torch.nn.modules.batchnorm',
        'torch.nn.modules.container',
        'torch.nn.modules.conv',
        'torch.nn.modules.dropout',
        'torch.nn.modules.linear',
        'torch.nn.modules.loss',
        'torch.nn.modules.module',
        'torch.nn.modules.padding',
        'torch.nn.modules.pooling',
        'torch.nn.modules.rnn',
        'torch.nn.modules.upsampling',
        'torch.nn.modules.utils',
        'torch.autograd',
        'torch.optim',
        'torch.utils',
        'torch.utils.data',
        'torch.jit',
        'torch.backends',
        'torch.backends.cpu',
        'torch.backends.mkl',
        'torch.serialization',

        # ── Application modules ──
        'src',
        'src.config',
        'src.config.config_manager',
        'src.config.constants',
        'src.ui',
        'src.ui.main_window',
        'src.ui.theme',
        'src.ui.widgets',
        'src.ui.dashboard_page',
        'src.ui.records_page',
        'src.ui.calibration_page',
        'src.ui.settings_page',
        'src.ui.reports_page',
        'src.ui.search_page',
        'src.ui.logs_page',
        'src.ui.confirmation_dialog',
        'src.ui.record_detail_dialog',
        'src.database',
        'src.database.db_manager',
        'src.database.models',
        'src.ocr',
        'src.ocr.ocr_engine',
        'src.ocr.image_preprocessor',
        'src.ocr.ocr_result',
        'src.detection',
        'src.detection.color_detector',
        'src.detection.result_detector',
        'src.detection.screen_types',
        'src.capture',
        'src.capture.screen_monitor',
        'src.capture.window_finder',
        'src.calibration',
        'src.calibration.calibration_manager',
        'src.calibration.roi_selector',
        'src.excel',
        'src.excel.excel_exporter',
        'src.reports',
        'src.reports.report_generator',
        'src.validation',
        'src.validation.validation_engine',
        'src.validation.validation_result',
        'src.utils',
        'src.utils.helpers',
        'src.utils.logger',
        'src.utils.file_manager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[
        # ── GUI frameworks we don't use ──
        'tkinter',
        '_tkinter',
        'PyQt5',
        'PyQt6',
        'wx',

        # ── GPU / CUDA — not needed for CPU-only build ──
        'torch.cuda',
        'torch.distributed',
        'torch.distributed.fsdp',
        'torch.distributed.pipeline',
        'torch.distributed.rpc',
        'torchaudio',
        'torchvision',
        'torchtext',

        # ── MASSIVE BLOAT — packages from global env, NOT used by BalanceLog ──
        'tensorflow',
        'tf_keras',
        'tensorboard',
        'jax',
        'jaxlib',
        'flax',
        'optax',
        'transformers',
        'huggingface_hub',
        'tokenizers',
        'safetensors',
        'sentencepiece',
        'onnx',
        'onnxruntime',
        'pyarrow',
        'av',
        'flask',
        'django',
        'fastapi',
        'uvicorn',
        'starlette',
        'aiohttp',
        'httpx',
        'boto3',
        'botocore',
        's3transfer',
        'google',
        'googleapiclient',
        'google_auth_httplib2',
        'google_auth_oauthlib',
        'grpc',
        'grpcio',
        'google.cloud',
        'google.api_core',
        'google.protobuf',
        'protobuf',
        'psycopg',
        'psycopg2',
        'psycopg_binary',
        'sqlalchemy',
        'redis',
        'celery',
        'h5py',
        'h2',
        'hpack',
        'hyperframe',
        'lxml',
        'nltk',
        'plotly',
        'skimage',
        'scikit_image',
        'sklearn',
        'scikit_learn',
        'scipy',
        'sympy',
        'networkx',
        'shapely',
        'pydantic',
        'pydantic_core',
        'tiktoken',
        'watchfiles',
        'websockets',
        'tornado',
        'cryptography',
        'bcrypt',
        'paramiko',
        'mcp',
        'opentelemetry',
        'hf_xet',
        'soundfile',
        '_soundfile_data',
        'greenlet',
        'optree',

        # ── Heavy scientific packages not needed ──
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',

        # ── Qt modules we don't use (saves ~100+ MB) ──
        'PySide6.QtWebEngine',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebChannel',
        'PySide6.QtQuick',
        'PySide6.QtQuick3D',
        'PySide6.QtQuickWidgets',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic',
        'PySide6.Qt3DAnimation',
        'PySide6.Qt3DExtras',
        'PySide6.QtDesigner',
        'PySide6.QtBluetooth',
        'PySide6.QtNfc',
        'PySide6.QtPositioning',
        'PySide6.QtLocation',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtRemoteObjects',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtTest',
        'PySide6.QtXml',
        'PySide6.QtSvgWidgets',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'PySide6.QtPdf',
        'PySide6.QtPdfWidgets',
        'PySide6.QtHelp',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtStateMachine',
        'PySide6.QtScxml',
        'PySide6.QtSql',

        # ── Other unnecessary modules ──
        'test',
        'unittest',
        # NOTE: Do NOT exclude 'distutils' — PyInstaller has an internal
        # hook that aliases it, and excluding it causes a ValueError.
        'setuptools',
        'pip',
        'ensurepip',
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
    icon=app_icon,
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
