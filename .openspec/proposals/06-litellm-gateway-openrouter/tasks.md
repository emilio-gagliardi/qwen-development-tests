# Tasks

## Phase 1: LiteLLM Proxy Configuration
- [ ] Create `litellm_config.yaml` with OpenRouter models
- [ ] Configure FAST tier with `deepseek-chat` and `llama-3-8b`
- [ ] Configure BALANCED tier with `llama-3.3-70b` and `mixtral-8x22b`
- [ ] Configure ADVANCED tier with `gpt-4-turbo` and `claude-3-opus`
- [ ] Set appropriate timeouts per tier (15s, 30s, 60s)
- [ ] Configure rate limits (RPM/TPM) per model
- [ ] Enable Langfuse callbacks for tracing
- [ ] Enable cost tracking callbacks

## Phase 2: Gateway Client Implementation
- [ ] Implement `LiteLLMGatewayClient` class
- [ ] Add async HTTP session management with connection pooling
- [ ] Implement `generate()` method with proper error handling
- [ ] Implement `generate_stream()` for streaming responses
- [ ] Add timeout handling per model tier
- [ ] Implement retry logic with exponential backoff
- [ ] Add health check endpoint
- [ ] Implement model-to-tier mapping

## Phase 3: Error Handling & Resilience
- [ ] Handle connection errors gracefully
- [ ] Implement timeout exceptions
- [ ] Add retry logic for transient failures
- [ ] Map HTTP status codes to domain exceptions
- [ ] Log all errors with structured context

## Phase 4: Langfuse Integration
- [ ] Configure Langfuse environment variables
- [ ] Test trace collection in Langfuse dashboard
- [ ] Verify token usage tracking
- [ ] Verify cost calculation accuracy
- [ ] Test error trace capture

## Phase 5: Testing & Validation
- [ ] Write unit tests for gateway client
- [ ] Test with mock LiteLLM proxy
- [ ] Load test concurrent requests
- [ ] Validate timeout behavior
- [ ] Test streaming functionality
- [ ] Measure latency per tier
- [ ] Achieve >90% test coverage

## Acceptance Criteria
- All 6 models configured across 3 tiers
- Gateway client implements LLMGateway protocol
- Langfuse traces visible in dashboard
- Cost tracking accurate within 5%
- FAST tier latency < 1 second p95
- Proper error handling for all failure modes
- Test coverage >90%

## Notes
- Start with DeepSeek for all chat requests during development
- Monitor Langfuse dashboards for anomalies
- Adjust rate limits based on OpenRouter quotas
- Document model pricing for cost optimization
