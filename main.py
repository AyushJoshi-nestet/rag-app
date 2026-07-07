from fastapi import FastAPI, UploadFile, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from typing import Annotated
from sqlmodel import Session
from storage.db import create_db_and_tables, get_session
from storage.data import Documents
import uuid
from pathlib import Path
from ingestion.extract import extract_text_from_pdf
import pdfplumber
import io
from ingestion.chunk import make_chunks 
from ingestion.pipeline import store

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

STORAGE_PATH = Path("storage/documents")

SessionDep = Annotated[Session, Depends(get_session)]

@app.post("/upload")
async def upload_document(file: UploadFile, session: SessionDep):

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted"
        )
    content = await file.read()

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            num_pages = len(pdf.pages)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid PDF"
        )
    
    if num_pages > 25:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PDF must not exceed 25 pages (got {num_pages})"
        )

    document_id = str(uuid.uuid4())
    document_name = f"{document_id}_{file.filename}"
    save_path = STORAGE_PATH / document_name

    with open(save_path, "wb") as f:
        f.write(content)

    doc = Documents(file_id=document_id, user_file_path=str(save_path), user_file_name=document_name)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return {"id": doc.id, "file_id": doc.file_id, "file_path": doc.user_file_path, "file_name": doc.user_file_name}

@app.get("/extract-data/{document_id}/")
async def get_text(document_id: int, session: SessionDep):
    
    doc = session.get(Documents, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    pdf_text = extract_text_from_pdf(file_path=doc.user_file_path)
    chunks = make_chunks(pdf_text)
    vector = store(document_id=document_id, chunks=chunks)

    return vector