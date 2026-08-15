# Tasks

## Phase 1: Logger Setup
- [ ] Install `structlog` package
- [ ] Create `setup_logging()` function with environment detection
- [ ] Configure JSON formatter for production
- [ ] Configure console renderer for development
- [ ] Set up log level management

## Phase 2: Custom Processors
- [ ] Implement `CorrelationIDInjector` processor
- [ ] Implement `ServiceContextAdder` processor
- [ ] Implement `SensitiveDataFilter` processor
- [ ] Implement `DurationCalculator` processor
- [ ] Test processor chain ordering

## Phase 3: Context Managers
- [ ] Create `log_operation()` async context manager
- [ ] Create `correlation_id_context()` async context manager
- [ ] Test context propagation across async boundaries
- [ ] Verify cleanup on exceptions

## Phase 4: Integration
- [ ] Add logging middleware to FastAPI app
- [ ] Integrate with exception hierarchy (Proposal 02)
- [ ] Add structured logging to all use cases
- [ ] Test correlation ID flow end-to-end

## Phase 5: Testing & Validation
- [ ] Write unit tests for each processor
- [ ] Test sensitive data redaction patterns
- [ ] Verify JSON output schema compliance
- [ ] Load test logging performance impact
- [ ] Validate async context safety

## Acceptance Criteria
- All logs output valid JSON in production
- Correlation ID present in 100% of log entries
- Sensitive data redacted in all contexts
- Duration calculated for timed operations
- No performance degradation > 5%
- Test coverage > 90% for logging module

## Notes
- Keep processor chain efficient
- Avoid blocking I/O in processors
- Test with high concurrency scenarios
- Document log schema for observability team
