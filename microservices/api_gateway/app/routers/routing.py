
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from libs.database.connection import get_db
from libs.database.models import RoutingRule, DocumentAssignment
from ..schemas import RoutingRuleCreate, RoutingRuleResponse

router = APIRouter()

@router.get("/rules", response_model=List[RoutingRuleResponse])
def get_routing_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """Get list of routing rules"""
    query = db.query(RoutingRule)
    
    if is_active is not None:
        query = query.filter(RoutingRule.is_active == is_active)
    
    rules = query.offset(skip).limit(limit).all()
    return [RoutingRuleResponse.from_orm(rule) for rule in rules]

@router.post("/rules", response_model=RoutingRuleResponse)
def create_routing_rule(rule_data: RoutingRuleCreate, db: Session = Depends(get_db)):
    """Create a new routing rule"""
    rule = RoutingRule(**rule_data.dict())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return RoutingRuleResponse.from_orm(rule)

@router.get("/rules/{rule_id}", response_model=RoutingRuleResponse)
def get_routing_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a specific routing rule"""
    rule = db.query(RoutingRule).filter(RoutingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    return RoutingRuleResponse.from_orm(rule)

@router.put("/rules/{rule_id}", response_model=RoutingRuleResponse)
def update_routing_rule(
    rule_id: int, 
    rule_data: RoutingRuleCreate, 
    db: Session = Depends(get_db)
):
    """Update a routing rule"""
    rule = db.query(RoutingRule).filter(RoutingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    
    for field, value in rule_data.dict(exclude_unset=True).items():
        setattr(rule, field, value)
    
    db.commit()
    db.refresh(rule)
    
    return RoutingRuleResponse.from_orm(rule)

@router.delete("/rules/{rule_id}")
def delete_routing_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete a routing rule"""
    rule = db.query(RoutingRule).filter(RoutingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    
    db.delete(rule)
    db.commit()
    return {"message": "Routing rule deleted successfully"}

@router.get("/assignments")
def get_assignments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get document assignments"""
    query = db.query(DocumentAssignment)
    
    if status:
        query = query.filter(DocumentAssignment.status == status)
    
    assignments = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": assignment.id,
            "doc_id": assignment.doc_id,
            "user_id": assignment.user_id,
            "status": assignment.status,
            "priority": assignment.priority,
            "due_date": assignment.due_date,
            "created_at": assignment.created_at
        }
        for assignment in assignments
    ]
