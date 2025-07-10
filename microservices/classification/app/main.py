
from fastapi import FastAPI, BackgroundTasks
import uvicorn
import json
import os
import threading
from libs.utils.messaging import mq
from libs.database.connection import get_db_session
from libs.database.models import Document, Metadata
from .classifier import DocumentClassifier
from .content_analyzer import ContentAnalyzer

app = FastAPI(title="Document Classification Service")

# Initialize classifier and content analyzer
classifier = DocumentClassifier()
content_analyzer = ContentAnalyzer()

@app.on_event("startup")
async def startup_event():
    """Start message queue consumer"""
    def start_consumer():
        try:
            mq.connect()
            mq.consume_messages("document_processing", process_document_message)
        except Exception as e:
            print(f"Error starting consumer: {e}")
    
    # Start consumer in background thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "classification"}

@app.get("/")
async def root():
    return {"message": "Document Classification Service"}

def process_document_message(ch, method, properties, body):
    """Process incoming document for classification"""
    try:
        message = json.loads(body)
        document_id = message["document_id"]
        file_path = message["file_path"]
        
        print(f"Processing document {document_id}")
        
        # Get database session
        db = get_db_session()
        
        try:
            # Get document from database
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                print(f"Document {document_id} not found")
                return
            
            # Update status to processing
            document.status = 'processing'
            db.commit()
            
            # Classify document
            classification_result = classifier.classify_document(file_path)
            
            # Analyze content
            content_result = content_analyzer.analyze_content(file_path)
            
            # Update document with classification results
            document.doc_type = classification_result['doc_type']
            document.confidence = classification_result['confidence']
            document.status = 'classified'
            
            # Create or update metadata
            metadata = db.query(Metadata).filter(Metadata.doc_id == document_id).first()
            if not metadata:
                metadata = Metadata(doc_id=document_id)
                db.add(metadata)
            
            metadata.key_entities = content_result.get('entities', {})
            metadata.summary = content_result.get('summary', '')
            metadata.language = content_result.get('language', 'en')
            metadata.sentiment_score = content_result.get('sentiment', 0.0)
            metadata.topics = content_result.get('topics', {})
            metadata.risk_score = content_result.get('risk_score', 0.0)
            
            db.commit()
            
            # Send result to routing engine
            routing_message = {
                "document_id": document_id,
                "doc_type": classification_result['doc_type'],
                "confidence": classification_result['confidence'],
                "entities": content_result.get('entities', {}),
                "risk_score": content_result.get('risk_score', 0.0),
                "priority": classification_result.get('priority', 1)
            }
            
            mq.publish_message("classification_results", routing_message)
            print(f"Document {document_id} classified successfully")
            
        except Exception as e:
            print(f"Error processing document {document_id}: {e}")
            document.status = 'failed'
            db.commit()
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error processing message: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
