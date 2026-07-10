from fastapi import FastAPI, UploadFile, Depends, HTTPException, status, Request
from pydantic import BaseModel
from fastapi.responses import RedirectResponse, PlainTextResponse, StreamingResponse
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
from retrieval.search import get_data
from generation.llm import llm_response
from sentence_transformers import SentenceTransformer, CrossEncoder
from fastembed import SparseTextEmbedding
import json

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

    app.state.embed_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    app.state.rerank_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    app.state.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

    yield

app = FastAPI(lifespan=lifespan)

class Question(BaseModel):
    document_id: int
    pipeline: str = 'rag'
    question: str

STORAGE_PATH = Path("storage/documents")

SessionDep = Annotated[Session, Depends(get_session)]

@app.post("/upload/")
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
async def get_text(document_id: int, session: SessionDep, request: Request):

    embed_model = request.app.state.embed_model    
    doc = session.get(Documents, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    pdf_text = await extract_text_from_pdf(file_path=doc.user_file_path)
    chunks =  await make_chunks(pdf_text)
    vector = await store(document_id=document_id, chunks=chunks, embed_model=embed_model)
    return vector

@app.post("/query/")
async def get_response(data: Question, session: SessionDep, request: Request):
    
    question = data.question
    pipeline = data.pipeline
    document_id = data.document_id
    embed_model = request.app.state.embed_model
    rerank_model = request.app.state.rerank_model
    sparse_model = request.app.state.sparse_model

    get_relevent_chunks = get_data(question,  pipeline, document_id, embed_model, rerank_model, sparse_model)

    return StreamingResponse(
        llm_response(question=question, data=get_relevent_chunks, session=session, document_id=document_id),
        media_type="text/event-stream"
    )

# corrected the datafetching and embedings pipeline to be workig together asynchronasly 
# Fix the repeated model loading
# applied the hybrid search with existing Qdrant retreivel using bm2 space embeding and RRf