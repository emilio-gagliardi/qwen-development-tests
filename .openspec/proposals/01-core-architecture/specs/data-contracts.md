# Data Contracts & Type Safety

## Core Principles
1. **No Silent Nulls**: Methods never return `None` to indicate failure.
2. **Explicit Errors**: Failures return `Failure[ErrorDetail]` objects containing context.
3. **Primitive Restriction**: Primitives (`int`, `float`, `str`) only for simple values. All complex data must be Pydantic models.
4. **Immutable Domain**: All domain entities are immutable Pydantic models.
5. **Schema Enforcement**: All incoming/outgoing data validated via Pydantic schemas.

## Result Pattern Implementation
We use a Generic `Result[T, E]` type alias to enforce explicit handling of success/failure.

```python
from typing import Generic, TypeVar, Union, Optional
from pydantic import BaseModel
from datetime import datetime

T = TypeVar('T')
E = TypeVar('E', bound='ErrorDetail')

class Success(BaseModel, Generic[T]):
    """Represents a successful operation result."""
    success: bool = True
    data: T
    metadata: dict[str, any] = {}

class Failure(BaseModel, Generic[E]):
    """Represents a failed operation result with error details."""
    success: bool = False
    error: E
    traceback: Optional[str] = None

Result = Union[Success[T], Failure[E]]
```

## Error Detail Hierarchy
All errors must extend `ErrorDetail` to ensure consistent serialization and logging.

```python
class ErrorDetail(BaseModel):
    """Base class for all error details."""
    code: str
    message: str
    context: dict[str, any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        frozen = True  # Immutable
```

## Pydantic Schema Enforcement Rules

### External API Boundaries
- All FastAPI request/response bodies MUST be Pydantic models
- Query parameters auto-validated by FastAPI/Pydantic
- Headers validated via custom dependencies if complex

### Internal Service Boundaries
- Service methods return `Result[DomainModel, ServiceError]`
- Repository methods return `Result[Entity, RepositoryError]`
- Gateway methods return `Result[ResponseDTO, GatewayError]`

### Domain Layer
- Entities: Immutable Pydantic models with business logic
- Value Objects: Immutable Pydantic models without identity
- Aggregates: Root entities managing consistency boundaries

### Example Service Method Signature
```python
async def classify_intent(
    self, 
    query: str, 
    correlation_id: str
) -> Result[IntentClassification, IntentClassificationError]:
    """
    Classifies user intent.
    
    Returns:
        Success[IntentClassification] on success
        Failure[IntentClassificationError] on failure (never None)
    """
```

## Validation Strategy
1. **Early Validation**: Validate at system boundaries (API, messaging)
2. **Fail Fast**: Invalid data rejected immediately with clear error
3. **Context Preservation**: Errors include full context for debugging
4. **Type Safety**: MyPy strict mode enforced in CI/CD

## Null Handling Policy
- `Optional[T]` ONLY used when null is a valid business state
- Never use `None` to signal errors
- Use `Result` pattern for operations that can fail
- Default values provided for optional fields where appropriate
