from sqlmodel import Field, SQLModel
from datetime import datetime
from sqlalchemy import Column, DateTime, func

class Documents(SQLModel, table= True):
    __tablename__ = 'documents'

    id: int | None = Field(default=None, primary_key=True)
    file_id: str
    user_file_path: str
    user_file_name: str
    created_at: datetime = Field(
            sa_column=Column(DateTime(timezone=True), server_default=func.now())
        )