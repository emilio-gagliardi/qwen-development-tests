# Design Specification

## Architecture Layers

### Domain Layer
The domain layer contains core business logic that is independent of external frameworks:
- **Entities**: `Document`, `Query`, `Intent`, `ModelDecision` (all immutable with `frozen=True`)
- **Value Objects**: `ModelTier`, `IntentType`, `ConfidenceScore`, `CorrelationId`, `RequestId`
- **Domain Services**: Pure business logic operations with Result[T, E] returns
- **Protocols**: Interface definitions for repositories, gateways, classifiers

### Application Layer
Orchestrates domain objects to execute use cases:
- **Use Cases**: `ProcessRAGQuery`, `ClassifyIntent`, `RouteModel` (all async with proper error handling)
- **DTOs**: Data transfer objects for inter-layer communication (Pydantic models)
- **Validators**: Business rule validation with explicit error types
- **Result Types**: `Success[T]` and `Failure[E]` for all operations

### Infrastructure Layer
Implements interfaces defined in domain/application layers:
- **Repositories**: Document storage abstraction with async support
- **External Services**: LiteLLM client with connection pooling, Langfuse integration
- **Message Bus**: Async event publishing with backpressure awareness
- **Connection Pools**: HTTP client pools with keepalive and retry logic

### Presentation Layer
FastAPI-based API endpoints:
- **Controllers**: Request/response handling with correlation ID injection
- **Middleware**: Correlation ID generation, timeout enforcement, backpressure monitoring
- **Schemas**: Pydantic models for API contracts with strict validation
- **Rate Limiters**: Token bucket implementation per endpoint

## Async-Safe Configuration Singleton

```python
import asyncio
from typing import Optional, Any
from pydantic import FrozenSet
from app.core.settings import Settings

class ConfigSingleton:
    """
    Async-safe configuration singleton with frozen state guarantees.
    
    This singleton ensures thread-safe initialization under concurrent load
    using asyncio.Lock. Once initialized, the configuration becomes immutable
    to prevent race conditions during runtime.
    
    Attributes:
        _instance: Class-level singleton instance reference
        _lock: Asyncio lock for thread-safe initialization
        _settings: Frozen settings object after initialization
        _initialized: Flag indicating completion of initialization
    
    Example:
        >>> config = await ConfigSingleton.get_instance()
        >>> api_key = config.settings.OPENAI_API_KEY
        >>> # config.settings is frozen - cannot be modified
    """
    _instance: Optional['ConfigSingleton'] = None
    _lock: asyncio.Lock = asyncio.Lock()
    _settings: Optional[Settings] = None
    _initialized: bool = False
    
    def __init__(self) -> None:
        """Private constructor to prevent direct instantiation."""
        if self._initialized:
            raise RuntimeError("ConfigSingleton already initialized")
    
    async def _initialize(self) -> None:
        """
        Initialize settings with asyncio lock protection.
        
        This method loads settings from environment variables and validates
        them using pydantic-settings. The lock ensures only one initialization
        occurs even under concurrent access.
        """
        async with self._lock:
            if self._initialized:
                return
            self._settings = Settings()
            self._initialized = True
    
    @classmethod
    async def get_instance(cls) -> 'ConfigSingleton':
        """
        Get or create the singleton instance with async safety.
        
        Returns:
            ConfigSingleton: The singleton instance with loaded settings
        
        Raises:
            RuntimeError: If initialization fails
        """
        if cls._instance is None:
            instance = cls.__new__(cls)
            await instance._initialize()
            cls._instance = instance
        return cls._instance
    
    @property
    def settings(self) -> Settings:
        """
        Get the frozen settings object.
        
        Returns:
            Settings: Immutable configuration object
        
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or self._settings is None:
            raise RuntimeError("ConfigSingleton not initialized")
        return self._settings
```

## Backpressure Controller

```python
import asyncio
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class BackpressureConfig:
    """Configuration for backpressure control mechanisms."""
    max_concurrent_requests: int = 500
    rate_limit_tokens: float = 1000.0
    rate_limit_capacity: float = 1000.0
    queue_max_size: int = 1000
    circuit_breaker_threshold: int = 10
    circuit_breaker_timeout: int = 30

class BackpressureController:
    """Hybrid backpressure controller combining semaphores, token bucket, and circuit breakers."""
    
    def __init__(self, config: BackpressureConfig) -> None:
        self._config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self._token_bucket = asyncio.Queue(maxsize=int(config.rate_limit_capacity))
        self._queue = asyncio.Queue(maxsize=config.queue_max_size)
        self._failure_count = 0
        self._circuit_open = False
        self._last_failure_time: Optional[datetime] = None
    
    async def acquire(self) -> asyncio.Semaphore:
        """Acquire permission to process a request within concurrency limits."""
        if self._circuit_open:
            raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            await asyncio.wait_for(self._token_bucket.get(), timeout=5.0)
        except asyncio.TimeoutError:
            raise RateLimitExceededError("Rate limit exceeded")
        
        await self._semaphore.acquire()
        return self._semaphore
    
    def record_success(self) -> None:
        """Record successful request, resetting failure count."""
        self._failure_count = max(0, self._failure_count - 1)
    
    def record_failure(self) -> None:
        """Record failed request, potentially tripping circuit breaker."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        if self._failure_count >= self._config.circuit_breaker_threshold:
            self._circuit_open = True

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and rejecting requests."""
    pass

class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""
    pass
```

## Correlation ID Manager

```python
import uuid
import contextvars
from typing import Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class CorrelationId:
    """Value object representing a unique request correlation ID."""
    value: str
    
    @classmethod
    def new(cls) -> 'CorrelationId':
        """Generate a new correlation ID using UUIDv4."""
        return cls(value=str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value

_correlation_id_ctx: contextvars.ContextVar[Optional[CorrelationId]] = \
    contextvars.ContextVar('correlation_id', default=None)

class CorrelationIdManager:
    """Manages correlation ID lifecycle and context propagation across async boundaries."""
    
    @staticmethod
    def generate() -> CorrelationId:
        """Generate a new correlation ID."""
        return CorrelationId.new()
    
    @staticmethod
    def set_current(correlation_id: CorrelationId) -> None:
        """Set correlation ID in current async context."""
        _correlation_id_ctx.set(correlation_id)
    
    @staticmethod
    def get_current() -> Optional[CorrelationId]:
        """Get correlation ID from current async context."""
        return _correlation_id_ctx.get()
    
    @staticmethod
    def get_or_generate() -> CorrelationId:
        """Get current correlation ID or generate a new one."""
        current = _correlation_id_ctx.get()
        if current is None:
            new_id = CorrelationId.new()
            _correlation_id_ctx.set(new_id)
            return new_id
        return current
```

## Connection Pool Manager

```python
import httpx
from typing import Optional, Dict
from dataclasses import dataclass

@dataclass(frozen=True)
class ConnectionPoolConfig:
    """Configuration for HTTP connection pools."""
    max_connections: int = 100
    max_keepalive_connections: int = 50
    keepalive_expiry: float = 30.0
    timeout: float = 30.0

class ConnectionPoolManager:
    """Manages HTTP client connection pools for external services."""
    
    def __init__(self, config: ConnectionPoolConfig) -> None:
        self._config = config
        self._clients: Dict[str, httpx.AsyncClient] = {}
    
    def create_client(self, name: str, base_url: Optional[str] = None) -> httpx.AsyncClient:
        """Create a new pooled HTTP client with keepalive and limits."""
        limits = httpx.Limits(
            max_connections=self._config.max_connections,
            max_keepalive_connections=self._config.max_keepalive_connections,
            keepalive_expiry=self._config.keepalive_expiry
        )
        
        timeout = httpx.Timeout(timeout=self._config.timeout)
        
        client = httpx.AsyncClient(
            base_url=base_url,
            limits=limits,
            timeout=timeout,
            follow_redirects=False
        )
        
        self._clients[name] = client
        return client
    
    def get_client(self, name: str) -> httpx.AsyncClient:
        """Get existing client by name."""
        if name not in self._clients:
            raise KeyError(f"Client '{name}' not found")
        return self._clients[name]
    
    async def close_all(self) -> None:
        """Close all HTTP clients and release connections."""
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
```

## Registry Pattern (Async-Safe)

```python
import asyncio
from typing import Any, Callable, Dict

class ServiceRegistry:
    """Async-safe service registry with factory support."""
    _services: Dict[str, Any] = {}
    _factories: Dict[str, Callable[[], Any]] = {}
    _lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    async def register(cls, name: str, service: Any) -> None:
        """Register a service instance."""
        async with cls._lock:
            cls._services[name] = service
    
    @classmethod
    async def register_factory(cls, name: str, factory: Callable[[], Any]) -> None:
        """Register a factory function for lazy service creation."""
        async with cls._lock:
            cls._factories[name] = factory
    
    @classmethod
    async def get(cls, name: str) -> Any:
        """Get service instance, creating via factory if needed."""
        async with cls._lock:
            if name not in cls._services and name in cls._factories:
                factory = cls._factories[name]
                if asyncio.iscoroutinefunction(factory):
                    cls._services[name] = await factory()
                else:
                    cls._services[name] = factory()
            
            if name not in cls._services:
                raise KeyError(f"Service '{name}' not registered")
            
            return cls._services[name]
```

## Dependency Flow
```
Presentation → Application → Domain ← Infrastructure
                    ↑
              Configuration Singleton (async-safe)
                    ↑
              Service Registry (async-safe)
                    ↑
          Backpressure Controller
                    ↑
          Connection Pool Manager
```

## Module Structure
```
app/
├── domain/
│   ├── entities/
│   ├── value_objects/
│   ├── protocols/
│   └── result.py
├── application/
│   ├── use_cases/
│   ├── dtos/
│   └── validators/
├── infrastructure/
│   ├── repositories/
│   ├── external/
│   ├── pooling/
│   └── messaging/
├── presentation/
│   ├── controllers/
│   ├── middleware/
│   └── schemas/
└── core/
    ├── config.py
    ├── registry.py
    ├── backpressure.py
    ├── correlation.py
    └── logging.py
```
