
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from libs.database.connection import get_db
from libs.database.models import User, DocumentAssignment
from ..schemas import UserResponse, UserCreate
import uuid

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get list of users with optional filtering"""
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    if department:
        query = query.filter(User.department == department)
    
    users = query.offset(skip).limit(limit).all()
    return [UserResponse.from_orm(user) for user in users]

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(user)

@router.get("/{user_id}/workload")
def get_user_workload(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get user's current workload"""
    assignments = db.query(DocumentAssignment).filter(
        DocumentAssignment.user_id == user_id,
        DocumentAssignment.status.in_(['assigned', 'in_progress'])
    ).all()
    
    workload_summary = {
        "user_id": user_id,
        "active_assignments": len(assignments),
        "high_priority": len([a for a in assignments if a.priority >= 4]),
        "medium_priority": len([a for a in assignments if a.priority == 3]),
        "low_priority": len([a for a in assignments if a.priority <= 2]),
        "assignments": [
            {
                "id": assignment.id,
                "doc_id": assignment.doc_id,
                "status": assignment.status,
                "priority": assignment.priority,
                "due_date": assignment.due_date,
                "created_at": assignment.created_at
            }
            for assignment in assignments
        ]
    }
    
    return workload_summary

@router.post("/", response_model=UserResponse)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    user = User(**user_data.dict())
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: uuid.UUID, user_data: UserCreate, db: Session = Depends(get_db)):
    """Update a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for field, value in user_data.dict(exclude_unset=True).items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)
