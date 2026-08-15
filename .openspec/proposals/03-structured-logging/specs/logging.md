# Structured Logging Design

## Logger Configuration

### Base Setup
```python
import structlog
from structlog.types import Processor, WrappedLogger
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
import uuid

def setup_logging(environment: str = "production") -> None:
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    log_level = getattr(logging, environment.upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
    
    # Configure structlog processors
    processors: List[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        CorrelationIDInjector(),
        ServiceContextAdder(service="rag-pipeline"),
        SensitiveDataFilter(),
        DurationCalculator(),
    ]
    
    if environment == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

## Custom Processors

### Correlation ID Injector
```python
class CorrelationIDInjector:
    """Inject correlation ID into every log entry."""
    
    def __call__(
        self, 
        logger: WrappedLogger, 
        method_name: str, 
        event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        correlation_id = structlog.contextvars.get_merged_contextvars().get(
            "correlation_id"
        )
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        
        event_dict["correlation_id"] = correlation_id
        return event_dict
```

### Service Context Adder
```python
@dataclass
class ServiceContextAdder:
    """Add service-wide context to logs."""
    service: str
    version: str = "1.0.0"
    environment: str = "production"
    
    def __call__(
        self,
        logger: WrappedLogger,
        method_name: str,
        event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        event_dict["service"] = self.service
        event_dict["version"] = self.version
        event_dict["environment"] = self.environment
        return event_dict
```

### Sensitive Data Filter
```python
class SensitiveDataFilter:
    """Redact sensitive information from logs."""
    
    SENSITIVE_FIELDS = {
        "api_key", "password", "secret", "token", "authorization",
        "credit_card", "ssn", "email", "phone"
    }
    REDACTED_VALUE = "[REDACTED]"
    
    def __call__(
        self,
        logger: WrappedLogger,
        method_name: str,
        event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        for key in list(event_dict.keys()):
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                event_dict[key] = self.REDACTED_VALUE
        
        # Redact in nested dicts
        for key, value in event_dict.items():
            if isinstance(value, dict):
                event_dict[key] = self._redact_dict(value)
            elif isinstance(value, str) and self._looks_like_secret(value):
                event_dict[key] = self.REDACTED_VALUE
        
        return event_dict
    
    def _redact_dict(self, data: Dict) -> Dict:
        for key in list(data.keys()):
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                data[key] = self.REDACTED_VALUE
        return data
    
    def _looks_like_secret(self, value: str) -> bool:
        # Simple heuristic for API keys
        if len(value) > 20 and re.match(r'^[A-Za-z0-9_-]+$', value):
            return True
        return False
```

### Duration Calculator
```python
class DurationCalculator:
    """Calculate operation duration when start_time is provided."""
    
    def __call__(
        self,
        logger: WrappedLogger,
        method_name: str,
        event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        if "start_time" in event_dict:
            start_time = event_dict.pop("start_time")
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            event_dict["duration_ms"] = round(duration, 2)
        return event_dict
```

## Context Managers

### Operation Timing Context
```python
@asynccontextmanager
async def log_operation(
    logger: Any,
    operation: str,
    component: str,
    **extra_context: Any
):
    """Context manager for logging operations with timing."""
    start_time = datetime.utcnow()
    structlog.contextvars.bind_contextvars(
        operation=operation,
        component=component,
        start_time=start_time,
        **extra_context
    )
    
    try:
        logger.info(f"Starting {operation}")
        yield
        logger.info(f"Completed {operation}")
    except Exception as e:
        logger.error(
            f"Failed {operation}",
            extra={"error": str(e), "error_type": type(e).__name__}
        )
        raise
    finally:
        structlog.contextvars.clear_contextvars()
```

### Correlation ID Context
```python
@asynccontextmanager
async def correlation_id_context(correlation_id: Optional[str] = None):
    """Set correlation ID for async context."""
    cid = correlation_id or str(uuid.uuid4())
    token = structlog.contextvars.bind_contextvars(correlation_id=cid)
    try:
        yield cid
    finally:
        structlog.contextvars.reset_contextvars(token)
```

## Usage Examples

### Basic Logging
```python
logger = structlog.get_logger(__name__)

async def classify_intent(query: str) -> IntentClassification:
    async with log_operation(logger, "classify_intent", "intent_classifier"):
        result = await self._classify(query)
        logger.info(
            "Intent classified",
            intent_type=result.intent_type.value,
            confidence=result.confidence,
            model_used=result.model_name
        )
        return result
```

### Error Logging
```python
try:
    response = await gateway.generate(prompt, model)
except LiteLLMGatewayError as e:
    logger.error(
        "LiteLLM gateway error",
        error_code=e.error_code,
        context=e.context,
        original_error=str(e.original_exception)
    )
    raise
```

### Request Logging Middleware
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID")
    
    async with correlation_id_context(correlation_id):
        start_time = time.time()
        
        logger.info(
            "Request received",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host
        )
        
        response = await call_next(request)
        
        duration = (time.time() - start_time) * 1000
        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration_ms=round(duration, 2)
        )
        
        return response
```

## Log Output Example
```json
{
  "timestamp": "2025-01-15T10:30:00.000Z",
  "level": "info",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "service": "rag-pipeline",
  "version": "1.0.0",
  "environment": "production",
  "component": "intent_classifier",
  "operation": "classify_intent",
  "event": "Intent classified",
  "intent_type": "technical_question",
  "confidence": 0.94,
  "model_used": "deepseek-chat",
  "duration_ms": 145.23
}
```
