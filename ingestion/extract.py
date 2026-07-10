import pdfplumber
from paddleocr import PaddleOCR
import numpy as np
import os

os.environ["FLAGS_use_mkldnn"] = "0"
ocr_engine = None

async def get_ocr_engine():
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = PaddleOCR(
            use_angle_cls=False,
            lang="en"
        )
    return ocr_engine

async def extract_text_from_pdf(file_path: str):    
    
    pdf_text = []

    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            image = page.to_image(resolution=150).original
            image_array = np.array(image.convert("RGB"))

            ocr = get_ocr_engine()
            result = ocr.ocr(image_array)

            page_lines = []
            if result and result[0]:
                for detection in result[0]:
                    box, (text, confidence) = detection
                    page_lines.append(text)

            pdf_text.append({
                "page_number": page_number,
                "text": "   ".join(page_lines),
                "source": "paddle_ocr",
                "file_path": file_path
            })

    return pdf_text