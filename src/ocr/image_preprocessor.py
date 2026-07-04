"""
BalanceLog Pro - Image Preprocessor

Preprocessing pipeline for OCR optimization. Applies scaling, denoising,
contrast enhancement, thresholding, deskewing, and sharpening to improve
OCR accuracy on ABRO software screenshots.
"""

import cv2
import numpy as np
from typing import List, Tuple

from src.utils.logger import get_logger

logger = get_logger("ocr")


class ImagePreprocessor:
    """
    Image preprocessing pipeline for OCR optimization.

    Applies a sequence of transformations to maximize OCR accuracy:
    1. Scale up (higher resolution → better character recognition)
    2. Denoise (reduce noise artifacts)
    3. Enhance contrast (CLAHE)
    4. Convert to grayscale
    5. Apply adaptive thresholding
    6. Deskew (correct slight rotation)
    7. Sharpen

    The pipeline can be customized per field or run in auto mode
    which tries multiple preprocessing strategies and picks the best.
    """

    def __init__(self, scale_factor: float = 2.0) -> None:
        self._scale_factor = scale_factor

    # ─────────────────────────────────────────────────────────
    # Full Pipeline
    # ─────────────────────────────────────────────────────────
    def preprocess(self, image: np.ndarray, pipeline: str = "default") -> np.ndarray:
        """
        Apply the preprocessing pipeline to an image.

        Args:
            image: Input BGR image (ROI crop)
            pipeline: Pipeline name — 'default', 'aggressive', 'light', 'numeric'

        Returns:
            Preprocessed grayscale image optimized for OCR
        """
        if pipeline == "light":
            return self._pipeline_light(image)
        elif pipeline == "aggressive":
            return self._pipeline_aggressive(image)
        elif pipeline == "numeric":
            return self._pipeline_numeric(image)
        else:
            return self._pipeline_default(image)

    def preprocess_multi(self, image: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """
        Apply multiple preprocessing strategies and return all results.

        Used for automatic retry when OCR confidence is low.
        Returns list of (pipeline_name, processed_image) tuples.
        """
        results = []
        for pipeline in ("default", "light", "aggressive", "numeric"):
            try:
                processed = self.preprocess(image, pipeline)
                results.append((pipeline, processed))
            except Exception as e:
                logger.warning("Pipeline '%s' failed: %s", pipeline, e)
        return results

    # ─────────────────────────────────────────────────────────
    # Pipelines
    # ─────────────────────────────────────────────────────────
    def _pipeline_default(self, image: np.ndarray) -> np.ndarray:
        """Default pipeline: scale → denoise → contrast → threshold."""
        img = self.scale(image, self._scale_factor)
        img = self.denoise(img)
        img = self.enhance_contrast(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        gray = self.threshold_adaptive(gray)
        gray = self.deskew(gray)
        return gray

    def _pipeline_light(self, image: np.ndarray) -> np.ndarray:
        """Light pipeline: scale → grayscale → otsu threshold."""
        img = self.scale(image, self._scale_factor)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        gray = self.threshold_otsu(gray)
        return gray

    def _pipeline_aggressive(self, image: np.ndarray) -> np.ndarray:
        """Aggressive pipeline: all processing steps for difficult images."""
        img = self.scale(image, self._scale_factor * 1.5)
        img = self.denoise(img, strength=15)
        img = self.enhance_contrast(img)
        img = self.sharpen(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        gray = self.threshold_adaptive(gray)
        gray = self.deskew(gray)
        # Morphological operations to clean up
        kernel = np.ones((2, 2), np.uint8)
        gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        return gray

    def _pipeline_numeric(self, image: np.ndarray) -> np.ndarray:
        """Optimized for numeric values (weights, angles)."""
        img = self.scale(image, self._scale_factor * 1.2)
        img = self.denoise(img, strength=8)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        gray = self.enhance_contrast_gray(gray)
        gray = self.threshold_otsu(gray)
        # Dilate slightly to connect broken digits
        kernel = np.ones((2, 2), np.uint8)
        gray = cv2.dilate(gray, kernel, iterations=1)
        return gray

    # ─────────────────────────────────────────────────────────
    # Individual Operations
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def scale(image: np.ndarray, factor: float) -> np.ndarray:
        """Scale image by factor for better OCR resolution."""
        if factor <= 0 or factor == 1.0:
            return image
        width = int(image.shape[1] * factor)
        height = int(image.shape[0] * factor)
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_CUBIC)

    @staticmethod
    def denoise(image: np.ndarray, strength: int = 10) -> np.ndarray:
        """Apply bilateral filter for edge-preserving denoising."""
        return cv2.bilateralFilter(image, 9, strength, strength)

    @staticmethod
    def enhance_contrast(image: np.ndarray) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        if len(image.shape) == 2:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    @staticmethod
    def enhance_contrast_gray(gray: np.ndarray) -> np.ndarray:
        """Apply CLAHE to a grayscale image."""
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @staticmethod
    def threshold_adaptive(gray: np.ndarray) -> np.ndarray:
        """Apply adaptive thresholding for varying lighting conditions."""
        return cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2,
        )

    @staticmethod
    def threshold_otsu(gray: np.ndarray) -> np.ndarray:
        """Apply Otsu's thresholding for bimodal images."""
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    @staticmethod
    def deskew(gray: np.ndarray) -> np.ndarray:
        """Correct slight rotation using minimum area rectangle."""
        coords = np.column_stack(np.where(gray > 0))
        if len(coords) < 10:
            return gray

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Only deskew if the angle is small
        if abs(angle) > 10 or abs(angle) < 0.5:
            return gray

        h, w = gray.shape
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            gray, matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated

    @staticmethod
    def sharpen(image: np.ndarray) -> np.ndarray:
        """Apply unsharp masking to sharpen the image."""
        gaussian = cv2.GaussianBlur(image, (0, 0), 3)
        return cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)

    @staticmethod
    def crop_roi(image: np.ndarray, roi: dict) -> np.ndarray:
        """
        Crop an ROI from the image using percentage-based coordinates.

        ROI format: {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05}
        where values are percentages of image dimensions (0.0 to 1.0).
        """
        h, w = image.shape[:2]
        x1 = int(roi["x"] * w)
        y1 = int(roi["y"] * h)
        x2 = int((roi["x"] + roi["w"]) * w)
        y2 = int((roi["y"] + roi["h"]) * h)

        # Clamp to image bounds
        x1 = max(0, min(x1, w))
        y1 = max(0, min(y1, h))
        x2 = max(x1, min(x2, w))
        y2 = max(y1, min(y2, h))

        return image[y1:y2, x1:x2]
