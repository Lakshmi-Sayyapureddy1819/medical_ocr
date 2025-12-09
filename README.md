# Medical OCR + PII Extraction (Streamlit)

Streamlit app for extracting PII from handwritten medical documents
(PDF / JPEG / PNG) such as **SUM Hospital progress reports**.

## Features

- Upload multiple files at once
- Supports **PDF, JPG, JPEG, PNG**
- Uses **EasyOCR** (no API key) – works with messy handwriting
- Extracts:
  - patient_name
  - age
  - sex
  - ipd_no
  - uhid
  - bed_no
  - hospital_name
  - phone (if present)
  - date(s)
- Shows:
  - Original page
  - Redacted page (PII blacked out)
  - Extracted text
  - PII JSON

## Installation

```bash
git clone https://github.com/<your-username>/medical-ocr-pii-streamlit.git
cd medical-ocr-pii-streamlit
pip install -r requirements.txt
