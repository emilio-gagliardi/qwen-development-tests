# Exception Hierarchy Design

## Base Exception Classes

### RAGPipelineException
Root exception for all custom errors in the system.

```python
class RAGPipelineException(Exception):
    """Base exception for all RAG pipeline errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow()
        self.correlation_id: Optional[str] = None
        super().__init__(self.message)
    
    def with_correlation_id(self, correlation_id: str) -> 'RAGPipelineException':
        self.correlation_id = correlation_id
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
```

### DomainException
Base class for business logic violations.

```python
class DomainException(RAGPipelineException):
    """Base exception for domain layer errors."""
    pass
```

### InfrastructureException
Base class for external service failures.

```python
class InfrastructureException(RAGPipelineException):
    """Base exception for infrastructure layer errors."""
    pass
```

### ValidationException
Base class for input validation errors.

```python
class ValidationException(RAGPipelineException):
    """Base exception for validation errors."""
    pass
```

## Domain Exceptions

```python
class IntentClassificationError(DomainException):
    """Raised when intent classification fails."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "DOMAIN_001", context)

class ModelRoutingError(DomainException):
    """Raised when model routing decision fails."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "DOMAIN_002", context)

class DocumentRetrievalError(DomainException):
    """Raised when document retrieval fails."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "DOMAIN_003", context)

class ContextBuildingError(DomainException):
    """Raised when building context from retrieved documents."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "DOMAIN_004", context)

class GenerationError(DomainException):
    """Raised when LLM generation fails."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "DOMAIN_005", context)

class ConfigurationError(DomainException):
    """Raised when configuration is invalid or missing."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "DOMAIN_006", context)

class UnsupportedIntentTypeError(DomainException):
    """Raised when an unsupported intent type is encountered."""
    def __init__(self, intent_type: str, context: Optional[Dict] = None):
        super().__init__(
            f"Unsupported intent type: {intent_type}",
            "DOMAIN_007",
            {**(context or {}), "intent_type": intent_type}
        )

class InvalidModelTierError(DomainException):
    """Raised when an invalid model tier is specified."""
    def __init__(self, tier: str, context: Optional[Dict] = None):
        super().__init__(
            f"Invalid model tier: {tier}",
            "DOMAIN_008",
            {**(context or {}), "tier": tier}
        )

class ConfidenceThresholdError(DomainException):
    """Raised when confidence score doesn't meet threshold."""
    def __init__(self, score: float, threshold: float, context: Optional[Dict] = None):
        super().__init__(
            f"Confidence {score} below threshold {threshold}",
            "DOMAIN_009",
            {**(context or {}), "score": score, "threshold": threshold}
        )
```

## Infrastructure Exceptions

```python
class LiteLLMGatewayError(InfrastructureException):
    """Raised when LiteLLM gateway communication fails."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "INFRA_001", context)

class LangfuseIntegrationError(InfrastructureException):
    """Raised when Langfuse logging fails."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "INFRA_002", context)

class DocumentStoreError(InfrastructureException):
    """Raised when document store operations fail."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "INFRA_003", context)

class VectorSearchError(InfrastructureException):
    """Raised when vector search fails."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "INFRA_004", context)

class RerankerError(InfrastructureException):
    """Raised when reranking fails."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "INFRA_005", context)

class RateLimitExceededError(InfrastructureException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "INFRA_006", context)

class ProviderUnavailableError(InfrastructureException):
    """Raised when LLM provider is unavailable."""
    def __init__(self, provider: str, context: Optional[Dict] = None):
        super().__init__(
            f"Provider {provider} unavailable",
            "INFRA_007",
            {**(context or {}), "provider": provider}
        )

class AuthenticationError(InfrastructureException):
    """Raised when authentication fails."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "INFRA_008", context)
```

## Validation Exceptions

```python
class InvalidQueryError(ValidationException):
    """Raised when query is invalid."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "VALID_001", context)

class MissingRequiredFieldError(ValidationException):
    """Raised when a required field is missing."""
    def __init__(self, field: str, context: Optional[Dict] = None):
        super().__init__(
            f"Missing required field: {field}",
            "VALID_002",
            {**(context or {}), "field": field}
        )

class MalformedRequestError(ValidationException):
    """Raised when request format is malformed."""
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, "VALID_003", context)

class SchemaValidationError(ValidationException):
    """Raised when Pydantic validation fails."""
    def __init__(self, errors: List[Dict], context: Optional[Dict] = None):
        super().__init__(
            f"Schema validation failed with {len(errors)} errors",
            "VALID_004",
            {**(context or {}), "validation_errors": errors}
        )
```

## Exception Handler Middleware

```python
async def exception_handler(request: Request, exc: RAGPipelineException):
    logger.error(
        f"Exception occurred",
        extra={
            "error_code": exc.error_code,
            "correlation_id": exc.correlation_id,
            "context": exc.context
        }
    )
    return JSONResponse(
        status_code=get_status_code(exc),
        content=exc.to_dict()
    )
```
