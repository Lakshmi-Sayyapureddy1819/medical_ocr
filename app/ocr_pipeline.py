import cv2
import numpy as np
import easyocr
import torch

from .pii_extractor import extract_pii_fixed

# ---- make PyTorch + EasyOCR stable on Windows (no semaphore crash) ----
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

# ---- EasyOCR reader (NO workers argument) ----
reader = easyocr.Reader(['en'], gpu=False, verbose=False)


def preprocess_image(img_bgr: np.ndarray) -> np.ndarray:
    """
    CLAHE + bilateral filter.
    Good for faint handwriting and low contrast scans.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)

    return filtered


def crop_header_region(img_bgr: np.ndarray, top_ratio: float = 0.35) -> np.ndarray:
    """
    Crop only the top part of the page (where PII header lives).
    """
    h, w = img_bgr.shape[:2]
    h_top = int(h * top_ratio)
    return img_bgr[:h_top, :, :]


def run_dual_ocr(img_bgr: np.ndarray):
    """
    Run OCR twice: on grayscale and enhanced.
    Combine results.
    """
    enhanced = preprocess_image(img_bgr)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    r1 = reader.readtext(gray)
    r2 = reader.readtext(enhanced)

    return r1 + r2


def redact_image(img_bgr: np.ndarray, ocr_results, pii_dict):
    """
    Fill black rectangles over any OCR box whose text contains PII value.
    """
    redacted = img_bgr.copy()
    pii_vals = [str(v).lower() for v in pii_dict.values() if v]

    for (bbox, text, conf) in ocr_results:
        t_low = text.lower()
        if any(v in t_low for v in pii_vals):
            pts = np.array(bbox, np.int32)
            cv2.fillPoly(redacted, [pts], (0, 0, 0))

    return redacted


def process_page(img_bgr: np.ndarray):
    """
    Full OCR + PII pipeline for one page image (BGR).
    """
    # 1. OCR on full page
    full_results = run_dual_ocr(img_bgr)
    full_text = "\n".join([r[1] for r in full_results])

    # 2. OCR focused on header region (top of page)
    header_bgr = crop_header_region(img_bgr)
    header_results = run_dual_ocr(header_bgr)
    header_text = "\n".join([r[1] for r in header_results])

    # 3. Combine header + full text
    combined_text = header_text + "\n" + full_text

    pii = extract_pii_fixed(combined_text)

    # 4. Redact
    redacted = redact_image(img_bgr, full_results, pii)

    return {
        "text": combined_text,
        "pii": pii,
        "redacted": redacted,
        "ocr_results": full_results,
    }
