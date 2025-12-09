import cv2
import numpy as np
import easyocr

from .pii_extractor import extract_pii_fixed


reader = easyocr.Reader(['en'], gpu=False)  # no API key needed


# --------------------------------------------
# PREPROCESSING tuned for SUM Hospital notes
# --------------------------------------------
def preprocess_image(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # CLAHE dramatically improves faint handwriting
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # bilateral filter preserves edges while denoising
    filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)

    return filtered


# --------------------------------------------
# DUAL OCR (best for this dataset)
# --------------------------------------------
def run_dual_ocr(img_bgr):
    enhanced = preprocess_image(img_bgr)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    r1 = reader.readtext(gray)
    r2 = reader.readtext(enhanced)

    return r1 + r2


# --------------------------------------------
# REDACTION
# --------------------------------------------
def redact_image(img_bgr, ocr_results, pii):
    redacted = img_bgr.copy()
    pii_values = [str(v).lower() for v in pii.values() if v]

    for (bbox, text, conf) in ocr_results:
        if any(v in text.lower() for v in pii_values):
            pts = np.array(bbox, np.int32)
            cv2.fillPoly(redacted, [pts], (0, 0, 0))

    return redacted


# --------------------------------------------
# FULL PIPELINE
# --------------------------------------------
def process_page(img_bgr):
    # OCR
    ocr_results = run_dual_ocr(img_bgr)

    # Collect text
    text = "\n".join([res[1] for res in ocr_results])

    # PII detection
    pii = extract_pii_fixed(text)

    # Redaction
    redacted_bgr = redact_image(img_bgr, ocr_results, pii)

    return {
        "text": text,
        "pii": pii,
        "ocr_results": ocr_results,
        "redacted": redacted_bgr
    }
