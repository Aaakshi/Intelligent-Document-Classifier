
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ARRAY, JSON, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_name = Column(String(255), nullable=False)
    storage_path = Column(Text, nullable=False)
    doc_type = Column(String(50))
    confidence = Column(Float)
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    content_hash = Column(String(64))
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    metadata = relationship("Metadata", back_populates="document", cascade="all, delete-orphan")
    assignments = relationship("DocumentAssignment", back_populates="document", cascade="all, delete-orphan")

class Metadata(Base):
    __tablename__ = "metadata"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'))
    key_entities = Column(JSONB)
    related_docs = Column(ARRAY(UUID))
    risk_score = Column(Float)
    summary = Column(Text)
    language = Column(String(10))
    sentiment_score = Column(Float)
    topics = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="metadata")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default='user')
    department = Column(String(100))
    skills = Column(JSONB)
    workload_capacity = Column(Integer, default=10)
    timezone = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    assignments = relationship("DocumentAssignment", back_populates="user")

class RoutingRule(Base):
    __tablename__ = "routing_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    condition = Column(JSONB, nullable=False)
    assignee = Column(String(100))
    team = Column(String(100))
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class DocumentAssignment(Base):
    __tablename__ = "document_assignments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    assigned_by = Column(String(100))
    status = Column(String(50), default='assigned')
    priority = Column(Integer, default=1)
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="assignments")
    user = relationship("User", back_populates="assignments")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(255), nullable=False)
    action = Column(String(50), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    details = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

class ScrapingSource(Base):
    __tablename__ = "scraping_sources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    source_type = Column(String(50))
    scraping_rules = Column(JSONB)
    last_scraped = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    scraped_content = relationship("ScrapedContent", back_populates="source")

class ScrapedContent(Base):
    __tablename__ = "scraped_content"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey('scraping_sources.id'))
    url = Column(Text, nullable=False)
    title = Column(String(500))
    content = Column(Text)
    content_hash = Column(String(64))
    metadata = Column(JSONB)
    scraped_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    source = relationship("ScrapingSource", back_populates="scraped_content")
