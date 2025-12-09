import streamlit as st
import numpy as np
import cv2
from PIL import Image

from app.ocr_pipeline import process_page
from app.pdf_utils import pdf_to_images


st.set_page_config(page_title="Handwritten OCR + PII Extractor", layout="wide")
st.title("📄 OCR + PII Extraction (Handwritten SUM Hospital Dataset)")


uploaded_files = st.file_uploader(
    "Upload JPEG, PNG or PDF files",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Upload documents to start processing.")
else:
    for file in uploaded_files:
        st.header(f"📄 File: {file.name}")

        # ----------------------------
        # PDF Handling
        # ----------------------------
        if file.type == "application/pdf":
            pages = pdf_to_images(file.read())
        else:
            pages = [Image.open(file)]

        for idx, pil_img in enumerate(pages, start=1):
            st.subheader(f"Page {idx}")

            img_rgb = np.array(pil_img.convert("RGB"))
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

            result = process_page(img_bgr)

            col1, col2 = st.columns(2)

            with col1:
                st.image(pil_img, caption="Original Image", use_column_width=True)

            with col2:
                st.image(
                    cv2.cvtColor(result["redacted"], cv2.COLOR_BGR2RGB),
                    caption="Redacted Image",
                    use_column_width=True
                )

            st.subheader("Extracted PII")
            st.json(result["pii"])

            st.subheader("Extracted Text")
            st.text_area("OCR Text", result["text"], height=200)
