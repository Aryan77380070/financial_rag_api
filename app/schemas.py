from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from .models import DocumentType

# Role Schemas
class RoleBase(BaseModel):
    name: str

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: int

    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    role_id: Optional[int] = None

    class Config:
        from_attributes = True

class UserAssignRole(BaseModel):
    user_id: int
    role_id: int

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    
    
# --- Document Schemas ---

class DocumentResponse(BaseModel):
    document_id: int
    title: str
    company_name: str
    document_type: DocumentType
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True