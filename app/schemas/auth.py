from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)   # 아이디
    name: str = Field(min_length=1, max_length=100)      # 이름
    password: str = Field(min_length=8, max_length=128)

class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UsernameExists(BaseModel):
    exists: bool