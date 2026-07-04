# BalanceLog Pro

**Automated Balancing Record Digitization System**

Production-grade Windows desktop application for digitizing ABRO Dynamic Propeller Shaft Balancing Machine results. Replaces manual paper recording with reliable, offline, OCR-powered digital traceability.

---

## 🏭 Overview

BalanceLog Pro runs in parallel with the ABRO balancing software on a shop floor PC. It observes the screen, captures result pages, extracts data via OCR, validates values, and stores everything in a searchable database with Excel export.

**Key Principle:** This software NEVER modifies, injects into, automates, or interferes with the ABRO software. It only reads the screen.

## 🚀 Features

- **Screen Monitoring** — Captures only the ABRO window (not full desktop)
- **Calibration Wizard** — Draw ROI rectangles on screenshots to define data fields
- **Dual OCR Engine** — EasyOCR (primary) + Tesseract (fallback)
- **Smart Preprocessing** — 4 image pipelines for optimal OCR accuracy
- **Validation Engine** — Physical constraint checking with operator confirmation
- **SQLite Database** — Indexed, searchable, WAL-mode
- **Excel Export** — Professionally formatted with conditional highlighting
- **PDF Reports** — Daily/weekly/monthly with statistics
- **Industrial Dark Theme** — Premium UI designed for factory environments
- **100% Offline** — No internet connection required

## 📦 Installation

### Prerequisites
- Python 3.13+
- Windows 10/11

### Setup
```bash
# Clone or extract the project
cd BalanceLog

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Optional: Tesseract OCR
For fallback OCR, install Tesseract:
1. Download from https://github.com/UB-Mannheim/tesseract/wiki
2. Add to system PATH

## 🎯 Quick Start

1. **Launch** — Run `python main.py`
2. **Settings** — Go to Settings, click "Detect Windows" to find the ABRO software
3. **Calibration** — Go to Calibration, upload an ABRO result screenshot, draw ROI rectangles around each data field
4. **Monitor** — Click "Start Monitoring" on the Dashboard
5. **View Records** — Check the Records tab for captured data

## 🏗 Architecture

```
MVC Architecture with SOLID Principles

src/
├── capture/          Screen capture & window management
├── detection/        Result page detection (OpenCV)
├── ocr/              OCR extraction (EasyOCR + Tesseract)
├── calibration/      ROI definition & management
├── validation/       Data validation engine
├── database/         SQLite data layer
├── excel/            Excel export (openpyxl)
├── reports/          Report generation (Excel/CSV/PDF)
├── ui/               PySide6 UI pages
├── config/           Configuration management
├── utils/            Logging, file management, helpers
├── assets/           Icons and resources
└── logs/             Log files
```

## 📊 Data Fields Captured

| Field | Type | Description |
|-------|------|-------------|
| Punching Number | Text | Part identifier |
| Tube Length | Float (mm) | Shaft tube length |
| Type | Enum | Front / Rear |
| Initial Left/Right | Float | Initial imbalance values |
| Initial Left/Right Angle | Float (°) | Imbalance angles |
| Weight Addition L/R | Float | Correction weights added |
| After Correction L/R | Float | Post-correction values |
| OCR Confidence | Float (%) | Extraction accuracy |

## 📁 Output Structure

```
Balancing_Records/
├── 2024-01-15/
│   ├── Screenshots/
│   │   └── 14-30-45.png
│   ├── Excel/
│   │   └── Balancing_Record_2024-01-15.xlsx
│   └── Reports/
├── Database/
│   └── balancing.db
└── Logs/
    ├── app.log
    ├── ocr.log
    └── error.log
```

## 🔧 Build Executable

```bash
pyinstaller build.spec
```

The executable will be in `dist/BalanceLogPro/`.

## 📋 Tech Stack

| Component | Technology |
|-----------|-----------|
| UI | PySide6 |
| Computer Vision | OpenCV |
| OCR (Primary) | EasyOCR |
| OCR (Fallback) | Tesseract |
| Screen Capture | mss |
| Database | SQLite |
| Excel | openpyxl |
| PDF | reportlab |
| Data | pandas, NumPy |
| Build | PyInstaller |

## 🔮 Future Roadmap

- Barcode/QR scanner integration
- PLC communication (OPC UA / Modbus)
- REST API for MES integration
- User login & role management
- Cloud backup
- AI anomaly detection

---

**BalanceLog Pro** — Reliable digital traceability for every balancing operation.
