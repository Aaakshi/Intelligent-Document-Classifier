
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from datetime import datetime, timedelta
from libs.database.connection import get_db
from libs.database.models import Document, DocumentAssignment, User, Metadata
from ..schemas import AnalyticsResponse

router = APIRouter()

@router.get("/dashboard", response_model=AnalyticsResponse)
def get_dashboard_analytics(db: Session = Depends(get_db)):
    """Get dashboard analytics summary"""
    
    # Total documents
    total_documents = db.query(Document).count()
    
    # Documents by type
    doc_types = db.query(
        Document.doc_type, 
        func.count(Document.id).label('count')
    ).group_by(Document.doc_type).all()
    
    documents_by_type = {doc_type: count for doc_type, count in doc_types if doc_type}
    
    # Processing statistics
    processing_stats = {
        "pending": db.query(Document).filter(Document.status == 'pending').count(),
        "processing": db.query(Document).filter(Document.status == 'processing').count(),
        "completed": db.query(Document).filter(Document.status == 'completed').count(),
        "failed": db.query(Document).filter(Document.status == 'failed').count(),
    }
    
    # User workload
    user_workload = db.query(
        User.username,
        User.full_name,
        func.count(DocumentAssignment.id).label('active_assignments')
    ).outerjoin(
        DocumentAssignment,
        (DocumentAssignment.user_id == User.id) & 
        (DocumentAssignment.status.in_(['assigned', 'in_progress']))
    ).group_by(User.id, User.username, User.full_name).all()
    
    user_workload_list = [
        {
            "username": username,
            "full_name": full_name,
            "active_assignments": active_assignments
        }
        for username, full_name, active_assignments in user_workload
    ]
    
    return AnalyticsResponse(
        total_documents=total_documents,
        documents_by_type=documents_by_type,
        processing_stats=processing_stats,
        user_workload=user_workload_list
    )

@router.get("/trends")
def get_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get document processing trends over time"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Documents uploaded per day
    daily_uploads = db.query(
        func.date(Document.created_at).label('date'),
        func.count(Document.id).label('count')
    ).filter(
        Document.created_at >= start_date
    ).group_by(
        func.date(Document.created_at)
    ).order_by('date').all()
    
    # Processing time trends
    processing_times = db.query(
        func.date(Document.created_at).label('date'),
        func.avg(
            func.extract('epoch', Document.updated_at - Document.created_at)
        ).label('avg_processing_time')
    ).filter(
        Document.created_at >= start_date,
        Document.status == 'completed'
    ).group_by(
        func.date(Document.created_at)
    ).order_by('date').all()
    
    return {
        "daily_uploads": [
            {"date": str(date), "count": count}
            for date, count in daily_uploads
        ],
        "processing_times": [
            {"date": str(date), "avg_processing_time_seconds": float(avg_time) if avg_time else 0}
            for date, avg_time in processing_times
        ]
    }

@router.get("/classification-accuracy")
def get_classification_accuracy(db: Session = Depends(get_db)):
    """Get classification accuracy metrics"""
    
    # High confidence classifications (>0.9)
    high_confidence = db.query(Document).filter(Document.confidence > 0.9).count()
    
    # Medium confidence classifications (0.7-0.9)
    medium_confidence = db.query(Document).filter(
        Document.confidence >= 0.7,
        Document.confidence <= 0.9
    ).count()
    
    # Low confidence classifications (<0.7)
    low_confidence = db.query(Document).filter(Document.confidence < 0.7).count()
    
    total_classified = high_confidence + medium_confidence + low_confidence
    
    return {
        "total_classified": total_classified,
        "high_confidence": high_confidence,
        "medium_confidence": medium_confidence,
        "low_confidence": low_confidence,
        "accuracy_distribution": {
            "high": round((high_confidence / total_classified * 100) if total_classified > 0 else 0, 2),
            "medium": round((medium_confidence / total_classified * 100) if total_classified > 0 else 0, 2),
            "low": round((low_confidence / total_classified * 100) if total_classified > 0 else 0, 2)
        }
    }

@router.get("/search")
def search_documents(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search documents by content"""
    
    # Simple text search in document names and summaries
    documents = db.query(Document, Metadata).outerjoin(
        Metadata, Document.id == Metadata.doc_id
    ).filter(
        (Document.original_name.ilike(f"%{query}%")) |
        (Metadata.summary.ilike(f"%{query}%"))
    ).limit(limit).all()
    
    results = []
    for doc, metadata in documents:
        result = {
            "id": doc.id,
            "original_name": doc.original_name,
            "doc_type": doc.doc_type,
            "confidence": doc.confidence,
            "summary": metadata.summary if metadata else None,
            "created_at": doc.created_at
        }
        results.append(result)
    
    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }
