from pdf2image import convert_from_bytes
from PIL import Image
from typing import List
import io

def pdf_to_images(file_bytes: bytes, dpi: int = 220) -> List[Image.Image]:
    """
    Convert PDF bytes to a list of PIL images.
    """
    images = convert_from_bytes(file_bytes, dpi=dpi)
    return images
