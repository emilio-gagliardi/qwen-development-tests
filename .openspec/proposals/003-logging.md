# Proposal: Structured Logging System

## Overview
Implement comprehensive structured logging with JSON output, correlation IDs, and integration with Langfuse for complete observability.

## Requirements

### Logging Configuration
1. JSON-formatted logs for machine parsing
2. Correlation ID propagation across all services
3. Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
4. Sensitive data masking (API keys, tokens)
5. Async-safe logging handlers

### Log Schema
```json
{
  "timestamp": "2025-01-15T10:30:00.123Z",
  "level": "INFO",
  "service": "rag-api",
  "correlation_id": "uuid-v4",
  "request_id": "uuid-v4",
  "event": "request_received",
  "message": "RAG query received",
  "context": {
    "query_length": 45,
    "intent": "question",
    "model_tier": "balanced"
  },
  "duration_ms": 234,
  "user_id": null
}
```

### Components to Instrument
1. **FastAPI Middleware**
   - Request/response logging
   - Latency tracking
   - Status code capture
   - Client IP (anonymized)

2. **Intent Classifier**
   - Classification input/output
   - Confidence scores
   - Model used
   - Fallback triggers

3. **Model Router**
   - Routing decisions
   - Tier selection rationale
   - Confidence adjustments

4. **LiteLLM Gateway**
   - Request to proxy
   - Response from proxy
   - Token counts (input/output)
   - Costs (from Langfuse)
   - Retry attempts

5. **Haystack Pipeline**
   - Document retrieval count
   - Reranker scores
   - Generation prompts (truncated)
   - Final response length

6. **Error Handling**
   - Exception details
   - Stack traces (DEBUG only)
   - Recovery actions

### Integration Points
- **Langfuse**: Automatic trace/span creation via LiteLLM callbacks
- **Correlation ID**: Generated per request, passed to all downstream calls
- **Log Aggregation**: Compatible with ELK, Loki, or cloud providers

### Implementation Details
```python
# Logger factory
def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name).bind(
        service="rag-api",
        environment=settings.ENVIRONMENT
    )

# Context manager for timing
@asynccontextmanager
async def log_operation(logger, operation: str, **context):
    start = time.perf_counter()
    try:
        yield
        duration = (time.perf_counter() - start) * 1000
        logger.info(f"{operation}_completed", duration_ms=duration, **context)
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        logger.error(f"{operation}_failed", error=str(e), duration_ms=duration, **context)
        raise
```

### Environment Variables
- `LOG_LEVEL`: Default INFO, DEBUG for development
- `LOG_FORMAT`: json (default) or console for local dev
- `ENABLE_SENSITIVE_LOG_MASKING`: true (default)
- `CORRELATION_ID_HEADER`: X-Correlation-ID

## Acceptance Criteria
1. All logs output in JSON format in production
2. Correlation ID present in every log entry
3. No API keys or tokens appear in logs
4. Langfuse traces show complete request flow
5. Performance logs include duration metrics
6. Error logs include full exception context
7. Log level configurable via environment variable
