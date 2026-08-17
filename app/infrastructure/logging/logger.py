"""
Structured logging infrastructure with correlation ID support.

Provides JSON-formatted logging with automatic inclusion of:
- Correlation IDs for request tracing
- Timestamp in ISO format
- Log level and logger name
- Structured extra fields
- Exception details with stack traces
"""
import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import contextvars

from app.core.config import ConfigSingleton


# Context variable for correlation ID (thread-safe async context)
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", 
    default=None
)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: Optional[str]) -> None:
    """Set correlation ID in current context."""
    correlation_id_ctx.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid4())


class StructuredLogFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs logs as JSON objects with consistent fields:
    - timestamp: ISO 8601 format
    - level: Log level name
    - logger: Logger name
    - message: Log message
    - correlation_id: Request correlation ID (if present)
    - extra_fields: Additional structured data
    
    Usage:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(handler)
    """
    
    def __init__(
        self,
        include_extra: bool = True,
        include_stack_trace: bool = True,
    ) -> None:
        super().__init__()
        self.include_extra = include_extra
        self.include_stack_trace = include_stack_trace
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation ID if present
        corr_id = get_correlation_id()
        if corr_id:
            log_data["correlation_id"] = corr_id
        elif hasattr(record, 'correlation_id') and record.correlation_id:
            log_data["correlation_id"] = record.correlation_id
        
        # Add extra fields from both record and context
        if self.include_extra:
            extra_fields = self._extract_extra_fields(record)
            # Merge with context extra fields
            context_extra = get_extra_fields()
            if context_extra:
                extra_fields.update(context_extra)
            if extra_fields:
                log_data["extra"] = extra_fields
        
        # Add exception info if present
        if self.include_stack_trace and record.exc_info:
            log_data["exception"] = self._format_exception(record.exc_info)
        
        return json.dumps(log_data, default=str)
    
    def _extract_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract extra fields from log record."""
        reserved_attrs = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text',
            'filename', 'funcName', 'levelname', 'levelno', 'lineno',
            'module', 'msecs', 'message', 'msg', 'name', 'pathname',
            'process', 'processName', 'relativeCreated', 'stack_info',
            'thread', 'threadName', 'correlation_id'
        }
        
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in reserved_attrs:
                extra_fields[key] = value
        
        return extra_fields
    
    def _format_exception(
        self, 
        exc_info: tuple[type, BaseException, Any]
    ) -> Dict[str, Any]:
        """Format exception information."""
        exc_type, exc_value, exc_tb = exc_info
        
        return {
            "type": exc_type.__name__ if exc_type else "Unknown",
            "message": str(exc_value),
            "traceback": traceback.format_exception(*exc_info),
        }


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds correlation ID to log records.
    
    Automatically injects correlation ID from context into each log record.
    
    Usage:
        logger.addFilter(CorrelationIdFilter())
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to log record."""
        record.correlation_id = get_correlation_id()
        return True


def setup_logging(
    level: Optional[str] = None,
    log_format: Optional[str] = None,
    enable_correlation_id: Optional[bool] = None,
    handlers: Optional[List[logging.Handler]] = None,
) -> None:
    """
    Configure application-wide logging settings.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        enable_correlation_id: Whether to include correlation IDs
        handlers: Custom handlers (defaults to stdout)
    
    Usage:
        setup_logging(level="INFO", log_format="json")
    """
    # Load defaults from config
    config = ConfigSingleton.get_instance()
    
    log_level = level or config.settings.log_level
    fmt = log_format or config.settings.log_format
    use_corr_id = enable_correlation_id if enable_correlation_id is not None else config.settings.enable_correlation_id
    
    # Parse log level
    try:
        log_level_enum = getattr(logging, log_level.upper())
    except AttributeError:
        log_level_enum = logging.INFO
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_enum)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create handlers
    if handlers is None:
        handlers = [logging.StreamHandler(sys.stdout)]
    
    # Set up formatters and filters
    for handler in handlers:
        if fmt.lower() == 'json':
            handler.setFormatter(StructuredLogFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        if use_corr_id:
            handler.addFilter(CorrelationIdFilter())
        
        root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('haystack').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Starting process", extra={"step": "initialization"})
    """
    return logging.getLogger(name)


# Context variable for extra fields (thread-safe async context)
extra_fields_ctx: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "extra_fields", 
    default={}
)


def get_extra_fields() -> Dict[str, Any]:
    """Get current extra fields from context."""
    return extra_fields_ctx.get()


def set_extra_fields(extra_fields: Dict[str, Any]) -> None:
    """Set extra fields in current context."""
    extra_fields_ctx.set(extra_fields)


class LogContext:
    """
    Context manager for temporary logging context.
    
    Temporarily sets correlation ID and/or extra fields for the duration
    of the context. Properly propagates both through async contexts using
    contextvars.
    
    Usage:
        with LogContext(correlation_id="req-123"):
            logger.info("Processing request")
        
        with LogContext(extra_fields={"user_id": "u-456"}):
            logger.info("User action")
            
        with LogContext(correlation_id="req-456", extra_fields={"step": "validation"}):
            logger.info("Validating data")
    """
    
    def __init__(
        self,
        correlation_id: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.correlation_id = correlation_id
        self.extra_fields = extra_fields or {}
        self._previous_corr_id: Optional[str] = None
        self._previous_extra_fields: Dict[str, Any] = {}
    
    def __enter__(self) -> 'LogContext':
        """Enter context and set correlation ID and extra fields."""
        # Save previous state
        self._previous_corr_id = get_correlation_id()
        self._previous_extra_fields = get_extra_fields().copy()
        
        # Set new values
        if self.correlation_id:
            set_correlation_id(self.correlation_id)
        if self.extra_fields:
            set_extra_fields(self.extra_fields)
        
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore previous correlation ID and extra fields."""
        # Restore previous state
        if self._previous_corr_id is not None:
            set_correlation_id(self._previous_corr_id)
        elif self.correlation_id:
            set_correlation_id(None)
        
        if self._previous_extra_fields:
            set_extra_fields(self._previous_extra_fields)
        elif self.extra_fields:
            set_extra_fields({})


__all__ = [
    'StructuredLogFormatter',
    'CorrelationIdFilter',
    'setup_logging',
    'get_logger',
    'LogContext',
    'get_correlation_id',
    'set_correlation_id',
    'generate_correlation_id',
]
