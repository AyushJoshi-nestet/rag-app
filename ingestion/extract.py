from fastapi import HTTPException, status
import pdfplumber
from paddleocr import PaddleOCR
import numpy as np
import os
os.environ["FLAGS_use_mkldnn"] = "0"
ocr_engine = None

def get_ocr_engine():
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = PaddleOCR(
            use_angle_cls=False,
            lang="en"
        )
    return ocr_engine


def is_image(text: str, min_chars: int = 20):
    return len(text.strip()) < min_chars

def extract_text_from_pdf(file_path: str):
    print(file_path)
    pdf_text = []

    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)

        if page_count > 25:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="PDF must not exceed 25 pages"
            )

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
                "text": "\n".join(page_lines),
                "source": "paddle_ocr",
                "file_path": file_path
            })

    return pdf_text