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
    DEBUG: bool = False  # Security: Default to False, must be explicitly enabled
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str  # No default - must be set via environment variable
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Security
    SECRET_KEY: str  # No default - must be set via environment variable
    CREDENTIAL_ENCRYPTION_KEY: Optional[str] = None  # Optional - will be validated in credential_service
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Environment
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # External APIs
    PERPLEXITY_API_KEY: Optional[str] = None
    
    # CORS - Can be set as comma-separated string or JSON array
    ALLOWED_HOSTS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:8000", "http://localhost:8001"]
    
    # Rate Limiting (MF-10)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60  # Requests per minute per IP
    RATE_LIMIT_PER_HOUR: int = 1000  # Requests per hour per IP
    
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
    
    # URLs and Endpoints
    FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
    BACKEND_BASE_URL: str = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    OAUTH_CALLBACK_URL: str = os.getenv("OAUTH_CALLBACK_URL", "http://localhost:8000/oauth/callback")
    
    # Multi-tenant
    DEFAULT_TENANT_ID: int = int(os.getenv("DEFAULT_TENANT_ID", "1"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment (like PERPLEXITY_API_KEY, ENVIRONMENT, etc.)
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from string (comma-separated) or list"""
        if isinstance(v, str):
            # Try JSON first
            try:
                import json
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # Fall back to comma-separated
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate SECRET_KEY is set and secure (lenient in development)"""
        if not v:
            raise ValueError("SECRET_KEY must be set via environment variable")
        
        # Check if we're in development
        environment = os.getenv("ENVIRONMENT", "").lower()
        is_development = environment in ("development", "dev", "") or os.getenv("DOCKER_COMPOSE") == "true"
        
        # In development, allow temporary defaults but warn; in production, require secure key
        default_values = ["your-secret-key-change-in-production", "dev-secret-key-temp-allow-in-development-only-change-me"]
        if v in default_values:
            if is_development:
                import warnings
                warnings.warn(
                    "Using default/temporary SECRET_KEY in development. "
                    "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))' "
                    "and set it in backend/.env file or docker-compose.yml",
                    UserWarning
                )
                # For development, we'll allow it but recommend changing
                return v
            else:
                raise ValueError(
                    "SECRET_KEY must be set to a secure random value (not a default). "
                    "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
        
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str, info) -> str:
        """Validate DATABASE_URL doesn't contain default credentials (except in development)"""
        if not v:
            raise ValueError("DATABASE_URL must be set via environment variable")
        
        # Allow default password in development/docker-compose environments
        environment = os.getenv("ENVIRONMENT", "").lower()
        is_development = environment in ("development", "dev", "") or os.getenv("DOCKER_COMPOSE") == "true"
        
        # Check for default credentials (only block in production)
        if not is_development and (":password@" in v or "postgres:password" in v):
            raise ValueError(
                "Default database password detected in DATABASE_URL. "
                "Set a secure DATABASE_URL in environment variables for production."
            )
        return v
    
    @field_validator("DEBUG")
    @classmethod
    def validate_debug_mode(cls, v: bool, info) -> bool:
        """Prevent DEBUG mode in production"""
        environment = os.getenv("ENVIRONMENT", "").lower()
        if v and environment == "production":
            raise ValueError("DEBUG mode cannot be enabled in production environment")
        return v
    
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

