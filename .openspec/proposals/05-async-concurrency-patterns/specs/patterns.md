# Async Concurrency Patterns Design

## Timeout Wrapper Pattern

```python
from functools import wraps
from typing import Callable, Any, Optional
import asyncio
from app.core.exceptions import InfrastructureException

class TimeoutError(InfrastructureException):
    def __init__(self, operation: str, timeout: int):
        super().__init__(
            f"Operation {operation} timed out after {timeout}s",
            "INFRA_009",
            {"operation": operation, "timeout": timeout}
        )

def with_timeout(timeout_seconds: int, operation_name: str = "unnamed"):
    """Decorator to add timeout to async functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(operation_name, timeout_seconds)
        return wrapper
    return decorator

# Usage
@with_timeout(30, "llm_generation")
async def generate_with_timeout(prompt: str, model: str):
    return await gateway.generate(prompt, model)
```

## Semaphore Rate Limiting

```python
import asyncio
from contextlib import asynccontextmanager

class RateLimiter:
    """Async rate limiter using semaphore."""
    
    def __init__(self, max_concurrent: int):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._current = 0
    
    @asynccontextmanager
    async def acquire(self):
        async with self._semaphore:
            self._current += 1
            try:
                yield
            finally:
                self._current -= 1
    
    @property
    def current_load(self) -> int:
        return self._current

# Global rate limiters
LLM_RATE_LIMITER = RateLimiter(max_concurrent=10)
VECTOR_SEARCH_LIMITER = RateLimiter(max_concurrent=5)

# Usage
async def generate_with_rate_limit(prompt: str, model: str):
    async with LLM_RATE_LIMITER.acquire():
        return await gateway.generate(prompt, model)
```

## Connection Pool Management

```python
import aiohttp
from contextlib import asynccontextmanager

class ConnectionPoolManager:
    """Manage HTTP connection pools."""
    
    def __init__(self):
        self._sessions: dict[str, aiohttp.ClientSession] = {}
    
    def get_session(
        self,
        name: str,
        limit: int = 100,
        limit_per_host: int = 30,
        timeout: int = 30
    ) -> aiohttp.ClientSession:
        if name not in self._sessions or self._sessions[name].closed:
            connector = aiohttp.TCPConnector(
                limit=limit,
                limit_per_host=limit_per_host,
                ttl_dns_cache=300,
            )
            self._sessions[name] = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=timeout)
            )
        return self._sessions[name]
    
    async def close_all(self):
        for session in self._sessions.values():
            if not session.closed:
                await session.close()
        self._sessions.clear()

pool_manager = ConnectionPoolManager()
```

## Structured Concurrency with TaskGroup

```python
import asyncio
from typing import List, Any

async def process_batch(items: List[Any], processor: callable) -> List[Any]:
    """Process items concurrently with structured concurrency."""
    results = []
    
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(processor(item)) for item in items]
    
    results = [task.result() for task in tasks]
    return results

# Usage with error handling
async def classify_queries_batch(queries: List[str]) -> List[IntentClassification]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(classifier.classify(q)) for q in queries]
    
    return [task.result() for task in tasks]
```

## Circuit Breaker Pattern

```python
import asyncio
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._failures = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = CircuitState.CLOSED
        self._half_open_calls = 0
    
    async def call(self, func: callable, *args, **kwargs) -> Any:
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
            else:
                raise InfrastructureException(
                    "Circuit breaker is OPEN",
                    "INFRA_010",
                    {"service": func.__name__}
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self._failures = 0
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
    
    def _on_failure(self):
        self._failures += 1
        self._last_failure_time = datetime.utcnow()
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        if not self._last_failure_time:
            return True
        return datetime.utcnow() > (
            self._last_failure_time + timedelta(seconds=self.recovery_timeout)
        )

# Usage
gateway_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

async def safe_generate(prompt: str, model: str):
    return await gateway_breaker.call(gateway.generate, prompt, model)
```

## Async Context Manager for Operations

```python
from contextlib import asynccontextmanager
from datetime import datetime
import time

@asynccontextmanager
async def timed_operation(operation_name: str):
    """Context manager for timing operations."""
    start_time = time.time()
    try:
        yield {"start_time": start_time, "operation": operation_name}
    finally:
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"{operation_name} completed",
            duration_ms=round(duration_ms, 2)
        )

# Usage
async def process_query(query: str):
    async with timed_operation("intent_classification") as ctx:
        intent = await classifier.classify(query)
    
    async with timed_operation("model_routing") as ctx:
        decision = await router.route(intent.intent_type, intent.confidence)
```
