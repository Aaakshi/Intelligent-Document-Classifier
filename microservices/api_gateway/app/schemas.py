
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class DocumentUpload(BaseModel):
    file_name: str
    doc_type: Optional[str] = None

class DocumentResponse(BaseModel):
    id: uuid.UUID
    original_name: str
    doc_type: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "user"
    department: Optional[str] = None
    skills: Optional[Dict[str, Any]] = None

class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: Optional[str]
    role: str
    department: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True

class RoutingRuleCreate(BaseModel):
    name: str
    condition: Dict[str, Any]
    assignee: Optional[str] = None
    team: Optional[str] = None
    priority: int = 1

class RoutingRuleResponse(BaseModel):
    id: int
    name: str
    condition: Dict[str, Any]
    assignee: Optional[str]
    team: Optional[str]
    priority: int
    is_active: bool
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AssignmentResponse(BaseModel):
    id: int
    doc_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    priority: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class AnalyticsResponse(BaseModel):
    total_documents: int
    documents_by_type: Dict[str, int]
    processing_stats: Dict[str, Any]
    user_workload: List[Dict[str, Any]]
