import pdfplumber
import ocrmypdf
from pathlib import Path

def extract_text_from_pdf(file_path):
    OCR_STORAGE_PATH = Path("storage/ocr_documents")

    input_path = Path(file_path)
    save_path = OCR_STORAGE_PATH / f"OCR_{input_path.name}"
    OCR_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

    try:
        ocrmypdf.ocr(
            input_file=str(input_path),
            output_file=str(save_path),
            output_type="pdf",
            skip_text=True,
            rotate_pages=True,
            jobs=4,
            deskew=True,
        )
    except ocrmypdf.exceptions.PriorOcrFoundError:
        pass
    except ocrmypdf.exceptions.EncryptedPdfError:
        raise ValueError("PDF is password-protected")
    except Exception as e:
        raise ValueError(f"Could not process PDF: {e}")

    pdf_text = []
    with pdfplumber.open(save_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pdf_text.append({
                "page_number": page_number,
                "text": text,
                "source": "pdfplumber",
                "file_path": str(save_path)
            })

    return pdf_text 