from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .auth import RoleChecker
from .rag_core import process_and_index_document, remove_document_embeddings

from .auth import RoleChecker, get_current_user
from .rag_core import process_and_index_document, remove_document_embeddings, retrieve_and_rerank, get_document_context

router = APIRouter(prefix="/rag", tags=["RAG Pipeline"])

# Only Admins and Analysts should be modifying the AI index
index_roles = RoleChecker(["Admin", "Financial Analyst"])

class IndexRequest(BaseModel):
    document_id: int
    filename: str

@router.post("/index-document", status_code=status.HTTP_200_OK)
def index_document(
    payload: IndexRequest, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(index_roles)
):
    # Verify the document exists in our relational database first
    document = db.query(models.Document).filter(models.Document.document_id == payload.document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found in database")

    file_path = f"uploads/{payload.filename}"
    
    # Prepare metadata to store in the vector DB alongside the text
    metadata = {
        "title": document.title,
        "company_name": document.company_name,
        "document_type": document.document_type.value
    }

    try:
        chunks_created = process_and_index_document(payload.document_id, file_path, metadata)
        return {
            "message": "Document successfully indexed", 
            "document_id": payload.document_id,
            "chunks_processed": chunks_created
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Physical file not found in uploads folder")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@router.delete("/remove-document/{document_id}", status_code=status.HTTP_200_OK)
def remove_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(index_roles)
):
    deleted_count = remove_document_embeddings(document_id)
    return {
        "message": f"Successfully removed embeddings for document {document_id}",
        "chunks_deleted": deleted_count
    }
    
    
    
class SearchQuery(BaseModel):
    query: str

@router.post("/search")
def semantic_search(
    payload: SearchQuery,
    current_user: models.User = Depends(get_current_user) # Any authenticated user can search
):
    try:
        results = retrieve_and_rerank(payload.query, top_k_initial=20, top_k_final=5)
        return {
            "query": payload.query, 
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/context/{document_id}")
def get_context(
    document_id: int,
    current_user: models.User = Depends(get_current_user)
):
    context = get_document_context(document_id)
    if not context:
        raise HTTPException(status_code=404, detail="No AI context found for this document")
    
    return {
        "document_id": document_id,
        "total_chunks": len(context),
        "context": context
    }