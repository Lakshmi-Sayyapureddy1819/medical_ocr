import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
import numpy as np
import cv2
from PIL import Image
from app.ocr_pipeline import process_page
from app.pdf_utils import pdf_to_images

st.set_page_config(page_title="TrOCR Large — Handwritten OCR + PII", layout="wide")
st.title("Handwritten OCR + PII Extractor — TrOCR Large (local CPU)")

uploaded_files = st.file_uploader(
    "Upload JPEG, PNG or PDF",
    type=["jpg","jpeg","png","pdf"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Upload files to process. First run will download the TrOCR-large model.")
else:
    for file in uploaded_files:
        st.header(f"File: {file.name}")
        # Convert PDF pages -> PIL images, or open image
        if file.type == "application/pdf":
            pages = pdf_to_images(file.read())
        else:
            pages = [Image.open(file)]

        for idx, pil_img in enumerate(pages, start=1):
            st.subheader(f"Page {idx}")
            img_rgb = np.array(pil_img.convert("RGB"))
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

            with st.spinner("Running TrOCR Large + EasyOCR ensemble (may take a while first run)..."):
                res = process_page(img_bgr)

            col1, col2 = st.columns([1,1])
            with col1:
                st.image(pil_img, caption="Original", use_column_width=True)
                st.markdown("**Header OCR (TrOCR Large)**")
                st.code(res.get("header_text", "")[:500], language="text")
            with col2:
                st.image(cv2.cvtColor(res["redacted"], cv2.COLOR_BGR2RGB), caption="Redacted", use_column_width=True)

            st.subheader("Extracted PII")
            st.json(res["pii"])

            st.subheader("Full OCR text (header + page)")
            st.text_area("OCR", res["text"], height=300)
