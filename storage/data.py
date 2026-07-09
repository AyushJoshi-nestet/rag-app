from sqlmodel import Field, SQLModel
from datetime import datetime
from sqlalchemy import Column, DateTime, func

class Documents(SQLModel, table= True):
    __tablename__ = 'documents'

    id: int = Field( primary_key=True)
    file_id: str
    user_file_path: str
    user_file_name: str
    created_at: datetime = Field(default_factory=datetime.now)

class LLM_Response(SQLModel, table=True):
    __tablename__ = "llm_response"

    id: int | None = Field(default=None, primary_key=True)    
    document_id: int
    question: str
    llm_response: str

    created_at: datetime = Field(default_factory=datetime.now)