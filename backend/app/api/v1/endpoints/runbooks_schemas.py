"""
Shared Pydantic models for runbook endpoints
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, validator


class ServiceType(str, Enum):
    SERVER = "server"
    DATABASE = "database"
    WEB = "web"
    STORAGE = "storage"
    NETWORK = "network"
    AUTO = "auto"
    WINDOWS = "Windows"
    LINUX = "Linux"


class EnvironmentType(str, Enum):
    PROD = "prod"
    STAGING = "staging"
    DEV = "dev"
    TESTING = "testing"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GenerateAgentRunbookRequest(BaseModel):
    issue_description: str = Field(..., min_length=10, max_length=5000)
    service: ServiceType
    env: EnvironmentType
    risk: RiskLevel

    @validator("issue_description")
    def validate_issue_description(cls, v):
        if not v or not v.strip():
            raise ValueError("Issue description cannot be empty")
        sanitized = "".join(c for c in v if ord(c) >= 32 or c in "\n\t")
        if len(sanitized) < 10:
            raise ValueError("Issue description must be at least 10 characters")
        return sanitized


class RunbookStepApproveBody(BaseModel):
    section: str = Field(..., description="prechecks, steps, or postchecks")
    index: int = Field(..., ge=0, description="0-based step index")


class RunbookStepCommandBody(BaseModel):
    section: str = Field(..., description="prechecks, steps, or postchecks")
    index: int = Field(..., ge=0, description="0-based step index")
    command: str = Field(..., min_length=1)


class RunbookStepRegenerateBody(BaseModel):
    section: str = Field(..., description="prechecks, steps, or postchecks")
    index: int = Field(..., ge=0, description="0-based step index")
    human_context: Optional[str] = Field(None, description="Optional human context for regeneration")


class UserInputsRequest(BaseModel):
    inputs: dict = Field(..., description="Dictionary of input names to values")
