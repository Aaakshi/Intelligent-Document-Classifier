
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from libs.database.models import RoutingRule, User, DocumentAssignment
import json
from datetime import datetime, timedelta

class DocumentRouter:
    def __init__(self):
        self.rule_cache = {}
        self.user_cache = {}
        
    def route_document(
        self, 
        document_id: str,
        doc_type: str,
        confidence: float,
        entities: Dict[str, Any],
        risk_score: float,
        priority: int,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Route document based on rules and context"""
        
        # Get active routing rules
        rules = db.query(RoutingRule).filter(RoutingRule.is_active == True).order_by(RoutingRule.priority.desc()).all()
        
        # Document context for rule evaluation
        context = {
            "doc_type": doc_type,
            "confidence": confidence,
            "entities": entities,
            "risk_score": risk_score,
            "priority": priority,
            "persons": entities.get("persons", []),
            "organizations": entities.get("organizations", []),
            "amounts": entities.get("money", []),
            "dates": entities.get("dates", [])
        }
        
        # Find matching rule
        matched_rule = None
        for rule in rules:
            if self._evaluate_rule_condition(rule.condition, context):
                matched_rule = rule
                break
        
        if not matched_rule:
            # Use default routing based on document type
            matched_rule = self._get_default_routing_rule(doc_type, db)
        
        if not matched_rule:
            print(f"No routing rule found for document {document_id}")
            return None
        
        # Find best assignee
        assignee = self._find_best_assignee(matched_rule, context, db)
        
        if not assignee:
            print(f"No available assignee found for document {document_id}")
            return None
        
        # Create assignment
        assignment = DocumentAssignment(
            doc_id=document_id,
            user_id=assignee["user_id"],
            assigned_by="routing_engine",
            status="assigned",
            priority=priority,
            due_date=self._calculate_due_date(priority, doc_type)
        )
        
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        
        return {
            "assignment_id": assignment.id,
            "assigned_to": assignee["username"],
            "user_id": assignee["user_id"],
            "routing_reason": f"Matched rule: {matched_rule.name}",
            "priority": priority,
            "due_date": assignment.due_date
        }
    
    def _evaluate_rule_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate if rule condition matches document context"""
        try:
            # Simple condition evaluation
            for key, expected_value in condition.items():
                if key not in context:
                    continue
                
                context_value = context[key]
                
                if isinstance(expected_value, str):
                    # String matching (case insensitive)
                    if isinstance(context_value, str):
                        if expected_value.lower() not in context_value.lower():
                            return False
                    elif isinstance(context_value, list):
                        # Check if any item in list matches
                        found = False
                        for item in context_value:
                            if isinstance(item, str) and expected_value.lower() in item.lower():
                                found = True
                                break
                        if not found:
                            return False
                    else:
                        return False
                
                elif isinstance(expected_value, (int, float)):
                    # Numeric comparison
                    if isinstance(context_value, (int, float)):
                        if context_value != expected_value:
                            return False
                    else:
                        return False
                
                elif isinstance(expected_value, dict):
                    # Advanced conditions (greater than, less than, etc.)
                    if "gt" in expected_value:
                        if not (isinstance(context_value, (int, float)) and context_value > expected_value["gt"]):
                            return False
                    if "lt" in expected_value:
                        if not (isinstance(context_value, (int, float)) and context_value < expected_value["lt"]):
                            return False
                    if "gte" in expected_value:
                        if not (isinstance(context_value, (int, float)) and context_value >= expected_value["gte"]):
                            return False
                    if "lte" in expected_value:
                        if not (isinstance(context_value, (int, float)) and context_value <= expected_value["lte"]):
                            return False
                    if "contains" in expected_value:
                        if isinstance(context_value, str):
                            if expected_value["contains"].lower() not in context_value.lower():
                                return False
                        elif isinstance(context_value, list):
                            found = False
                            for item in context_value:
                                if isinstance(item, str) and expected_value["contains"].lower() in item.lower():
                                    found = True
                                    break
                            if not found:
                                return False
            
            return True
            
        except Exception as e:
            print(f"Error evaluating rule condition: {e}")
            return False
    
    def _get_default_routing_rule(self, doc_type: str, db: Session) -> Optional[RoutingRule]:
        """Get default routing rule for document type"""
        
        # Default routing mappings
        default_mappings = {
            "contract": "legal-team",
            "invoice": "finance-team",
            "legal": "legal-team",
            "financial": "finance-team",
            "hr": "hr-team",
            "technical": "engineering-team",
            "report": "management-team",
            "correspondence": "admin-team"
        }
        
        assignee = default_mappings.get(doc_type, "admin-team")
        
        # Create a temporary rule object
        class DefaultRule:
            def __init__(self, assignee):
                self.name = f"Default rule for {doc_type}"
                self.assignee = assignee
                self.team = assignee
                self.priority = 1
        
        return DefaultRule(assignee)
    
    def _find_best_assignee(self, rule: RoutingRule, context: Dict[str, Any], db: Session) -> Optional[Dict[str, Any]]:
        """Find the best available assignee for the rule"""
        
        # Get available users
        available_users = db.query(User).filter(User.is_active == True).all()
        
        if not available_users:
            return None
        
        # Filter by role/department if specified in rule
        candidate_users = []
        
        if hasattr(rule, 'assignee') and rule.assignee:
            # Check if assignee is a specific user
            user = db.query(User).filter(User.username == rule.assignee).first()
            if user and user.is_active:
                candidate_users = [user]
            else:
                # Check if assignee is a team/department
                candidate_users = db.query(User).filter(
                    User.department == rule.assignee.replace('-team', ''),
                    User.is_active == True
                ).all()
        
        if hasattr(rule, 'team') and rule.team and not candidate_users:
            # Filter by team
            candidate_users = db.query(User).filter(
                User.department == rule.team.replace('-team', ''),
                User.is_active == True
            ).all()
        
        if not candidate_users:
            candidate_users = available_users
        
        # Find user with lowest current workload
        best_user = None
        lowest_workload = float('inf')
        
        for user in candidate_users:
            # Count active assignments
            active_assignments = db.query(DocumentAssignment).filter(
                DocumentAssignment.user_id == user.id,
                DocumentAssignment.status.in_(['assigned', 'in_progress'])
            ).count()
            
            # Consider user capacity
            workload_ratio = active_assignments / max(user.workload_capacity, 1)
            
            # Adjust for skills match
            skills_bonus = 0
            if user.skills and context.get("doc_type"):
                user_skills = user.skills if isinstance(user.skills, list) else []
                if context["doc_type"] in user_skills:
                    skills_bonus = -0.2  # Reduce effective workload for skill match
            
            effective_workload = workload_ratio + skills_bonus
            
            if effective_workload < lowest_workload:
                lowest_workload = effective_workload
                best_user = user
        
        if best_user:
            return {
                "user_id": best_user.id,
                "username": best_user.username,
                "current_workload": lowest_workload
            }
        
        return None
    
    def _calculate_due_date(self, priority: int, doc_type: str) -> datetime:
        """Calculate due date based on priority and document type"""
        
        # Base due dates in hours
        priority_hours = {
            5: 2,   # Urgent: 2 hours
            4: 8,   # High: 8 hours
            3: 24,  # Medium: 1 day
            2: 72,  # Low: 3 days
            1: 168  # Very low: 1 week
        }
        
        # Document type modifiers
        type_modifiers = {
            "legal": 0.5,      # Legal docs need faster processing
            "contract": 0.5,   # Contracts are time-sensitive
            "invoice": 0.7,    # Invoices have payment deadlines
            "financial": 0.8,  # Financial docs are important
            "hr": 1.0,         # Normal processing
            "technical": 1.2,  # Technical docs can take longer
            "report": 1.5,     # Reports are less urgent
            "correspondence": 1.0
        }
        
        base_hours = priority_hours.get(priority, 72)
        modifier = type_modifiers.get(doc_type, 1.0)
        
        due_hours = base_hours * modifier
        due_date = datetime.utcnow() + timedelta(hours=due_hours)
        
        return due_date
    
    def get_routing_statistics(self, db: Session) -> Dict[str, Any]:
        """Get routing performance statistics"""
        
        # Total assignments
        total_assignments = db.query(DocumentAssignment).count()
        
        # Assignments by status
        status_counts = {}
        statuses = ['assigned', 'in_progress', 'completed', 'overdue']
        for status in statuses:
            count = db.query(DocumentAssignment).filter(DocumentAssignment.status == status).count()
            status_counts[status] = count
        
        # Average assignment time (for completed assignments)
        completed_assignments = db.query(DocumentAssignment).filter(
            DocumentAssignment.status == 'completed',
            DocumentAssignment.completed_at.isnot(None)
        ).all()
        
        total_time = 0
        if completed_assignments:
            for assignment in completed_assignments:
                time_diff = assignment.completed_at - assignment.created_at
                total_time += time_diff.total_seconds()
            
            avg_completion_time = total_time / len(completed_assignments) / 3600  # Hours
        else:
            avg_completion_time = 0
        
        # User workload distribution
        user_workloads = db.query(User.username, db.func.count(DocumentAssignment.id).label('active_count')).outerjoin(
            DocumentAssignment,
            (DocumentAssignment.user_id == User.id) & 
            (DocumentAssignment.status.in_(['assigned', 'in_progress']))
        ).group_by(User.id, User.username).all()
        
        return {
            "total_assignments": total_assignments,
            "status_distribution": status_counts,
            "avg_completion_time_hours": round(avg_completion_time, 2),
            "user_workloads": [
                {"username": username, "active_assignments": count}
                for username, count in user_workloads
            ]
        }
