
from fastapi import FastAPI
import uvicorn
import json
import threading
from libs.utils.messaging import mq
from libs.database.connection import get_db_session
from libs.database.models import Document, RoutingRule, DocumentAssignment, User
from .router import DocumentRouter

app = FastAPI(title="Document Routing Engine")

# Initialize document router
document_router = DocumentRouter()

@app.on_event("startup")
async def startup_event():
    """Start message queue consumer"""
    def start_consumer():
        try:
            mq.connect()
            mq.consume_messages("classification_results", process_routing_message)
        except Exception as e:
            print(f"Error starting routing consumer: {e}")
    
    # Start consumer in background thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

@app.get("/")
async def root():
    return {"message": "Document Routing Engine"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "routing_engine"}

def process_routing_message(ch, method, properties, body):
    """Process classification results and route documents"""
    try:
        message = json.loads(body)
        document_id = message["document_id"]
        doc_type = message["doc_type"]
        confidence = message["confidence"]
        entities = message.get("entities", {})
        risk_score = message.get("risk_score", 0.0)
        priority = message.get("priority", 1)
        
        print(f"Routing document {document_id} of type {doc_type}")
        
        # Get database session
        db = get_db_session()
        
        try:
            # Get document
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                print(f"Document {document_id} not found")
                return
            
            # Route document
            routing_result = document_router.route_document(
                document_id=document_id,
                doc_type=doc_type,
                confidence=confidence,
                entities=entities,
                risk_score=risk_score,
                priority=priority,
                db=db
            )
            
            if routing_result:
                # Update document status
                document.status = 'routed'
                db.commit()
                
                # Send notification
                notification_message = {
                    "document_id": document_id,
                    "assignment_id": routing_result["assignment_id"],
                    "assigned_to": routing_result["assigned_to"],
                    "doc_type": doc_type,
                    "priority": priority,
                    "routing_reason": routing_result["routing_reason"]
                }
                
                try:
                    mq.publish_message("notifications", notification_message)
                except Exception as e:
                    print(f"Warning: Could not send notification: {e}")
                
                print(f"Document {document_id} routed to {routing_result['assigned_to']}")
            else:
                print(f"Failed to route document {document_id}")
                
        except Exception as e:
            print(f"Error routing document {document_id}: {e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error processing routing message: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
