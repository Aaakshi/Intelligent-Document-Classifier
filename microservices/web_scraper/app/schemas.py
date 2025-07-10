
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
from datetime import datetime

class ScrapingSourceCreate(BaseModel):
    name: str
    url: HttpUrl
    source_type: Optional[str] = "website"
    scraping_rules: Optional[Dict[str, Any]] = None

class ScrapingSourceResponse(BaseModel):
    id: int
    name: str
    url: str
    source_type: Optional[str]
    scraping_rules: Optional[Dict[str, Any]]
    last_scraped: Optional[datetime]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ScrapedContentResponse(BaseModel):
    id: int
    source_id: int
    url: str
    title: Optional[str]
    content_hash: Optional[str]
    metadata: Optional[Dict[str, Any]]
    scraped_at: datetime
    
    class Config:
        from_attributes = True

class ScrapingTaskRequest(BaseModel):
    url: HttpUrl
    rules: Optional[Dict[str, Any]] = None
    priority: int = 1

class DocumentDiscoveryRequest(BaseModel):
    url: HttpUrl
    file_extensions: Optional[List[str]] = None
