from sqlmodel import Field, SQLModel
from datetime import datetime

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

    user_token : str
    question: str
    llm_response: str

    created_at: datetime = Field(default_factory=datetime.now)

class Users(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)

    name: str
    phone: str = Field(nullable=False)
    email: str = Field(unique=True, nullable=False)
    password: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)


