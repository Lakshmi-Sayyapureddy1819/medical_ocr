from PIL import Image
import fitz  # PyMuPDF


def pdf_to_images(file_bytes: bytes, dpi: int = 220):
    """
    Convert a PDF (bytes) to list of PIL images, one per page.
    """
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in pdf:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)
    return pages
