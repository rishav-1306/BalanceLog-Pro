"""
BalanceLog Pro - OCR Engine

Dual-engine OCR system using EasyOCR (primary) and Tesseract (fallback).
Extracts text from predefined ROI regions with confidence scoring,
automatic retry with different preprocessing if confidence is low.
"""

import time
import numpy as np
from typing import Optional, Dict, List

from .image_preprocessor import ImagePreprocessor
from .ocr_result import OCRResult, FieldExtractionResult, ExtractionSummary
from src.config.config_manager import ConfigManager
from src.config.constants import (
    OCR_EXTRACT_FIELDS, ROI_FIELD_LABELS,
    OCR_MAX_RETRY_ATTEMPTS, DEFAULT_OCR_ENGINE,
)
from src.utils.logger import get_logger
from src.utils.helpers import safe_float

logger = get_logger("ocr")


class OCREngine:
    """
    Dual-engine OCR system for extracting balancing data from screenshots.

    Features:
    - Primary: EasyOCR (CPU-only — no GPU required)
    - Fallback: Tesseract OCR
    - Only OCRs predefined ROI regions (never the whole screen)
    - Automatic retry with different preprocessing if confidence is low
    - Per-field confidence scoring
    - Configurable language and confidence thresholds
    """

    def __init__(self) -> None:
        self._config = ConfigManager()
        self._preprocessor = ImagePreprocessor(
            scale_factor=self._config.get("ocr.scale_factor", 2.0)
        )
        self._easyocr_reader = None
        self._tesseract_available = False
        self._engine = self._config.get("ocr.engine", DEFAULT_OCR_ENGINE)
        self._confidence_threshold = self._config.get("ocr.confidence_threshold", 0.75)
        self._language = self._config.get("ocr.language", "en")

        self._init_engines()

    def _init_engines(self) -> None:
        """Initialize OCR engines lazily."""
        # EasyOCR is loaded on first use to save startup time
        # Tesseract availability is checked once
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
            logger.info("Tesseract OCR available")
        except Exception:
            self._tesseract_available = False
            logger.info("Tesseract OCR not available — EasyOCR only")

    def _get_easyocr_reader(self):
        """Lazily initialize EasyOCR reader."""
        if self._easyocr_reader is None:
            try:
                import easyocr
                self._easyocr_reader = easyocr.Reader(
                    [self._language],
                    gpu=False,  # CPU mode for reliability on production PCs
                    verbose=False,
                )
                logger.info("EasyOCR reader initialized (lang: %s)", self._language)
            except Exception as e:
                logger.error("Failed to initialize EasyOCR: %s", e)
                raise
        return self._easyocr_reader

    # ─────────────────────────────────────────────────────────
    # Main Interface
    # ─────────────────────────────────────────────────────────
    def extract_all_fields(self, image: np.ndarray) -> ExtractionSummary:
        """
        Extract all data fields from a result screen screenshot.

        Uses calibrated ROI coordinates to crop each field region,
        then runs OCR on each cropped region individually.

        Args:
            image: Full BGR screenshot of the ABRO result screen

        Returns:
            ExtractionSummary with per-field results and overall confidence
        """
        start_time = time.time()
        summary = ExtractionSummary()

        rois = self._config.get_all_rois()
        if not rois:
            logger.warning("No ROI configuration found — calibration required")
            summary.extraction_time_ms = (time.time() - start_time) * 1000
            return summary

        for field_name in OCR_EXTRACT_FIELDS:
            roi = rois.get(field_name)
            if roi is None:
                logger.debug("No ROI configured for field: %s", field_name)
                continue

            try:
                # Crop the ROI region
                roi_image = ImagePreprocessor.crop_roi(image, roi)
                if roi_image.size == 0:
                    logger.warning("Empty ROI crop for field: %s", field_name)
                    continue

                # Extract text with retry
                result = self._extract_with_retry(roi_image, field_name)

                # Create field result
                field_result = FieldExtractionResult(
                    field_name=field_name,
                    field_label=ROI_FIELD_LABELS.get(field_name, field_name),
                    raw_text=result.text,
                    parsed_value=self._parse_field_value(field_name, result.text),
                    confidence=result.confidence,
                    engine_used=result.engine_used,
                )

                summary.fields[field_name] = field_result
                logger.debug("Extracted %s: '%s' (%.2f)", field_name, result.text, result.confidence)

            except Exception as e:
                logger.error("Error extracting field %s: %s", field_name, e)
                summary.fields[field_name] = FieldExtractionResult(
                    field_name=field_name,
                    field_label=ROI_FIELD_LABELS.get(field_name, field_name),
                    raw_text="",
                    parsed_value=None,
                    confidence=0.0,
                    is_valid=False,
                    error_message=str(e),
                )

        summary.extraction_time_ms = (time.time() - start_time) * 1000
        summary.compute_summary()

        logger.info(
            "Extraction complete: %d/%d fields, avg confidence: %.2f, time: %.0fms",
            summary.valid_fields, summary.total_fields,
            summary.overall_confidence, summary.extraction_time_ms,
        )

        return summary

    def extract_text(self, image: np.ndarray, roi: Optional[dict] = None) -> OCRResult:
        """
        Extract text from an image or a specific ROI.

        Args:
            image: Input BGR image
            roi: Optional ROI dict {"x": %, "y": %, "w": %, "h": %}

        Returns:
            OCRResult with extracted text and confidence
        """
        if roi is not None:
            image = ImagePreprocessor.crop_roi(image, roi)

        return self._extract_with_retry(image, "generic")

    # ─────────────────────────────────────────────────────────
    # Internal OCR
    # ─────────────────────────────────────────────────────────
    def _extract_with_retry(self, image: np.ndarray, field_name: str) -> OCRResult:
        """
        Try OCR with multiple preprocessing pipelines until confidence is adequate.

        1. Try default preprocessing
        2. If confidence < threshold, try other pipelines
        3. If all fail, try fallback engine (Tesseract)
        4. Return the best result across all attempts
        """
        best_result = OCRResult()
        pipelines = self._preprocessor.preprocess_multi(image)

        for pipeline_name, processed in pipelines:
            result = self._run_ocr(processed, self._engine)
            result.preprocessing = pipeline_name

            if result.confidence > best_result.confidence:
                best_result = result

            if result.confidence >= self._confidence_threshold:
                return result

        # Try fallback engine if primary didn't meet threshold
        if best_result.confidence < self._confidence_threshold and self._tesseract_available:
            fallback_engine = "tesseract" if self._engine == "easyocr" else "easyocr"
            for pipeline_name, processed in pipelines[:2]:  # Try first 2 pipelines
                result = self._run_ocr(processed, fallback_engine)
                result.preprocessing = pipeline_name
                if result.confidence > best_result.confidence:
                    best_result = result
                if result.confidence >= self._confidence_threshold:
                    return result

        return best_result

    def _run_ocr(self, image: np.ndarray, engine: str = "easyocr") -> OCRResult:
        """Run OCR on a preprocessed image using the specified engine."""
        if engine == "easyocr":
            return self._run_easyocr(image)
        elif engine == "tesseract":
            return self._run_tesseract(image)
        else:
            return self._run_easyocr(image)

    def _run_easyocr(self, image: np.ndarray) -> OCRResult:
        """Run EasyOCR on the image."""
        try:
            reader = self._get_easyocr_reader()
            results = reader.readtext(image, detail=1)

            if not results:
                return OCRResult(text="", confidence=0.0, engine_used="easyocr")

            # Combine all detected text regions
            texts = []
            confidences = []
            for bbox, text, conf in results:
                texts.append(text)
                confidences.append(conf)

            combined_text = " ".join(texts).strip()
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                engine_used="easyocr",
            )

        except Exception as e:
            logger.error("EasyOCR error: %s", e)
            return OCRResult(text="", confidence=0.0, engine_used="easyocr")

    def _run_tesseract(self, image: np.ndarray) -> OCRResult:
        """Run Tesseract OCR on the image."""
        if not self._tesseract_available:
            return OCRResult(text="", confidence=0.0, engine_used="tesseract")

        try:
            import pytesseract

            # Use appropriate config for numeric vs text fields
            config = "--psm 7 --oem 3"  # Single line mode
            data = pytesseract.image_to_data(
                image, config=config, output_type=pytesseract.Output.DICT
            )

            texts = []
            confidences = []
            for i, text in enumerate(data["text"]):
                conf = int(data["conf"][i])
                if conf > 0 and text.strip():
                    texts.append(text.strip())
                    confidences.append(conf / 100.0)

            combined_text = " ".join(texts).strip()
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                engine_used="tesseract",
            )

        except Exception as e:
            logger.error("Tesseract error: %s", e)
            return OCRResult(text="", confidence=0.0, engine_used="tesseract")

    # ─────────────────────────────────────────────────────────
    # Field Parsing
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _parse_field_value(field_name: str, raw_text: str):
        """Parse raw OCR text into the appropriate data type for the field."""
        if not raw_text or not raw_text.strip():
            return None

        text = raw_text.strip()

        # String fields
        if field_name in ("punching_number", "shaft_type", "rotor_no"):
            return text

        # Numeric fields — clean common OCR artifacts for numbers
        # Remove any non-numeric chars except +, -, .
        cleaned = text.replace(",", ".")
        return safe_float(cleaned, default=0.0)

    # ─────────────────────────────────────────────────────────
    # Configuration Update
    # ─────────────────────────────────────────────────────────
    def update_config(self) -> None:
        """Reload configuration after settings change."""
        self._engine = self._config.get("ocr.engine", DEFAULT_OCR_ENGINE)
        self._confidence_threshold = self._config.get("ocr.confidence_threshold", 0.75)
        new_lang = self._config.get("ocr.language", "en")

        if new_lang != self._language:
            self._language = new_lang
            self._easyocr_reader = None  # Force re-initialization with new language

        self._preprocessor = ImagePreprocessor(
            scale_factor=self._config.get("ocr.scale_factor", 2.0)
        )
