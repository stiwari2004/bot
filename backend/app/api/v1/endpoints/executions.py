"""
Execution tracking API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.models.execution_session import ExecutionSession, ExecutionStep, ExecutionFeedback
from app.models.runbook import Runbook
from app.models.runbook_usage import RunbookUsage
from app.services.runbook_parser import RunbookParser
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


# Request models
class ExecutionSessionCreate(BaseModel):
    runbook_id: int
    issue_description: str


class ExecutionStepUpdate(BaseModel):
    step_number: int
    step_type: str
    completed: bool
    success: Optional[bool] = None
    output: Optional[str] = None
    notes: Optional[str] = None


class ExecutionFeedbackCreate(BaseModel):
    was_successful: bool
    issue_resolved: bool
    rating: int
    feedback_text: Optional[str] = None
    suggestions: Optional[str] = None


# Response models
class ExecutionSessionResponse(BaseModel):
    id: int
    runbook_id: int
    runbook_title: str
    issue_description: str
    status: str
    started_at: str
    completed_at: Optional[str]
    total_duration_minutes: Optional[int]
    steps: List[dict] = []


class ExecutionHistoryResponse(BaseModel):
    sessions: List[dict]


@router.post("/demo/sessions", response_model=ExecutionSessionResponse)
async def create_execution_session(data: ExecutionSessionCreate, db: Session = Depends(get_db)):
    """Create a new execution session for a runbook"""
    try:
        # Get runbook
        runbook = db.query(Runbook).filter(Runbook.id == data.runbook_id).first()
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        
        # Create session (demo tenant_id = 1, no user)
        session = ExecutionSession(
            tenant_id=1,
            runbook_id=data.runbook_id,
            issue_description=data.issue_description,
            status="in_progress"
        )
        db.add(session)
        db.flush()  # Get session ID
        
        # Parse runbook body to create steps
        parser = RunbookParser()
        parsed = parser.parse_runbook(runbook.body_md)
        
        # Create step entries
        step_num = 1
        for precheck in parsed.get("prechecks", []):
            step = ExecutionStep(
                session_id=session.id,
                step_number=step_num,
                step_type="precheck",
                command=precheck.get("command"),
            )
            db.add(step)
            step_num += 1
        
        for main_step in parsed.get("main_steps", []):
            step = ExecutionStep(
                session_id=session.id,
                step_number=step_num,
                step_type="main",
                command=main_step.get("command"),
            )
            db.add(step)
            step_num += 1
        
        for postcheck in parsed.get("postchecks", []):
            step = ExecutionStep(
                session_id=session.id,
                step_number=step_num,
                step_type="postcheck",
                command=postcheck.get("command"),
            )
            db.add(step)
            step_num += 1
        
        db.commit()
        db.refresh(session)
        
        # Return with steps
        return ExecutionSessionResponse(
            id=session.id,
            runbook_id=session.runbook_id,
            runbook_title=runbook.title,
            issue_description=session.issue_description,
            status=session.status,
            started_at=session.started_at.isoformat(),
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            total_duration_minutes=session.total_duration_minutes,
            steps=[{
                "id": s.id,
                "step_number": s.step_number,
                "step_type": s.step_type,
                "command": s.command,
                "completed": s.completed,
                "success": s.success,
                "output": s.output,
                "notes": s.notes
            } for s in session.steps]
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/sessions/{session_id}", response_model=ExecutionSessionResponse)
async def get_execution_session(session_id: int, db: Session = Depends(get_db)):
    """Get execution session details with all steps"""
    session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Execution session not found")
    
    runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
    
    return ExecutionSessionResponse(
        id=session.id,
        runbook_id=session.runbook_id,
        runbook_title=runbook.title if runbook else "Unknown",
        issue_description=session.issue_description,
        status=session.status,
        started_at=session.started_at.isoformat(),
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
        total_duration_minutes=session.total_duration_minutes,
        steps=[{
            "id": s.id,
            "step_number": s.step_number,
            "step_type": s.step_type,
            "command": s.command,
            "completed": s.completed,
            "success": s.success,
            "output": s.output,
            "notes": s.notes
        } for s in sorted(session.steps, key=lambda x: x.step_number)]
    )


@router.patch("/demo/sessions/{session_id}/steps")
async def update_execution_step(
    session_id: int, 
    step_data: ExecutionStepUpdate,
    db: Session = Depends(get_db)
):
    """Update a specific step's completion status"""
    try:
        # Verify session exists
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Find the step
        step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == step_data.step_number,
            ExecutionStep.step_type == step_data.step_type
        ).first()
        
        if not step:
            raise HTTPException(status_code=404, detail="Execution step not found")
        
        # Update step
        step.completed = step_data.completed
        if step_data.success is not None:
            step.success = step_data.success
        if step_data.output is not None:
            step.output = step_data.output
        if step_data.notes is not None:
            step.notes = step_data.notes
        if step_data.completed:
            step.completed_at = datetime.now()
        
        db.commit()
        
        return {"message": "Step updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/sessions/{session_id}/complete")
async def complete_execution_session(
    session_id: int,
    feedback: ExecutionFeedbackCreate,
    db: Session = Depends(get_db)
):
    """Complete an execution session and record feedback"""
    try:
        # Get session
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Calculate duration
        completed_at = datetime.now()
        duration_minutes = int((completed_at - session.started_at).total_seconds() / 60)
        
        # Update session
        session.status = "completed" if feedback.was_successful else "failed"
        session.completed_at = completed_at
        session.total_duration_minutes = duration_minutes
        
        # Create feedback
        feedback_record = ExecutionFeedback(
            session_id=session_id,
            was_successful=feedback.was_successful,
            issue_resolved=feedback.issue_resolved,
            rating=feedback.rating,
            feedback_text=feedback.feedback_text,
            suggestions=feedback.suggestions
        )
        db.add(feedback_record)
        
        # Create or update runbook usage tracking
        runbook_usage = RunbookUsage(
            runbook_id=session.runbook_id,
            tenant_id=session.tenant_id,
            user_id=session.user_id,
            issue_description=session.issue_description,
            confidence_score=0.0,  # Will be set by search/analysis
            was_helpful=feedback.was_successful,
            feedback_text=feedback.feedback_text,
            execution_time_minutes=duration_minutes
        )
        db.add(runbook_usage)
        
        db.commit()
        
        return {"message": "Execution session completed", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/runbooks/{runbook_id}/executions", response_model=ExecutionHistoryResponse)
async def get_runbook_execution_history(runbook_id: int, db: Session = Depends(get_db)):
    """Get all execution sessions for a specific runbook"""
    sessions = db.query(ExecutionSession).filter(
        ExecutionSession.runbook_id == runbook_id
    ).order_by(ExecutionSession.started_at.desc()).all()
    
    result = []
    for session in sessions:
        feedback_data = None
        if session.feedback:
            feedback_data = {
                "was_successful": session.feedback.was_successful,
                "issue_resolved": session.feedback.issue_resolved,
                "rating": session.feedback.rating,
                "feedback_text": session.feedback.feedback_text
            }
        
        result.append({
            "id": session.id,
            "runbook_id": session.runbook_id,
            "issue_description": session.issue_description,
            "status": session.status,
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_duration_minutes": session.total_duration_minutes,
            "steps_count": len(session.steps),
            "feedback": feedback_data
        })
    
    return ExecutionHistoryResponse(sessions=result)


@router.get("/demo/executions", response_model=ExecutionHistoryResponse)
async def list_all_executions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all execution sessions (paginated)"""
    sessions = db.query(ExecutionSession).filter(
        ExecutionSession.tenant_id == 1  # Demo tenant
    ).order_by(ExecutionSession.started_at.desc()).limit(limit).offset(offset).all()
    
    result = []
    for session in sessions:
        runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
        feedback_data = None
        if session.feedback:
            feedback_data = {
                "was_successful": session.feedback.was_successful,
                "issue_resolved": session.feedback.issue_resolved,
                "rating": session.feedback.rating
            }
        
        result.append({
            "id": session.id,
            "runbook_id": session.runbook_id,
            "runbook_title": runbook.title if runbook else "Unknown",
            "issue_description": session.issue_description,
            "status": session.status,
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_duration_minutes": session.total_duration_minutes,
            "feedback": feedback_data
        })
    
    return ExecutionHistoryResponse(sessions=result)


