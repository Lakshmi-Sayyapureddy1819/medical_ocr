from PIL import Image
import fitz

def pdf_to_images(file_bytes, dpi=220):
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    images = []
    for page in pdf:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images
