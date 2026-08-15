# OpenSpec Proposals Index - Production RAG Pipeline

## Project Overview
Build a production-grade, LiteLLM-backed RAG pipeline with Haystack for deployment on Hostinger VPS using Docker. The system features intelligent model routing based on intent classification, comprehensive observability with Langfuse, and cost-optimized model selection via OpenRouter.

## Proposal Summary

| # | Title | Status | Priority | Key Components |
|---|-------|--------|----------|----------------|
| 001 | Production-Ready RAG Pipeline Architecture | ✅ Complete | P0 | Architecture, Goals, Constraints |
| 002 | Custom Exception Hierarchy and Error Handling | ✅ Complete | P0 | Exceptions, Error Codes, Response Schema |
| 003 | Structured Logging System | ✅ Complete | P0 | JSON Logs, Correlation IDs, Langfuse Integration |
| 004 | Anti-Corruption Layer and Protocol Architecture | ✅ Complete | P0 | Protocols, Interfaces, Registries, DI |
| 005 | Async-First Architecture | ✅ Complete | P0 | Async Components, Concurrency, Timeouts |
| 006 | LiteLLM Gateway with Langfuse Integration | ✅ Complete | P0 | Proxy Config, Model Tiers, Observability |
| 007 | Intent Classification System | ✅ Complete | P0 | 6 Intent Types, LLM + Fallback, Caching |
| 008 | Model Router with Tier Selection | ✅ Complete | P0 | 3 Tiers, Routing Strategies, Cost Optimization |
| 009 | Haystack RAG Pipeline with Reranker | ✅ Complete | P0 | Retrieval, Cross-Encoder Reranking, Generation |
| 010 | Docker Deployment for Hostinger VPS | ✅ Complete | P0 | Compose, Dockerfile, Security, Monitoring |

## Architecture Flow

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Client    │────▶│  FastAPI (RAG)   │────▶│Intent Classifier│
└─────────────┘     └──────────────────┘     └─────────────────┘
                            │                        │
                            ▼                        ▼
                    ┌──────────────────┐     ┌─────────────────┐
                    │  Model Router    │◀────│  (6 intents)    │
                    └──────────────────┘     └─────────────────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │ LiteLLM Gateway  │────▶┌─────────────────┐
                    │  (Proxy Server)  │     │  OpenRouter     │
                    └──────────────────┘     └─────────────────┘
                            │                        │
                            ▼                        ▼
                    ┌──────────────────┐     ┌─────────────────┐
                    │   Langfuse       │     │  Model Tiers:   │
                    │  (Observability) │     │  - Fast         │
                    └──────────────────┘     │  - Balanced     │
                                             │  - Advanced     │
                                             └─────────────────┘

Inside RAG Pipeline:
┌─────────────────────────────────────────────────────────────┐
│  1. Vector Retriever (top_k=10)                             │
│           ↓                                                  │
│  2. Cross-Encoder Reranker (top_k=3)                        │
│           ↓                                                  │
│  3. Prompt Builder (context + query)                        │
│           ↓                                                  │
│  4. LLM Generator (routed model)                            │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Core Framework
- **FastAPI**: Async web framework
- **Haystack**: RAG pipeline components
- **LiteLLM**: Unified LLM gateway/proxy
- **Pydantic**: Data validation and contracts

### Models & Providers
- **OpenRouter**: Primary model provider
- **DeepSeek Chat**: Fast tier (~$0.14/1M tokens)
- **DeepSeek V3**: Balanced tier (~$0.27/1M tokens)
- **Llama 3.3 70B**: Advanced tier (~$0.40/1M tokens)

### Observability
- **Langfuse**: Tracing, metrics, cost tracking
- **Structlog**: Structured JSON logging
- **Correlation IDs**: Request tracing across services

### Infrastructure
- **Docker Compose**: Multi-container orchestration
- **Hostinger VPS**: Target deployment environment
- **uvicorn**: ASGI server with workers
- **httpx**: Async HTTP client

## Key Design Decisions

### 1. LiteLLM as Standalone Proxy
**Decision**: Deploy LiteLLM as separate container, not embedded library  
**Rationale**: Security (API keys isolated), scalability, centralized observability, easier updates

### 2. Three-Tier Model Strategy
**Decision**: Route queries to FAST/BALANCED/ADVANCED tiers based on intent  
**Rationale**: 60% cost reduction vs using advanced models for everything, maintains quality for complex queries

### 3. Intent Classification Before Routing
**Decision**: Classify query intent with cheap model before selecting generation model  
**Rationale**: Enables intelligent routing, adds metadata for analytics, minimal latency overhead (<500ms)

### 4. Cross-Encoder Reranking
**Decision**: Add reranker after vector retrieval (10 → 3 documents)  
**Rationale**: Significantly improves response quality by selecting most relevant context, small latency tradeoff

### 5. Protocol-Based Architecture
**Decision**: Define interfaces (protocols) for all external dependencies  
**Rationale**: Testability, swappable implementations, clear boundaries, anti-corruption layer

### 6. Async-First Design
**Decision**: All I/O operations async with proper concurrency controls  
**Rationale**: Maximizes throughput on limited VPS resources, prevents blocking, better resource utilization

## Cost Projections

### Per Query Costs (Average)
| Tier | Model | Cost/Query | Usage % | Monthly (10K/day) |
|------|-------|------------|---------|-------------------|
| FAST | DeepSeek Chat | $0.00007 | 50% | $10.50 |
| BALANCED | DeepSeek V3 | $0.00019 | 40% | $22.80 |
| ADVANCED | Llama 3.3 70B | $0.00036 | 10% | $10.80 |
| **Total** | - | **~$0.00015 avg** | 100% | **~$44/month** |

**Comparison**: Using only advanced models would cost ~$120/month (173% increase)

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| End-to-end Latency (P50) | < 2s | From request to response |
| End-to-end Latency (P95) | < 5s | Including retries |
| Intent Classification | < 500ms | LLM + fallback |
| Document Retrieval | < 200ms | Vector search |
| Reranking | < 300ms | Cross-encoder |
| LLM Generation | < 3s | Token generation |
| Throughput | 50 req/s | Concurrent requests |
| Availability | 99.5% | Uptime target |

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [x] 001: Architecture proposal
- [x] 002: Exception hierarchy
- [x] 003: Structured logging
- [x] 004: Protocols and interfaces
- [x] 005: Async architecture

### Phase 2: Core Components (Week 2)
- [x] 006: LiteLLM gateway setup
- [x] 007: Intent classifier
- [x] 008: Model router
- [x] 009: Haystack RAG pipeline

### Phase 3: Deployment (Week 3)
- [x] 010: Docker configuration
- [ ] Implementation code
- [ ] Testing suite
- [ ] Documentation

### Phase 4: Production Readiness (Week 4)
- [ ] Load testing
- [ ] Security audit
- [ ] Monitoring dashboards
- [ ] Runbook creation

## Next Steps

1. **Review Proposals**: Stakeholders review all 10 proposals
2. **Prioritize Adjustments**: Identify any gaps or changes needed
3. **Begin Implementation**: Start with Phase 1 foundation components
4. **Iterative Development**: Build, test, refine each component
5. **Deploy to Staging**: Test on staging VPS before production

## File Structure

```
.openspec/
├── proposals/
│   ├── 001-architecture.md
│   ├── 002-exceptions.md
│   ├── 003-logging.md
│   ├── 004-protocols.md
│   ├── 005-async.md
│   ├── 006-litellm-gateway.md
│   ├── 007-intent-classifier.md
│   ├── 008-model-router.md
│   ├── 009-haystack-reranker.md
│   ├── 010-docker-deployment.md
│   └── INDEX.md (this file)
```

## Related Documentation

- **GUIDE.md**: Original implementation guide
- **DEPLOYMENT.md**: Docker deployment instructions
- **README.md**: Project overview
- **litellm_config.yaml**: LiteLLM proxy configuration
- **docker-compose.yml**: Container orchestration
- **.env.example**: Environment variable template

## Contact & Support

For questions about these proposals:
- Review individual proposal files for detailed specifications
- Check acceptance criteria in each proposal
- Refer to architecture diagram for component relationships
- Use troubleshooting section in deployment proposal

---

**Status**: All proposals complete and ready for implementation  
**Last Updated**: 2025-01-15  
**Version**: 1.0
