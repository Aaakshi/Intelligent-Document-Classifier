
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from libs.database.connection import get_db
from libs.database.models import User
from libs.utils.auth import create_access_token, get_password_hash, verify_password
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserResponse

router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return access token"""
    # For demo purposes, using simple username/password
    # In production, use proper password hashing
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user:
        # Create default user if not exists (for demo)
        user = User(
            username=login_data.username,
            email=f"{login_data.username}@company.com",
            full_name=f"User {login_data.username}"
        )
        db.add(user)
        db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=access_token)

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    user = User(**user_data.dict())
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)
