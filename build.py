"""
BalanceLog Pro — One-Click Build Script

Automates the entire process of building a standalone Windows executable.

Usage:
    python build.py

Steps performed:
    1. Validates that all required dependencies are installed
    2. Downloads EasyOCR models if not already present
    3. Generates app icon if not present
    4. Runs PyInstaller with the build spec
    5. Cleans up unnecessary files from the output
    6. Reports final output size and location
"""

import sys
import os
import shutil
import subprocess
import time
import io
from pathlib import Path

# Force UTF-8 output on Windows to handle Unicode progress bars from EasyOCR
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

# ── Configuration ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
SPEC_FILE = PROJECT_ROOT / "build.spec"
DIST_DIR = PROJECT_ROOT / "dist" / "BalanceLogPro"
BUILD_DIR = PROJECT_ROOT / "build"
ICON_PATH = PROJECT_ROOT / "src" / "assets" / "icon.ico"
EASYOCR_MODEL_DIR = Path.home() / ".EasyOCR" / "model"

# ANSI colors for terminal output
class C:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def banner():
    print(f"""
{C.CYAN}{C.BOLD}+======================================================+
|          BalanceLog Pro -- Build System               |
|          Standalone Offline Executable                |
+======================================================+{C.END}
""")


def step(msg: str):
    print(f"\n{C.BOLD}{C.CYAN}>> {msg}{C.END}")


def ok(msg: str):
    print(f"  {C.GREEN}[OK] {msg}{C.END}")


def warn(msg: str):
    print(f"  {C.YELLOW}[WARN] {msg}{C.END}")


def fail(msg: str):
    print(f"  {C.RED}[FAIL] {msg}{C.END}")


def fatal(msg: str):
    fail(msg)
    print(f"\n{C.RED}{C.BOLD}Build failed.{C.END}")
    sys.exit(1)


# ── Step 1: Check Dependencies ────────────────────────────────────────────
def check_dependencies():
    step("Checking required dependencies...")

    required = [
        ("PySide6", "PySide6"),
        ("cv2", "opencv-python-headless"),
        ("numpy", "numpy"),
        ("easyocr", "easyocr"),
        ("torch", "torch"),
        ("mss", "mss"),
        ("PIL", "Pillow"),
        ("pandas", "pandas"),
        ("openpyxl", "openpyxl"),
        ("reportlab", "reportlab"),
        ("PyInstaller", "pyinstaller"),
    ]

    missing = []
    for module, pip_name in required:
        try:
            __import__(module)
            ok(f"{pip_name}")
        except ImportError:
            fail(f"{pip_name} — NOT INSTALLED")
            missing.append(pip_name)

    # Optional: pywin32
    try:
        __import__("win32gui")
        ok("pywin32")
    except ImportError:
        warn("pywin32 -- not installed (Windows API features may be limited)")

    if missing:
        fatal(
            f"Missing packages: {', '.join(missing)}\n"
            f"  Run: pip install {' '.join(missing)}"
        )


# ── Step 2: Download EasyOCR Models ───────────────────────────────────────
def download_easyocr_models():
    step("Checking EasyOCR models...")

    if EASYOCR_MODEL_DIR.exists() and any(EASYOCR_MODEL_DIR.iterdir()):
        files = list(EASYOCR_MODEL_DIR.iterdir())
        total_mb = sum(f.stat().st_size for f in files if f.is_file()) / (1024 * 1024)
        ok(f"Models found at {EASYOCR_MODEL_DIR} ({total_mb:.1f} MB, {len(files)} files)")
        for f in files:
            if f.is_file():
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"    {f.name}  ({size_mb:.1f} MB)")
        return

    warn("EasyOCR models not found -- downloading now (requires internet)...")
    print(f"    Model directory: {EASYOCR_MODEL_DIR}")

    try:
        import easyocr
        reader = easyocr.Reader(["en"], gpu=False, verbose=True)
        ok("EasyOCR models downloaded successfully")

        # Verify
        if EASYOCR_MODEL_DIR.exists():
            files = list(EASYOCR_MODEL_DIR.iterdir())
            total_mb = sum(f.stat().st_size for f in files if f.is_file()) / (1024 * 1024)
            ok(f"Models saved: {total_mb:.1f} MB ({len(files)} files)")
        else:
            fatal("Models directory was not created -- check EasyOCR installation")
    except Exception as e:
        fatal(f"Failed to download EasyOCR models: {e}")


# ── Step 3: Generate App Icon ─────────────────────────────────────────────
def generate_icon():
    step("Checking app icon...")

    if ICON_PATH.exists():
        ok(f"Icon found: {ICON_PATH}")
        return

    warn("No icon.ico found — generating a default icon...")

    try:
        from PIL import Image, ImageDraw, ImageFont

        sizes = [256, 128, 64, 48, 32, 16]
        images = []

        for size in sizes:
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Background: rounded square with gradient-like color
            bg_color = (55, 37, 73)  # Colors.PRIMARY = #372549
            draw.rounded_rectangle(
                [(0, 0), (size - 1, size - 1)],
                radius=size // 6,
                fill=bg_color,
            )

            # Draw "BL" text centered
            text = "BL"
            font_size = int(size * 0.45)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = (size - tw) // 2
            ty = (size - th) // 2 - bbox[1]
            draw.text((tx, ty), text, fill=(255, 255, 255), font=font)

            images.append(img)

        # Save as .ico with multiple sizes
        ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
        images[0].save(
            str(ICON_PATH),
            format="ICO",
            sizes=[(s, s) for s in sizes],
            append_images=images[1:],
        )
        ok(f"Icon generated: {ICON_PATH}")

    except Exception as e:
        warn(f"Could not generate icon: {e}")
        warn("Build will proceed without an icon")


# ── Step 4: Run PyInstaller ───────────────────────────────────────────────
def run_pyinstaller():
    step("Building executable with PyInstaller...")
    print(f"    Spec file: {SPEC_FILE}")
    print(f"    Output:    {DIST_DIR}")

    # Clean previous build
    if DIST_DIR.exists():
        warn(f"Removing previous build: {DIST_DIR}")
        shutil.rmtree(DIST_DIR, ignore_errors=True)

    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    start_time = time.time()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--clean",
        "--noconfirm",
        f"--distpath={PROJECT_ROOT / 'dist'}",
        f"--workpath={BUILD_DIR}",
    ]

    print(f"\n    Running: {' '.join(cmd)}\n")
    print(f"\n    {'-' * 60}")

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
    )

    elapsed = time.time() - start_time

    if result.returncode != 0:
        fatal(f"PyInstaller failed with exit code {result.returncode}")

    ok(f"PyInstaller completed in {elapsed:.0f}s")


# ── Step 5: Clean Up Output ──────────────────────────────────────────────
def cleanup_output():
    step("Cleaning up build output...")

    if not DIST_DIR.exists():
        fatal(f"Output directory not found: {DIST_DIR}")

    internal_dir = DIST_DIR / "_internal"

    # ── Remove unnecessary Qt DLLs ──
    qt_bloat = [
        "Qt6WebEngine*",
        "Qt6Quick*",
        "Qt6Qml*",
        "Qt6Designer*",
        "Qt63D*",
        "Qt6Bluetooth*",
        "Qt6Nfc*",
        "Qt6Multimedia*",
        "Qt6Sensors*",
        "Qt6SerialPort*",
        "Qt6Test*",
        "opengl32sw.dll",
        "d3dcompiler_47.dll",
    ]

    removed_mb = 0.0

    def safe_delete_file(f):
        nonlocal removed_mb
        if f.is_file():
            size_mb = f.stat().st_size / (1024 * 1024)
            try:
                f.unlink()
                removed_mb += size_mb
            except PermissionError:
                pass

    def safe_delete_dir(d):
        nonlocal removed_mb
        if d.is_dir():
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            try:
                shutil.rmtree(d, ignore_errors=True)
                removed_mb += size / (1024 * 1024)
            except Exception:
                pass

    for pattern in qt_bloat:
        for f in DIST_DIR.rglob(pattern):
            safe_delete_file(f)

    # ── Remove CUDA DLLs from torch (saves ~2-3 GB) ──
    # The installed torch is cu121 but we only need CPU.
    cuda_patterns = [
        "cublas*", "cudart*", "cudnn*", "cufft*", "curand*",
        "cusolver*", "cusparse*", "nccl*", "nvrtc*", "nvJitLink*",
        "cupti*", "nvfatbin*", "nvvm*", "triton*",
        "torch_cuda*", "c10_cuda*",
    ]
    for pattern in cuda_patterns:
        for f in DIST_DIR.rglob(pattern):
            safe_delete_file(f)

    # ── Remove bloat directories that may have slipped through excludes ──
    bloat_dirs = [
        "tensorflow", "tf_keras", "tensorboard",
        "jax", "jaxlib", "flax", "optax",
        "transformers", "huggingface_hub",
        "tokenizers", "safetensors", "sentencepiece",
        "onnxruntime", "onnx",
        "pyarrow", "pyarrow.libs",
        "av", "av.libs",
        "flask", "django", "fastapi", "starlette", "uvicorn",
        "aiohttp", "httpx",
        "boto3", "botocore", "s3transfer",
        "google", "googleapiclient",
        "grpc", "grpcio",
        "psycopg", "psycopg2", "psycopg_binary",
        "psycopg_binary.libs", "psycopg2_binary.libs",
        "sqlalchemy",
        "redis", "celery",
        "h5py", "h2",
        "lxml", "nltk",
        "plotly", "skimage",
        "sklearn", "scipy", "sympy", "networkx",
        "shapely", "Shapely.libs",
        "pydantic", "pydantic_core",
        "tiktoken", "hf_xet",
        "watchfiles", "websockets", "tornado",
        "cryptography", "bcrypt", "paramiko",
        "mcp", "opentelemetry",
        "_soundfile_data", "soundfile",
        "greenlet", "optree",
        "orjson",
        # dist-info directories (metadata we don't need)
    ]
    if internal_dir.exists():
        for dirname in bloat_dirs:
            safe_delete_dir(internal_dir / dirname)
        # Remove all .dist-info directories for excluded packages
        for d in internal_dir.glob("*.dist-info"):
            if any(pkg in d.name.lower() for pkg in [
                "tensorflow", "jax", "torch-2.5.1+cu121", "torchvision",
                "transformers", "onnx", "pyarrow", "flask", "django",
                "boto", "google", "grpc", "psycopg", "redis", "celery",
                "plotly", "sklearn", "scipy", "shapely", "pydantic",
                "cryptography", "tornado", "websocket", "aiohttp",
                "h5py", "tiktoken", "safetensors", "tokenizers",
                "huggingface", "nltk", "lxml", "sqlalchemy", "hf_xet",
                "sentencepiece", "watchfiles", "bcrypt", "optree",
                "greenlet", "starlette", "uvicorn", "httpx", "av-",
            ]):
                safe_delete_dir(d)

    # ── Remove torch CUDA-specific subdirectories ──
    torch_dir = internal_dir / "torch" if internal_dir.exists() else None
    if torch_dir and torch_dir.is_dir():
        cuda_subdirs = ["_C", "_inductor", "_dynamo", "_functorch",
                        "distributed", "cuda"]
        for subdir in cuda_subdirs:
            safe_delete_dir(torch_dir / subdir)

    # Remove __pycache__ directories
    for cache_dir in DIST_DIR.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir, ignore_errors=True)

    if removed_mb > 0:
        ok(f"Removed {removed_mb:.1f} MB of unnecessary files")
    else:
        ok("No unnecessary files to remove")


# ── Step 6: Report Results ────────────────────────────────────────────────
def report_results():
    step("Build Summary")

    if not DIST_DIR.exists():
        fatal(f"Output directory not found: {DIST_DIR}")

    # Calculate total size
    total_size = 0
    file_count = 0
    for f in DIST_DIR.rglob("*"):
        if f.is_file():
            total_size += f.stat().st_size
            file_count += 1

    total_mb = total_size / (1024 * 1024)

    exe_path = DIST_DIR / "BalanceLogPro.exe"
    exe_exists = exe_path.exists()
    exe_size_mb = exe_path.stat().st_size / (1024 * 1024) if exe_exists else 0

    print(f"""
{C.GREEN}{C.BOLD}+======================================================+
|                  BUILD SUCCESSFUL                    |
+======================================================+{C.END}

  {C.BOLD}Output folder:{C.END}  {DIST_DIR}
  {C.BOLD}Executable:{C.END}     {exe_path if exe_exists else 'NOT FOUND'}
  {C.BOLD}Exe size:{C.END}       {exe_size_mb:.1f} MB
  {C.BOLD}Total size:{C.END}     {total_mb:.1f} MB ({file_count} files)

  {C.CYAN}To deploy:{C.END}
    1. Copy the entire {C.BOLD}dist\\BalanceLogPro\\{C.END} folder to the target PC
    2. Double-click {C.BOLD}BalanceLogPro.exe{C.END} to run
    3. No Python, no internet, no dependencies required!
""")


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    banner()

    check_dependencies()
    download_easyocr_models()
    generate_icon()
    run_pyinstaller()
    cleanup_output()
    report_results()


if __name__ == "__main__":
    main()
