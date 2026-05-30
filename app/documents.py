import os
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from .database import get_db
from . import models, schemas
from .auth import get_current_user, RoleChecker

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allow Admins and Analysts to upload
upload_roles = RoleChecker(["Admin", "Financial Analyst"])
# Allow Admins to delete
delete_roles = RoleChecker(["Admin"])

@router.post("/upload", response_model=schemas.DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    company_name: str = Form(...),
    document_type: models.DocumentType = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(upload_roles)
):
    # 1. Save the file locally
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Save metadata to the database
    new_doc = models.Document(
        title=title,
        company_name=company_name,
        document_type=document_type,
        uploaded_by=current_user.id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    return new_doc

@router.get("", response_model=List[schemas.DocumentResponse])
def get_all_documents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # Any logged-in user can view
):
    documents = db.query(models.Document).all()
    return documents

@router.get("/search", response_model=List[schemas.DocumentResponse])
def search_documents(
    title: Optional[str] = None,
    company_name: Optional[str] = None,
    document_type: Optional[models.DocumentType] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Document)
    
    if title:
        query = query.filter(models.Document.title.ilike(f"%{title}%"))
    if company_name:
        query = query.filter(models.Document.company_name.ilike(f"%{company_name}%"))
    if document_type:
        query = query.filter(models.Document.document_type == document_type)
        
    return query.all()

@router.get("/{document_id}", response_model=schemas.DocumentResponse)
def get_document(
    document_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    document = db.query(models.Document).filter(models.Document.document_id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(delete_roles) # Only Admins can delete
):
    document = db.query(models.Document).filter(models.Document.document_id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    db.delete(document)
    db.commit()
    return None