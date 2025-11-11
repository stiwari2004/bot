"""
Structured logging configuration with request IDs
"""
import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Optional


# Context variable to store request ID for current request
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class StructuredFormatter(logging.Formatter):
    """JSON structured formatter for logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request ID if available
        request_id = request_id_context.get()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.__dict__.get('extra', {}))
        
        return json.dumps(log_data)


class RedactingFilter(logging.Filter):
    """Filter that redacts common secret patterns before formatting."""

    PATTERNS = [
        re.compile(r"(password|passwd|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
        re.compile(r"(Authorization|X-Api-Key|X-Access-Token)\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True

        redacted = message
        for pattern in self.PATTERNS:
            redacted = pattern.sub(lambda m: f"{m.group(1)}=***", redacted)

        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Setup structured logging configuration"""
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Use structured formatter
    formatter = StructuredFormatter()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RedactingFilter())
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set level for specific loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Import and apply to existing modules
    logging.getLogger("app").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with structured logging"""
    return logging.getLogger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set request ID for current context"""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_context.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """Get current request ID"""
    return request_id_context.get()

