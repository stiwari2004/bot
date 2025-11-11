"""
Application configuration settings
"""
from typing import Dict, List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Troubleshooting AI Agent"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/troubleshooting_ai"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Vector Store
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DIMENSION: int = 1024
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    
    # LLM
    LLM_MODEL: str = "llama3.1:8b"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_BUDGET_DEFAULT_TOKENS: int = 500_000
    LLM_BUDGET_WINDOW_SECONDS: int = 86_400  # 24 hours rolling
    LLM_RATE_LIMIT_PER_MINUTE: int = 30
    LLM_BUDGET_ALERT_THRESHOLD: float = 0.8
    LLM_TENANT_BUDGETS: Dict[int, int] = {}
    LLM_POLICY_CACHE_TTL_SECONDS: int = 300
    
    # File Upload
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    UPLOAD_DIR: str = "uploads"
    
    # Multi-tenant
    DEFAULT_TENANT: str = "default"

    # Queue / Streaming (Redis Streams)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAM_ASSIGN: str = "session.assign"
    REDIS_STREAM_COMMAND: str = "session.command"
    REDIS_STREAM_RESULT: str = "session.result"
    REDIS_STREAM_EVENTS: str = "session.events"
    REDIS_STREAM_DEAD_LETTER: str = "session.deadletter"
    REDIS_CONSUMER_GROUP_ORCHESTRATOR: str = "orchestrator"
    REDIS_DEFAULT_MAXLEN: int = 10_000
    WORKER_ORCHESTRATION_ENABLED: bool = True
    IDEMPOTENCY_TTL_SECONDS: int = 86_400
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_PATH: str = "logs/audit.log"
    AUDIT_LOG_S3_BUCKET: Optional[str] = None
    AUDIT_LOG_S3_PREFIX: str = "audit-log/"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator("LLM_TENANT_BUDGETS", mode="before")
    @classmethod
    def _parse_tenant_budgets(cls, value: Union[str, Dict[int, int], None]) -> Dict[int, int]:
        if value in (None, "", {}):
            return {}
        if isinstance(value, dict):
            parsed: Dict[int, int] = {}
            for key, val in value.items():
                try:
                    parsed[int(key)] = int(val)
                except Exception:
                    continue
            return parsed
        if isinstance(value, str):
            parsed: Dict[int, int] = {}
            parts = [part.strip() for part in value.split(",") if part.strip()]
            for part in parts:
                if "=" not in part:
                    continue
                tenant, limit = part.split("=", 1)
                try:
                    parsed[int(tenant.strip())] = int(limit.strip())
                except Exception:
                    continue
            return parsed
        return {}


# Create settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

