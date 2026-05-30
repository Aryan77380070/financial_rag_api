from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class DocumentType(str, enum.Enum):
    INVOICE = "invoice"
    REPORT = "report"
    CONTRACT = "contract"

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # e.g., Admin, Analyst, Auditor, Client
    
    # Relationship to users
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"))

    # Relationships
    role = relationship("Role", back_populates="users")
    documents = relationship("Document", back_populates="owner")

class Document(Base):
    __tablename__ = "documents"

    document_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    company_name = Column(String, index=True, nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    
    # uploaded_by acts as a foreign key to the User table
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    
    # created_at defaults to the current timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to the user who uploaded it
    owner = relationship("User", back_populates="documents")