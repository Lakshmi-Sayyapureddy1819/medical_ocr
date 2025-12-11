import io
import math
import cv2
import numpy as np
from PIL import Image

import easyocr
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from .pii_extractor import extract_pii_fixed

# limit threads (Windows safe)
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

# initialize EasyOCR (fallback + box detection)
_easy_reader = None
def get_easy_reader():
    global _easy_reader
    if _easy_reader is None:
        _easy_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _easy_reader

# TrOCR model & processor (large handwritten)
_trocr_processor = None
_trocr_model = None
def init_trocr(model_name="microsoft/trocr-large-handwritten"):
    global _trocr_processor, _trocr_model
    if _trocr_model is None:
        _trocr_processor = TrOCRProcessor.from_pretrained(model_name)
        _trocr_model = VisionEncoderDecoderModel.from_pretrained(model_name)
        _trocr_model.to(torch.device("cpu"))
    return _trocr_processor, _trocr_model

# -------------------------
# Preprocessing helpers
# -------------------------
def apply_clahe_gray(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    # denoise
    den = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
    # optional morphological opening to reduce pen noise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,1))
    opened = cv2.morphologyEx(den, cv2.MORPH_OPEN, kernel)
    return opened

def deskew_image(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    coords = np.column_stack(np.where(edges > 0))
    if coords.shape[0] < 50:
        return img_bgr
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = img_bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    rotated = cv2.warpAffine(img_bgr, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def crop_header(img_bgr, top_ratio=0.32):
    h = img_bgr.shape[0]
    return img_bgr[:int(h*top_ratio), :, :]

# -------------------------
# TrOCR read (PIL input)
# -------------------------
def trocr_read_pil(pil_img: Image.Image, max_length=512):
    proc, model = init_trocr()
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    pixel_values = proc(images=pil_img, return_tensors="pt").pixel_values
    pixel_values = pixel_values.to(model.device)
    # generation params tuned for handwriting
    generated_ids = model.generate(pixel_values, max_length=max_length, num_beams=4, early_stopping=True)
    preds = proc.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return preds

# -------------------------
# EasyOCR read (full page)
# -------------------------
def easy_read(img_bgr):
    reader = get_easy_reader()
    try:
        results = reader.readtext(img_bgr)
    except Exception:
        results = []
    text = "\n".join([r[1] for r in results])
    return results, text

# -------------------------
# Pipeline: ensemble
# -------------------------
def run_ensemble(img_bgr: np.ndarray):
    """
    Returns:
      combined_text (header trocr + full easyocr)
      easy_results (list of boxes)
      header_text (str)
    """
    # deskew for whole page
    img_d = deskew_image(img_bgr)

    # crop and preprocess header for TrOCR
    header = crop_header(img_d)
    header_pre = apply_clahe_gray(header)
    header_pil = Image.fromarray(cv2.cvtColor(header_pre, cv2.COLOR_GRAY2RGB))

    # TrOCR on header (handwriting)
    header_text = ""
    try:
        header_text = trocr_read_pil(header_pil)
    except Exception:
        header_text = ""

    # EasyOCR on full page for boxes and additional text
    easy_results, easy_text = easy_read(img_d)

    combined_text = (header_text + "\n" + easy_text).strip()
    return combined_text, easy_results, header_text

# -------------------------
# Redaction
# -------------------------
def redact_image(img_bgr: np.ndarray, easy_results, pii_dict):
    out = img_bgr.copy()
    pii_vals = []
    for v in pii_dict.values():
        if v is None:
            continue
        if isinstance(v, list):
            pii_vals += [str(x).lower() for x in v]
        else:
            pii_vals.append(str(v).lower())
    pii_vals = [p for p in pii_vals if len(p) >= 2]

    for (bbox, text, conf) in easy_results:
        t = text.lower()
        if any(p in t for p in pii_vals):
            pts = np.array(bbox, np.int32)
            cv2.fillPoly(out, [pts], (0,0,0))
    return out

# -------------------------
# Exported: process_page
# -------------------------
def process_page(img_bgr: np.ndarray):
    """
    Input: BGR numpy image
    Returns: dict with text, pii, redacted, ocr_results, header_text
    """
    combined_text, easy_results, header_text = run_ensemble(img_bgr)
    pii = extract_pii_fixed(combined_text)
    redacted = redact_image(img_bgr, easy_results, pii)

    return {
        "text": combined_text,
        "pii": pii,
        "redacted": redacted,
        "ocr_results": easy_results,
        "header_text": header_text
    }
