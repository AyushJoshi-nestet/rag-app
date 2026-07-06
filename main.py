from fastapi import FastAPI, UploadFile, Depends, HTTPException, status
from contextlib import asynccontextmanager
from typing import Annotated
from sqlmodel import Session
from storage.db import create_db_and_tables, get_session
from storage.data import Documents
import uuid
from pathlib import Path
from ingestion.extract import extract_text_from_pdf

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

STORAGE_PATH = Path("storage/documents")

SessionDep = Annotated[Session, Depends(get_session)]

@app.post("/upload")
async def upload_document(file: UploadFile, session: SessionDep):
    document_id = str(uuid.uuid4())
    document_name = f"{document_id}_{file.filename}"
    save_path = STORAGE_PATH / document_name

    with open(save_path, "wb") as f:
        f.write(await file.read())

    doc = Documents(file_id=document_id, user_file_path=str(save_path), user_file_name=document_name)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return {"id": doc.id, "file_id": doc.file_id, "file_path": doc.user_file_path, "file_name": doc.user_file_name}

@app.get("/extract-data/{document_id}/")
async def get_text(document_id: int, session: SessionDep):
    doc = session.get(Documents, document_id)
    if not doc:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    return extract_text_from_pdf(file_path=doc.user_file_path)