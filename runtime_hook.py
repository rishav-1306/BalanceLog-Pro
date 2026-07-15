"""
BalanceLog Pro — PyInstaller Runtime Hook

This script executes BEFORE main.py when running as a frozen .exe.
It configures the environment to ensure:
  1. CPU-only PyTorch (no CUDA/GPU)
  2. Offline mode (no network calls for model downloads)
  3. EasyOCR uses bundled models, not user home directory
  4. Suppresses irrelevant warnings in the packaged build
"""

import os
import sys

# ── Force CPU-only mode ─────────────────────────────────────────────────────
# Must be set before torch is imported anywhere (EasyOCR triggers it).
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TORCH_CUDA_ARCH_LIST"] = ""

# ── Offline mode — block all network attempts ──────────────────────────────
# Some libraries (torch.hub, easyocr) try to download models on first run.
# We bundle everything, so network access is never needed.
os.environ["NO_PROXY"] = "*"
os.environ["TORCH_HOME"] = os.path.join(
    os.environ.get("TEMP", os.path.expanduser("~")), "BalanceLogPro_torch_cache"
)
os.environ["TORCH_HUB_DIR"] = os.environ["TORCH_HOME"]

# ── EasyOCR model path ─────────────────────────────────────────────────────
# Redirect EasyOCR to use the bundled model directory inside the exe package
# instead of trying to download to ~/.EasyOCR/model/
if getattr(sys, "frozen", False):
    _bundle_dir = sys._MEIPASS  # PyInstaller temp extraction folder
    _easyocr_model_dir = os.path.join(_bundle_dir, "EasyOCR")
    os.environ["EASYOCR_MODULE_PATH"] = _easyocr_model_dir

# ── Suppress noisy warnings ────────────────────────────────────────────────
# These clutter the console in frozen builds and confuse end users.
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow warnings (if any)

import warnings
warnings.filterwarnings("ignore")
