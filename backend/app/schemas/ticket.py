"""
Ticket analysis schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class TicketAnalysisRequest(BaseModel):
    """Request for ticket analysis"""
    issue_description: str = Field(..., description="Description of the IT issue")
    severity: str = Field(default="medium", description="Issue severity level")
    service_type: Optional[str] = Field(None, description="Service type (server, network, database, etc.)")
    environment: str = Field(default="prod", description="Environment (prod, staging, dev)")


class RunbookMatch(BaseModel):
    """Information about a matched runbook"""
    id: int
    title: str
    similarity_score: float = Field(..., description="Semantic similarity score (0-1)")
    confidence_score: float = Field(..., description="Multi-factor confidence score (0-1)")
    success_rate: Optional[float] = Field(None, description="Historical success rate")
    times_used: int = Field(default=0, description="Number of times this runbook was used")
    last_used: Optional[str] = Field(None, description="ISO timestamp of last use")
    reasoning: str = Field(..., description="Explanation of why this runbook was suggested")
    
    class Config:
        from_attributes = True


class TicketAnalysisResponse(BaseModel):
    """Response from ticket analysis"""
    recommendation: Literal["existing_runbook", "generate_new", "escalate"]
    confidence: float = Field(..., description="Overall confidence in recommendation")
    reasoning: str = Field(..., description="Explanation of the recommendation")
    matched_runbooks: List[RunbookMatch] = Field(default_factory=list, description="List of similar runbooks found")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested next steps")
    threshold_used: float = Field(..., description="Confidence threshold that was applied")
    
    class Config:
        from_attributes = True


class RunbookUsageRequest(BaseModel):
    """Request to record runbook usage"""
    issue_description: str = Field(..., description="Issue that the runbook was used for")
    confidence_score: Optional[float] = Field(None, description="Confidence score when runbook was selected")


class RunbookFeedbackRequest(BaseModel):
    """Request to submit feedback on runbook"""
    was_helpful: bool = Field(..., description="Whether the runbook was helpful")
    feedback_text: Optional[str] = Field(None, description="Optional text feedback")
    execution_time_minutes: Optional[int] = Field(None, description="Time taken to execute")

