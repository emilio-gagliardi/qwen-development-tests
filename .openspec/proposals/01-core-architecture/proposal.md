# Proposal 01: Core Architecture (Production-Scale)

## Overview
Establish the foundational architecture for a production-grade RAG pipeline capable of handling 1000+ requests/second with LiteLLM gateway, Haystack integration, and model routing capabilities. This proposal defines the structural backbone that supports all subsequent components with explicit focus on async safety, backpressure, observability, and fault tolerance.

## Problem Statement
Current RAG implementations lack proper architectural boundaries, making them difficult to maintain, test, and scale. We need a clean architecture that separates concerns while maintaining high performance through async operations, with explicit mechanisms for:
- **Race condition prevention** in singleton access under concurrent load
- **Backpressure management** to prevent resource exhaustion
- **Request tracing** across async boundaries via correlation IDs
- **Connection pooling** to prevent socket exhaustion
- **Explicit error propagation** without silent failures
- **Route timeouts** to prevent hanging requests

## Solution Approach
Implement a layered architecture with clear boundaries between domain logic, infrastructure, and presentation layers. Use dependency injection via registries to maintain loose coupling. Introduce production-scale patterns including async-safe singletons, semaphore-based backpressure, structured logging with correlation IDs, and connection pooling.

## Key Components
- **Domain Layer**: Core business logic, entities, and value objects with immutable guarantees
- **Application Layer**: Use cases and orchestration logic with Result pattern for error handling
- **Infrastructure Layer**: External service integrations (LiteLLM, Haystack, Langfuse) with connection pooling
- **Presentation Layer**: FastAPI endpoints with middleware for correlation IDs, timeouts, and backpressure
- **Configuration Singleton**: Async-safe, frozen configuration management with lazy initialization
- **Registry Pattern**: Service location for decoupled dependencies with factory support
- **Backpressure Controller**: Semaphore-based concurrency limiting with request queuing
- **Correlation ID Manager**: Context-propagated request tracing across async boundaries
- **Connection Pool Manager**: HTTP client pooling with keepalive and retry logic

## Technical Decisions
- **Python 3.11+** for async/await improvements and exception groups
- **Pydantic v2** for data validation, serialization, and frozen models
- **Dependency injection** through explicit registries with async factory support
- **Async-first design** throughout all layers with `asyncio.Lock` for shared state
- **Environment-based configuration** with validation and immutability guarantees
- **Backpressure strategy**: Token bucket algorithm with semaphore-based concurrency limits
- **Correlation ID propagation**: UUIDv4 per request, propagated via contextvars
- **Connection pooling**: `httpx.AsyncClient` with pool_limits and keepalive
- **Timeout strategy**: Cascading timeouts (route → service → client)
- **Error handling**: Result[T, E] pattern with explicit Success/Failure returns

## Success Criteria
- All components follow layered architecture with zero circular dependencies
- Configuration accessible via async-safe singleton with frozen state
- All external dependencies injected via registries with factory support
- 100% async-compatible codebase with no blocking calls
- Handles 1000+ req/sec with <100ms p99 latency overhead from architecture
- Backpressure activates at configurable threshold (default: 500 concurrent requests)
- All requests traceable via correlation IDs in logs and Langfuse
- Zero silent failures - all errors return explicit Failure[E] with context
- Connection pools prevent socket exhaustion under sustained load

## Backpressure Strategy
**Methodology**: Hybrid approach combining:
1. **Semaphore-based concurrency limiting** at route level (max 500 concurrent per endpoint)
2. **Token bucket algorithm** for rate limiting (configurable tokens/second)
3. **Bounded queues** for request buffering (max queue size: 1000)
4. **Circuit breaker pattern** for downstream services (LiteLLM, Haystack)
5. **Graceful degradation** when limits exceeded (return 503 with Retry-After header)

## Risks & Mitigations
- **Risk**: Over-engineering for simple use cases
  - **Mitigation**: Start minimal, add layers only when needed, profile before optimizing
- **Risk**: Performance overhead from abstraction
  - **Mitigation**: Profile critical paths, optimize bottlenecks, use benchmarks
- **Risk**: Race conditions in async singleton
  - **Mitigation**: Use `asyncio.Lock` for initialization, frozen config after init
- **Risk**: Resource exhaustion under load
  - **Mitigation**: Backpressure with semaphores, connection pooling, timeouts
- **Risk**: Lost correlation IDs in async contexts
  - **Mitigation**: Contextvars propagation, middleware injection, logging integration

## Dependencies
None - this is the foundation proposal

## Timeline
3 days for initial implementation with load testing validation

## Load Testing Requirements
- **Tool**: Locust or k6
- **Target**: 1000 req/sec sustained for 10 minutes
- **Metrics**: p50 < 50ms, p99 < 200ms, error rate < 0.1%
- **Validation**: No memory leaks, no socket exhaustion, backpressure activates correctly
