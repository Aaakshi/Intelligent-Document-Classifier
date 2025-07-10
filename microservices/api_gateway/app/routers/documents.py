
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from libs.database.connection import get_db
from libs.database.models import Document, Metadata, DocumentAssignment
from ..schemas import DocumentResponse
import uuid

router = APIRouter()

@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    doc_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get list of documents with optional filtering"""
    query = db.query(Document)
    
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if status:
        query = query.filter(Document.status == status)
    
    documents = query.offset(skip).limit(limit).all()
    return [DocumentResponse.from_orm(doc) for doc in documents]

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific document by ID"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.from_orm(document)

@router.get("/{document_id}/metadata")
def get_document_metadata(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get document metadata"""
    metadata = db.query(Metadata).filter(Metadata.doc_id == document_id).first()
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")
    
    return {
        "doc_id": metadata.doc_id,
        "key_entities": metadata.key_entities,
        "related_docs": metadata.related_docs,
        "risk_score": metadata.risk_score,
        "summary": metadata.summary,
        "language": metadata.language,
        "sentiment_score": metadata.sentiment_score,
        "topics": metadata.topics
    }

@router.get("/{document_id}/assignments")
def get_document_assignments(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get document assignments"""
    assignments = db.query(DocumentAssignment).filter(
        DocumentAssignment.doc_id == document_id
    ).all()
    
    return [
        {
            "id": assignment.id,
            "user_id": assignment.user_id,
            "status": assignment.status,
            "priority": assignment.priority,
            "due_date": assignment.due_date,
            "created_at": assignment.created_at
        }
        for assignment in assignments
    ]

@router.delete("/{document_id}")
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a document"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(document)
    db.commit()
    return {"message": "Document deleted successfully"}
