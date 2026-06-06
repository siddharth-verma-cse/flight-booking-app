from pydantic import EmailStr
import uuid
from sqlmodel import SQLModel, Field


class UserInDB(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr
    password: str
