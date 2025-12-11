# Setup (local) — REQUIREMENTS: Python 3.10 or 3.11

1. Install Python 3.10 (or 3.11). Do NOT use 3.12/3.13.
   https://www.python.org/downloads/

2. Create venv and activate:
   cd medical_ocr
   python -m venv venv
   venv\Scripts\activate   # Windows
   source venv/bin/activate # Linux / macOS

3. Upgrade pip:
   python -m pip install --upgrade pip

4. Install requirements:
   pip install -r requirements.txt

   Note: First run will download TrOCR (~400MB). Be patient.

5. Run Streamlit:
   streamlit run streamlit_app.py

6. Troubleshooting:
   - If pip fails for torch, use the torch build matching your Python
     e.g. torch==2.6.0 / torchvision==0.21.0 for Python 3.13 or
     torch==2.0.1+cpu & torchvision==0.15.2+cpu for Python 3.10.

   - If OpenCV import fails, ensure `opencv-python-headless` is installed
     (or install `opencv-python` for local GUI).

7. Deploying:
   - For Render/any Docker host, use a Dockerfile and CPU torch wheel versions.
