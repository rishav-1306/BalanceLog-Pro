"""
prepare_easyocr.py — Run this ONCE on your dev machine (with internet)
before building the exe.

It downloads the EasyOCR English language model to:
    C:\\Users\\<you>\\.EasyOCR\\model\\

Those files are then automatically bundled by build.spec so the packaged
app works on machines with no internet.

Usage:
    python prepare_easyocr.py
"""

import sys

def main():
    print("Downloading EasyOCR English model (requires internet)...")
    print("This only needs to be done once before building the exe.\n")

    try:
        import easyocr
    except ImportError:
        print("ERROR: easyocr is not installed.")
        print("Run:  pip install easyocr")
        sys.exit(1)

    # Creating a Reader forces the model download
    print("Initialising EasyOCR reader for language: en")
    reader = easyocr.Reader(["en"], gpu=False, verbose=True)
    print("\nModel download complete.")

    from pathlib import Path
    model_dir = Path.home() / ".EasyOCR" / "model"
    files = list(model_dir.iterdir()) if model_dir.exists() else []
    print(f"\nModel files stored in: {model_dir}")
    for f in files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name}  ({size_mb:.1f} MB)")

    print("\nYou can now run:  pyinstaller build.spec --clean")


if __name__ == "__main__":
    main()
