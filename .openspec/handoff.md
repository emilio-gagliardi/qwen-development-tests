# OpenSpec Session Handoff - Proposal 01 Core Architecture

## Executive Summary
This session upscaled OpenSpec Proposal 01 from a basic architecture to a production-scale design capable of handling 1000+ requests/second. The proposal has been comprehensively updated with async-safe patterns, backpressure mechanisms, correlation ID tracking, connection pooling, and explicit error handling via the Result pattern.

## What We Accomplished

### 1. Proposal Documentation Upscaled
- **proposal.md**: Enhanced with production-scale requirements including:
  - Explicit problem statements for race conditions, backpressure, correlation IDs, connection pooling, silent failures, and route timeouts
  - Hybrid backpressure strategy (semaphore + token bucket + circuit breaker)
  - Load testing requirements (1000 req/sec, p99 < 200ms)
  - Success criteria quantified with metrics

- **specs/design.md**: Completely rewritten with senior engineer-quality specifications:
  - Async-safe ConfigSingleton with `asyncio.Lock` and frozen state
  - BackpressureController with hybrid strategies
  - CorrelationIdManager using contextvars for async propagation
  - ConnectionPoolManager with httpx limits and keepalive
  - Async-safe ServiceRegistry with factory support
  - All code examples include comprehensive docstrings following Google style

### 2. Key Architectural Decisions Documented

#### Backpressure Strategy
We selected a **hybrid approach** combining:
1. **Semaphore-based concurrency limiting** (500 concurrent requests per endpoint)
2. **Token bucket algorithm** (1000 tokens/second refill rate)
3. **Bounded queues** (1000 max queue size before rejection)
4. **Circuit breaker pattern** (trips after 10 failures, 30s timeout)
5. **Graceful degradation** (503 responses with Retry-After header)

**Rationale**: Single strategies have weaknesses - semaphores don't handle bursts, token buckets don't limit concurrency, queues can grow unbounded. The hybrid approach provides defense in depth.

#### Correlation ID Propagation
- **Mechanism**: Python `contextvars.ContextVar` for async-safe context propagation
- **Format**: UUIDv4 as string value object
- **Lifecycle**: Generated at middleware layer, propagated through all async boundaries, included in all logs and Langfuse events
- **Fallback**: Auto-generates if not provided by client

#### Connection Pooling
- **Library**: `httpx.AsyncClient` (native async, better than aiohttp for this use case)
- **Configuration**: 
  - max_connections: 100
  - max_keepalive_connections: 50
  - keepalive_expiry: 30 seconds
  - timeout: 30 seconds (cascading: route → service → client)

#### Configuration Singleton
- **Pattern**: Async-safe lazy initialization with `asyncio.Lock`
- **Immutability**: Frozen via pydantic-settings after initialization
- **Thread Safety**: Double-checked locking pattern prevents race conditions
- **Error Handling**: RuntimeError if accessed before initialization

#### Error Handling
- **Pattern**: Result[T, E] = Union[Success[T], Failure[E]]
- **No Silent Failures**: Methods never return None for errors
- **Error Context**: Failure includes error code, message, timestamp, correlation_id, and optional cause
- **Exception Hierarchy**: Structured exception classes mapped to error codes

## What We Learned

### Technical Learnings

1. **Async Singletons Are Hard**: Standard singleton patterns fail under concurrent async load. Must use `asyncio.Lock` for initialization and avoid mutable state after init.

2. **Contextvars Are Essential for Correlation**: Thread-local storage doesn't work in async contexts. `contextvars.ContextVar` is the only safe way to propagate request-scoped data across await points.

3. **Backpressure Requires Multiple Layers**: A single mechanism (e.g., just semaphores) creates false confidence. Need layered approach: rate limiting → concurrency limiting → queuing → circuit breaking.

4. **Connection Pools Prevent Cascading Failures**: Without pooling, socket exhaustion occurs quickly under load, causing downstream failures that cascade through the system.

5. **Result Pattern Improves Type Safety**: Explicit Success/Failure returns force callers to handle errors, eliminating entire classes of bugs from unhandled exceptions or None checks.

### Process Learnings

1. **OpenSpec Structure Works**: Separating proposal.md (what/why), design.md (how), tasks.md (action items), and specs/ (domain details) creates clear separation of concerns.

2. **Adversarial Review Before Implementation**: Identifying gaps in the proposal phase prevents costly refactors after code is written.

3. **Load Testing Requirements Must Be Explicit**: "Handles high load" is meaningless without specific metrics (req/sec, latency percentiles, error rates).

## Current State

### Files Modified
```
.openspec/proposals/01-core-architecture/
├── proposal.md          ✅ Updated with production-scale requirements
├── tasks.md             ⏳ Needs update with new tasks
└── specs/
    └── design.md        ✅ Completely rewritten with async-safe patterns
```

### Branch Status
- **Current Branch**: `feature/01-core-architecture-v2`
- **Base Branch**: `dev`
- **Status**: Ready for implementation (design complete)
- **Commits**: Design documentation updated, code implementation pending

## Next Steps for Continuation

### Immediate Actions (Priority 1)

1. **Update tasks.md** with new implementation tasks:
   - Create async-safe ConfigSingleton
   - Implement BackpressureController
   - Build CorrelationIdManager with middleware integration
   - Create ConnectionPoolManager
   - Update ServiceRegistry for async safety
   - Implement Result pattern types
   - Add structured logging with correlation IDs

2. **Implement Core Infrastructure** (in order):
   ```bash
   # Create directory structure
   mkdir -p app/{domain/{entities,value_objects,protocols},application/{use_cases,dtos},infrastructure/{repositories,external,pooling},presentation/{controllers,middleware},core}
   
   # Implement in priority order:
   1. app/core/result.py           # Result pattern types
   2. app/core/correlation.py      # CorrelationIdManager
   3. app/core/config.py           # Async-safe ConfigSingleton
   4. app/core/backpressure.py     # BackpressureController
   5. app/core/pooling.py          # ConnectionPoolManager
   6. app/core/registry.py         # Async-safe ServiceRegistry
   7. app/core/logging.py          # Structured JSON logging
   8. app/domain/protocols/        # Interface definitions
   9. app/presentation/middleware/ # Correlation ID, timeout, backpressure middleware
   ```

3. **Write Unit Tests** for each component:
   - Test async safety under concurrent load (use asyncio.gather with 1000 concurrent calls)
   - Test backpressure activation thresholds
   - Test correlation ID propagation across async boundaries
   - Test connection pool exhaustion and recovery

4. **Integration Test** with load testing:
   - Use locust or k6 to verify 1000 req/sec
   - Measure p50, p95, p99 latency
   - Verify backpressure activates correctly
   - Check for memory leaks over 10-minute sustained load

### Medium Priority (Priority 2)

5. **Implement Domain Layer**:
   - Entities with frozen=True
   - Value objects with validation
   - Protocol definitions for repositories and services

6. **Implement Application Layer**:
   - Use cases with Result pattern returns
   - DTOs for inter-layer communication
   - Validators with explicit error types

### Lower Priority (Priority 3)

7. **Implement Infrastructure Layer**:
   - Repository implementations
   - External service clients (LiteLLM gateway stub)
   - Message bus with backpressure awareness

8. **Implement Presentation Layer**:
   - FastAPI application factory
   - Controllers with proper error handling
   - Schemas with strict validation

## Code Quality Standards

All implementation must follow these standards:

### Docstring Format (Google Style)
```python
def method_name(param1: str, param2: int) -> Result[str, ErrorDetail]:
    """
    One-line summary of what the method does.
    
    Extended description if needed, explaining why and any side effects.
    
    Args:
        param1: Description of param1 including valid ranges/constraints
        param2: Description of param2 including units if applicable
    
    Returns:
        Success containing result description, or Failure with error context
    
    Raises:
        SpecificExceptionType: When and why this exception is raised
    
    Example:
        >>> result = await method_name("value", 42)
        >>> if isinstance(result, Success):
        ...     print(result.value)
    """
```

### Type Hints
- Full type annotations on all parameters and return values
- Use `Optional[T]` only for truly optional values (prefer Result pattern)
- Use `Union[Success[T], Failure[E]]` or custom `Result[T, E]` type alias
- Generic type parameters for reusable components

### Async Best Practices
- All I/O operations must be async (no blocking calls)
- Use `asyncio.Lock` for shared mutable state
- Propagate contextvars across all await points
- Implement proper cancellation handling with `try/finally`
- Use `asyncio.wait_for()` for timeout enforcement

### Error Handling
- Never raise exceptions for expected failures - return Failure[E]
- Include correlation_id in all error contexts
- Log errors with full stack traces at ERROR level
- Return actionable error messages to API consumers

## Testing Strategy

### Unit Tests
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_backpressure_activates_under_load():
    """Verify backpressure activates when concurrent requests exceed threshold."""
    config = BackpressureConfig(max_concurrent_requests=10)
    controller = BackpressureController(config)
    await controller.start()
    
    # Attempt 100 concurrent acquisitions
    tasks = [controller.acquire() for _ in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify some were rejected
    rejections = sum(1 for r in results if isinstance(r, RateLimitExceededError))
    assert rejections > 0, "Backpressure should reject excess requests"
    
    await controller.stop()
```

### Load Tests
```python
# locustfile.py
from locust import HttpUser, task, between

class RAGUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    @task
    def query(self):
        self.client.post("/rag/query", json={
            "query": "test question",
            "correlation_id": str(uuid.uuid4())
        })
```

Run with: `locust -f locustfile.py --host=http://localhost:8000 --users 1000 --spawn-rate 100`

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Over-engineering for current scale | Medium | Start with minimal viable implementation, add complexity only when load tests prove need |
| Performance overhead from locks | Low | Profile critical paths, optimize lock granularity if p99 exceeds targets |
| Contextvar leakage between requests | Medium | Clear contextvars in middleware finally blocks, add tests for isolation |
| Connection pool starvation | High | Monitor pool utilization, implement circuit breakers, add alerting |
| Incorrect backpressure thresholds | Medium | Start conservative, tune based on load test results and production metrics |

## Dependencies for Next Proposals

Proposal 01 must be fully implemented and tested before proceeding to:

- **Proposal 02 (Exception Hierarchy)**: Depends on Result pattern from Proposal 01
- **Proposal 03 (Structured Logging)**: Depends on CorrelationIdManager from Proposal 01
- **Proposal 06 (LiteLLM Gateway)**: Depends on ConnectionPoolManager from Proposal 01
- **Proposal 10 (Docker Deployment)**: Depends on all infrastructure components

Proposals 04 (Anti-Corruption Layer) and 05 (Async Patterns) can proceed in parallel once core infrastructure (config, registry, result types) is complete.

## Success Metrics for This Proposal

Implementation is complete when:

- [ ] All components pass unit tests with >90% coverage
- [ ] Load test achieves 1000 req/sec sustained for 10 minutes
- [ ] p50 latency < 50ms, p99 latency < 200ms (architecture overhead only)
- [ ] Error rate < 0.1% under normal load
- [ ] Backpressure activates gracefully at configured thresholds
- [ ] Zero memory leaks over extended load testing
- [ ] All correlation IDs traceable end-to-end in logs
- [ ] No blocking calls detected via profiling
- [ ] All docstrings follow Google style with examples
- [ ] Adversarial code review completed with zero critical findings

## Contact Points

For questions about this implementation:
- **Architecture decisions**: See proposal.md and design.md
- **Backpressure tuning**: Adjust BackpressureConfig defaults based on load test results
- **Correlation ID format**: UUIDv4, immutable, propagated via contextvars
- **Error handling pattern**: Result[T, E] with explicit Success/Failure

---

*Generated: End of Session 1 | Next Session: Implement core infrastructure components*
