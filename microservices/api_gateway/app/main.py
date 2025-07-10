
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uvicorn
import os
import shutil
from typing import List, Optional
import uuid

from libs.database.connection import get_db, create_tables
from libs.database.models import Document, User, RoutingRule, DocumentAssignment
from libs.utils.auth import verify_token, create_access_token
from libs.utils.messaging import mq
from .routers import documents, users, routing, analytics, auth
from .schemas import DocumentUpload, DocumentResponse, UserCreate, UserResponse

app = FastAPI(
    title="Document Classifier and Router API",
    description="AI-powered document intelligence system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(routing.router, prefix="/routing", tags=["routing"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

@app.on_event("startup")
async def startup_event():
    """Initialize database and connections on startup"""
    create_tables()
    try:
        mq.connect()
    except Exception as e:
        print(f"Warning: Could not connect to RabbitMQ: {e}")

@app.get("/")
async def root():
    return {"message": "Document Classifier and Router API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api_gateway"}

@app.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Upload a document for classification and routing"""
    # Verify token
    username = verify_token(credentials.credentials)
    
    # Create uploads directory if it doesn't exist
    os.makedirs("uploads", exist_ok=True)
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    storage_filename = f"{file_id}.{file_extension}" if file_extension else file_id
    file_path = f"uploads/{storage_filename}"
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create document record
    document = Document(
        original_name=file.filename,
        storage_path=file_path,
        doc_type=doc_type,
        file_size=os.path.getsize(file_path),
        mime_type=file.content_type,
        status='uploaded'
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Send message for processing
    message = {
        "document_id": str(document.id),
        "file_path": file_path,
        "original_name": file.filename,
        "mime_type": file.content_type,
        "uploaded_by": username
    }
    
    try:
        mq.publish_message("document_processing", message)
    except Exception as e:
        print(f"Warning: Could not send message to queue: {e}")
    
    return DocumentResponse(
        id=document.id,
        original_name=document.original_name,
        doc_type=document.doc_type,
        status=document.status,
        created_at=document.created_at
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
