from fastapi import FastAPI, UploadFile, Depends, HTTPException, status, Request, Header
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestFormStrict
from typing import Annotated
from sqlmodel import Session, select
from storage.db import create_db_and_tables, get_session
from storage.data import Documents, Users
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
import os
from dotenv import load_dotenv
from datetime import timedelta
import jwt

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"
TOKEN_EXPIRE_TIME = 60

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

    app.state.embed_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    app.state.rerank_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    app.state.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
   
    yield

app = FastAPI(lifespan=lifespan)

class HeaderToken(BaseModel):
    Authorization: str

class Question(BaseModel):
    question: str

class UserFields(BaseModel):
    name: str
    phone: str
    email: str
    password: str

class LoginFields(BaseModel):
    email: str
    password: str

STORAGE_PATH = Path("storage/documents")
SessionDep = Annotated[Session, Depends(get_session)]


def create_access_token(data: dict):
    token = jwt.encode(
    payload=data,
    key=SECRET_KEY,
    algorithm=ALGORITHM
)
    return token

@app.post("/sign-up/")
async def user_signup(data: UserFields, session: SessionDep):
    
    statement = select(Users).where(
        Users.email == data.email    )
    
    user_data = session.exec(statement).first()
    
    if user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="email already exist"
        )

    user = Users(
        name=data.name,
        phone=data.phone,
        email=data.email,
        password=data.password,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email
            }

@app.post("/login/")
async def user_login(data: LoginFields, session: SessionDep):

    statement = select(Users).where(
        Users.email == data.email,
        Users.password == data.password
    )
    
    user_data = session.exec(statement).first()

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid email or password"
        )    
    
    token = create_access_token(
        data=user_data.model_dump(mode="json")
    )

    return {
        token
    }

@app.post("/upload/")
async def upload_document(file: UploadFile, session: SessionDep, request: Request):

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

    embed_model = request.app.state.embed_model    

    pdf_text = await extract_text_from_pdf(file_path=save_path)
    chunks =  await make_chunks(pdf_text, document_id)
    source_name = file.filename
    print(source_name)
    vector = await store(chunks=chunks, embed_model=embed_model, source_name=source_name)
    return vector

@app.post("/query/")
async def get_response(data: Question, session: SessionDep, request: Request, Authorization: str = Header()):
    
    question = data.question
    header_token = jwt.decode(
        Authorization,
        SECRET_KEY,
        algorithms=["HS256"]
    )

    user_email = header_token.get("email")
    if not user_email:
       raise HTTPException(status_code=401, detail="Invalid token")

    embed_model = request.app.state.embed_model
    rerank_model = request.app.state.rerank_model
    sparse_model = request.app.state.sparse_model

    get_relevent_chunks = get_data(question, embed_model, rerank_model, sparse_model)

    return StreamingResponse(

        llm_response( user_email= user_email, question=question, data=get_relevent_chunks, session=session),
        media_type="text/event-stream"
    
    )
