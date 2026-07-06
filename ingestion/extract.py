import pdfplumber
from paddleocr import PaddleOCR
import numpy as np
import time
import sys
import platform
import paddle

ocr_engine = None


def get_ocr_engine():
    global ocr_engine

    if ocr_engine is None:
        print("\n===== OCR INIT DEBUG =====")
        print("Paddle version:", paddle.__version__)
        print("Device:", paddle.device.get_device())

        try:
            ocr_engine = PaddleOCR(
    lang="en",
    use_angle_cls=False,
    enable_mkldnn=False,
    device="cpu",
    use_doc_preprocessor=False,
)
            print("OCR engine initialized successfully\n")

        except Exception as e:
            print("OCR INIT FAILED:")
            print(e)
            raise

    return ocr_engine


def is_image(text: str, min_chars: int = 20):
    return len(text.strip()) < min_chars


def extract_text_from_pdf(file_path: str):
    print("\n===== PDF DEBUG START =====")
    print("File:", file_path)
    print("Python:", sys.version)
    print("Platform:", platform.platform())

    pdf_text = []

    with pdfplumber.open(file_path) as pdf:
        print("Total pages:", len(pdf.pages))

        for i, page in enumerate(pdf.pages):
            print(f"\n----- PAGE {i} -----")

            text = page.extract_text() or ""
            print("Extracted text length:", len(text))

            if not is_image(text):
                print("Using native PDF text extraction")
                pdf_text.append({
                    "text": text,
                    "source": "pdf_extracted"
                })
                continue

            print("Using OCR path")

            image = page.to_image(resolution=150).original
            image_array = np.array(image.convert("RGB"))

            print("Image shape:", image_array.shape)
            print("Image dtype:", image_array.dtype)

            ocr = get_ocr_engine()

            t1 = time.time()
            try:
                result = ocr.predict(image_array)
            except Exception as e:
                print("OCR PREDICT FAILED:")
                print(e)
                raise

            print("OCR time:", time.time() - t1)
            print("Raw result type:", type(result))

            ocr_text = []

            if result:
                try:
                    first = result[0]
                    print("First result sample:", first)

                    if isinstance(first, dict) and "rec_texts" in first:
                        ocr_text = first["rec_texts"]
                    else:
                        print("Unexpected OCR format:", first)

                except Exception as e:
                    print("Result parsing error:", e)

            pdf_text.append({
                "text": "\n".join(ocr_text),
                "source": "paddle_ocr",
                "file_path": file_path
            })

    print("\n===== PDF DEBUG END =====")
    return pdf_text