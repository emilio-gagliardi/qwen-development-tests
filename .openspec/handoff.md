# OpenSpec Handoff Document

## Session Summary
**Date:** Current Session  
**Branch:** `dev` (with feature branch `feature/01-core-architecture` pending PR)  
**Status:** Proposal 01 implemented and pushed; adversarial review requested before proceeding

---

## What We Accomplished

### 1. Created Complete OpenSpec Proposal Structure
- **10 Proposals** properly structured in `.openspec/proposals/`:
  - Each proposal has: `proposal.md`, `design.md`, `tasks.md`, and `specs/` folder
  - Proper domain-grouped specification files in each `specs/` directory

### 2. Implemented Proposal 01 (Core Architecture)
- **Feature Branch:** `feature/01-core-architecture` (26 files created)
- **Key Components:**
  - Layered architecture (Domain, Application, Infrastructure, Presentation)
  - Pydantic-based data contracts with strict validation
  - Result pattern (`Result[T, E]`) for explicit error handling
  - Generic repository interfaces
  - Service layer with dependency injection
  - FastAPI application skeleton
  - Comprehensive exception hierarchy (21 exception classes)
  - Structured logging foundation
  - Test suite with unit and integration tests

### 3. Pushed to Remote
- Successfully pushed `feature/01-core-architecture` to GitHub
- PR ready for adversarial review: https://github.com/emilio-gagliardi/qwen-development-tests/pull/new/feature/01-core-architecture

---

## What We Learned

### Critical Gaps Identified During Review

#### 1. **Singleton Pattern Not Async-Safe** ❌
**Current State:** Uses basic `lru_cache()` and simple class-level caching  
**Problem:** Race conditions under high concurrency (1000+ req/sec)  
**Required Fix:**
```python
# Need asyncio.Lock for thread-safe async initialization
class AsyncSingletonMeta(type):
    _instances: dict = {}
    _locks: dict = {}
    
    @classmethod
    async def get_instance(cls) -> "AppSettings":
        if cls not in cls._instances:
            async with cls._locks.get(cls, asyncio.Lock()):
                if cls not in cls._instances:
                    cls._instances[cls] = cls()
        return cls._instances[cls]
```

#### 2. **Missing Backpressure Mechanisms** ❌
**Current State:** No concurrency limits configured  
**Problem:** Unbounded requests will exhaust LiteLLM proxy and memory  
**Required Fix:**
```python
# Add to Settings
max_concurrent_llm_calls: int = 50
max_concurrent_db_ops: int = 100
request_timeout_seconds: int = 30

# Use asyncio.Semaphore in services
self._llm_semaphore = asyncio.Semaphore(settings.max_concurrent_llm_calls)
```

#### 3. **Configuration Not Frozen** ❌
**Current State:** Settings can be mutated at runtime  
**Problem:** Race conditions when config changes during request processing  
**Required Fix:**
```python
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True)  # Immutable after load
```

#### 4. **FastAPI Async Implementation Incomplete** ❌
**Current Issues:**
- No middleware for correlation IDs
- No timeout enforcement at route level
- Blocking calls potentially in async paths
- No connection pooling configuration
- Missing graceful shutdown handlers

**Required Patterns:**
```python
# Middleware for correlation IDs
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

# Timeout enforcement
from asyncio import wait_for
async def query_with_timeout(query: str, timeout: float = 30.0):
    try:
        return await wait_for(rag_pipeline.query(query), timeout=timeout)
    except TimeoutError:
        raise PipelineTimeoutError(f"Query exceeded {timeout}s limit")
```

#### 5. **No Connection Pooling or Resource Management** ❌
**Current State:** HTTP clients created per-request or globally without limits  
**Problem:** Socket exhaustion, memory leaks under load  
**Required Fix:**
```python
# Use httpx.AsyncClient with limits
self.http_client = httpx.AsyncClient(
    base_url=settings.litellm_proxy_url,
    timeout=httpx.Timeout(30.0),
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)
)
```

#### 6. **Error Handling Doesn't Use Result Pattern Consistently** ❌
**Current State:** Mix of exceptions and None returns  
**Problem:** Silent failures, unclear error boundaries  
**Required Fix:** All service methods must return `Result[T, E]`

#### 7. **Logging Missing Correlation Context** ❌
**Current State:** Basic JSON logging  
**Problem:** Cannot trace requests across async boundaries  
**Required Fix:**
```python
context_var = contextvars.ContextVar("correlation_id", default=None)

class CorrelationFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = context_var.get()
        return True
```

---

## Architecture Readiness for Scale (1000+ req/sec)

### Current Score: 3/10 ❌

| Component | Status | Gap |
|-----------|--------|-----|
| Configuration Singleton | ⚠️ Partial | Not async-safe, mutable |
| Concurrency Control | ❌ Missing | No semaphores, rate limiting |
| Connection Pooling | ❌ Missing | No HTTP client limits |
| Timeout Enforcement | ❌ Missing | No route-level timeouts |
| Correlation IDs | ❌ Missing | Cannot trace async requests |
| Graceful Shutdown | ⚠️ Partial | Basic handler exists, no drain logic |
| Backpressure | ❌ Missing | No queue limits |
| Circuit Breakers | ❌ Missing | No failure isolation |
| Health Checks | ✅ Present | Basic endpoint exists |
| Metrics/Observability | ⚠️ Partial | Langfuse configured but not tested |

---

## Required Fixes Before Proceeding to Proposal 02

### Priority 1: Foundation Stability
1. **Implement Async-Safe Singleton** with double-check locking
2. **Add Concurrency Limits** (semaphores for LLM calls, DB ops)
3. **Freeze Configuration** to prevent runtime mutation
4. **Add Correlation ID Middleware** for request tracing
5. **Configure HTTP Client Pools** with proper limits

### Priority 2: Resilience
6. **Implement Route-Level Timeouts** using `asyncio.wait_for`
7. **Add Graceful Shutdown** with connection draining
8. **Enforce Result Pattern** across all service methods
9. **Add Structured Logging** with correlation context

### Priority 3: Observability
10. **Test Langfuse Integration** end-to-end
11. **Add Prometheus Metrics** for request rates, latencies, errors
12. **Implement Distributed Tracing** headers propagation

---

## Next Steps for Continuation

### Immediate Actions Required
1. **DO NOT merge `feature/01-core-architecture` yet** - needs fixes above
2. **Create new feature branch** from `dev`: `feature/01-core-architecture-v2`
3. **Implement all Priority 1 fixes** listed above
4. **Run load test** with `locust` or `k6` to verify 1000 req/sec capability
5. **Conduct adversarial review** focusing on:
   - Async safety under concurrent load
   - Memory leaks over extended runtime
   - Error propagation completeness
   - Timeout enforcement effectiveness
6. **Only then create PR** to `dev` branch

### Subsequent Proposals (After 01 is Stable)
- **Proposal 02:** Exception Hierarchy refinement (ensure all exceptions have correlation IDs)
- **Proposal 03:** Structured Logging (add correlation context, async-safe handlers)
- **Proposal 04:** Anti-Corruption Layer (implement adapters with proper async patterns)
- **Proposal 05:** Async Concurrency Patterns (formalize semaphore usage, circuit breakers)
- **Proposal 06:** LiteLLM Gateway + OpenRouter (add connection pooling, retry logic)
- **Proposal 07:** Intent Classifier (ensure timeout protection, backpressure)
- **Proposal 08:** Model Router (add circuit breakers for model tiers)
- **Proposal 09:** Haystack Rerank Pipeline (async batch processing, memory limits)
- **Proposal 10:** Docker Deployment (resource limits, health checks, scaling config)

---

## Code Quality Checklist for Adversarial Review

### Async Safety
- [ ] All singletons use `asyncio.Lock` for initialization
- [ ] No blocking I/O in async paths (use `aiofiles`, `httpx.AsyncClient`)
- [ ] All shared state protected by locks or semaphores
- [ ] Context variables used for request-scoped data (correlation IDs)
- [ ] No mutable global state

### Concurrency & Scaling
- [ ] Semaphores limit concurrent LLM calls
- [ ] Database operations bounded by semaphore
- [ ] HTTP clients use connection pooling with limits
- [ ] Timeouts enforced at every external call boundary
- [ ] Backpressure mechanism prevents queue overflow

### Error Handling
- [ ] Result pattern used consistently (no bare exceptions)
- [ ] All errors include correlation ID
- [ ] Exceptions have proper hierarchy with context
- [ ] No silent failures (explicit Failure returns)
- [ ] Graceful degradation on partial failures

### Configuration
- [ ] Settings frozen after initialization
- [ ] Validation occurs at startup (fail fast)
- [ ] Secrets loaded from environment only
- [ ] No hardcoded values in business logic
- [ ] Configuration reloadable only in dev mode

### Observability
- [ ] Correlation ID propagated through all layers
- [ ] Structured logs include timing, correlation, context
- [ ] Langfuse traces include full request lifecycle
- [ ] Metrics exposed for Prometheus scraping
- [ ] Health checks verify dependencies

### Resource Management
- [ ] All async clients properly closed on shutdown
- [ ] Connection pools drained gracefully
- [ ] No resource leaks in error paths
- [ ] Memory usage bounded under load
- [ ] File handles properly managed with context managers

---

## Technical Debt Log

| Issue | Severity | Impact | Fix Required In |
|-------|----------|--------|-----------------|
| Non-async-safe singleton | Critical | Race conditions at scale | Proposal 01 v2 |
| No concurrency limits | Critical | Resource exhaustion | Proposal 01 v2 |
| Mutable configuration | High | Data corruption risk | Proposal 01 v2 |
| Missing correlation IDs | High | Debugging impossible | Proposal 01 v2 |
| No connection pooling | High | Socket exhaustion | Proposal 01 v2 |
| Inconsistent Result pattern | Medium | Silent failures | Proposal 01 v2 |
| No route timeouts | Medium | Hanging requests | Proposal 01 v2 |
| Incomplete shutdown logic | Medium | Data loss on restart | Proposal 01 v2 |

---

## Repository State

### Branches
- `main`: Production-ready code (empty/minimal)
- `dev`: Integration branch (contains initial scaffolding)
- `feature/01-core-architecture`: **DO NOT MERGE** - needs fixes
- `feature/01-core-architecture-v2`: To be created with fixes

### Key Files to Modify
1. `/workspace/app/core/config.py` - Rewrite with async singleton
2. `/workspace/app/main.py` - Add middleware, timeouts, shutdown logic
3. `/workspace/app/gateway.py` - Add connection pooling, semaphores
4. `/workspace/app/infrastructure/logging/logger.py` - Add correlation context
5. `/workspace/app/domain/services/interfaces.py` - Enforce Result pattern

---

## Lessons for Future Sessions

1. **Always start with load testing requirements** - Design for 1000 req/sec from day 1
2. **Async safety is non-trivial** - Simple patterns fail under concurrency
3. **Backpressure must be explicit** - Semaphores, queues, timeouts everywhere
4. **Correlation IDs are essential** - Cannot debug distributed async systems without them
5. **Frozen configuration prevents entire classes of bugs** - Make immutability default
6. **Result pattern requires discipline** - Easy to slip back into exceptions
7. **Adversarial review should happen BEFORE implementation** - Catch gaps in design phase

---

## Contact Points for Questions

- **Architecture Decisions:** See `.openspec/proposals/01-core-architecture/specs/`
- **Async Patterns:** See `.openspec/proposals/05-async-concurrency-patterns/specs/`
- **Error Handling:** See `app/domain/exceptions/` and Result pattern docs
- **Testing Strategy:** See `tests/` directory and pytest fixtures

---

*This handoff document captures the current state, critical gaps, and required fixes before proceeding. The next agent/session MUST address Priority 1 items before implementing Proposal 02.*
