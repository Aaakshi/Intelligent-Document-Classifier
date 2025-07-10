
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import uvicorn
import threading
import json
from typing import List, Optional
from libs.database.connection import get_db, get_db_session
from libs.database.models import ScrapingSource, ScrapedContent
from libs.utils.messaging import mq
from .scraper import WebScraper
from .schemas import ScrapingSourceCreate, ScrapingSourceResponse, ScrapedContentResponse

app = FastAPI(title="Web Scraper Service")

# Initialize web scraper
web_scraper = WebScraper()

@app.on_event("startup")
async def startup_event():
    """Start message queue consumer for scraping tasks"""
    def start_consumer():
        try:
            mq.connect()
            mq.consume_messages("web_scraping", process_scraping_message)
        except Exception as e:
            print(f"Error starting scraper consumer: {e}")
    
    # Start consumer in background thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

@app.get("/")
async def root():
    return {"message": "Web Scraper Service"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "web_scraper"}

@app.post("/sources", response_model=ScrapingSourceResponse)
async def create_scraping_source(
    source_data: ScrapingSourceCreate,
    db: Session = Depends(get_db)
):
    """Create a new web scraping source"""
    source = ScrapingSource(**source_data.dict())
    db.add(source)
    db.commit()
    db.refresh(source)
    
    # Send scraping task to queue
    scraping_task = {
        "source_id": source.id,
        "url": source.url,
        "rules": source.scraping_rules
    }
    
    try:
        mq.publish_message("web_scraping", scraping_task)
    except Exception as e:
        print(f"Warning: Could not send scraping task to queue: {e}")
    
    return ScrapingSourceResponse.from_orm(source)

@app.get("/sources", response_model=List[ScrapingSourceResponse])
async def get_scraping_sources(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get list of scraping sources"""
    query = db.query(ScrapingSource)
    
    if is_active is not None:
        query = query.filter(ScrapingSource.is_active == is_active)
    
    sources = query.offset(skip).limit(limit).all()
    return [ScrapingSourceResponse.from_orm(source) for source in sources]

@app.get("/sources/{source_id}", response_model=ScrapingSourceResponse)
async def get_scraping_source(source_id: int, db: Session = Depends(get_db)):
    """Get a specific scraping source"""
    source = db.query(ScrapingSource).filter(ScrapingSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Scraping source not found")
    return ScrapingSourceResponse.from_orm(source)

@app.post("/sources/{source_id}/scrape")
async def trigger_scraping(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger scraping for a source"""
    source = db.query(ScrapingSource).filter(ScrapingSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Scraping source not found")
    
    # Send scraping task to queue
    scraping_task = {
        "source_id": source.id,
        "url": source.url,
        "rules": source.scraping_rules
    }
    
    try:
        mq.publish_message("web_scraping", scraping_task)
        return {"message": "Scraping task queued successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue scraping task: {e}")

@app.get("/content", response_model=List[ScrapedContentResponse])
async def get_scraped_content(
    skip: int = 0,
    limit: int = 100,
    source_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get scraped content"""
    query = db.query(ScrapedContent)
    
    if source_id:
        query = query.filter(ScrapedContent.source_id == source_id)
    
    content = query.offset(skip).limit(limit).all()
    return [ScrapedContentResponse.from_orm(item) for item in content]

@app.get("/content/search")
async def search_scraped_content(
    query: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Search scraped content"""
    content = db.query(ScrapedContent).filter(
        (ScrapedContent.title.ilike(f"%{query}%")) |
        (ScrapedContent.content.ilike(f"%{query}%"))
    ).limit(limit).all()
    
    results = []
    for item in content:
        results.append({
            "id": item.id,
            "source_id": item.source_id,
            "url": item.url,
            "title": item.title,
            "content_preview": item.content[:200] if item.content else "",
            "scraped_at": item.scraped_at
        })
    
    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }

def process_scraping_message(ch, method, properties, body):
    """Process web scraping tasks from message queue"""
    try:
        message = json.loads(body)
        source_id = message["source_id"]
        url = message["url"]
        rules = message.get("rules", {})
        
        print(f"Starting scraping for source {source_id}: {url}")
        
        # Get database session
        db = get_db_session()
        
        try:
            # Get scraping source
            source = db.query(ScrapingSource).filter(ScrapingSource.id == source_id).first()
            if not source:
                print(f"Scraping source {source_id} not found")
                return
            
            # Perform scraping
            scraped_data = web_scraper.scrape_url(url, rules)
            
            if scraped_data:
                # Save scraped content
                content = ScrapedContent(
                    source_id=source_id,
                    url=scraped_data['url'],
                    title=scraped_data.get('title', ''),
                    content=scraped_data.get('content', ''),
                    content_hash=scraped_data.get('content_hash', ''),
                    metadata=scraped_data.get('metadata', {})
                )
                
                db.add(content)
                
                # Update source last_scraped timestamp
                source.last_scraped = content.scraped_at
                
                db.commit()
                
                print(f"Successfully scraped content from {url}")
                
                # If scraped content looks like a document, send for classification
                if scraped_data.get('content') and len(scraped_data['content']) > 500:
                    classification_message = {
                        "scraped_content_id": content.id,
                        "content": scraped_data['content'],
                        "source_url": url,
                        "title": scraped_data.get('title', '')
                    }
                    
                    try:
                        mq.publish_message("document_processing", classification_message)
                    except Exception as e:
                        print(f"Warning: Could not send scraped content for classification: {e}")
            
        except Exception as e:
            print(f"Error processing scraping task for source {source_id}: {e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error processing scraping message: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
