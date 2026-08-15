# Proposal: LiteLLM Gateway with Langfuse Integration

## Overview
Configure and deploy LiteLLM proxy as a standalone service with comprehensive Langfuse integration for observability, cost tracking, and model routing across OpenRouter providers.

## Requirements

### LiteLLM Proxy Configuration

#### Model Configuration (litellm_config.yaml)
```yaml
model_list:
  # Fast/Cheap tier - Intent Classification & Simple Queries
  - model_name: fast-model
    litellm_params:
      model: openrouter/deepseek/deepseek-chat
      api_key: os.environ/OPENROUTER_API_KEY
      rpm: 100
      timeout: 30
    
  # Balanced tier - General Chat
  - model_name: balanced-model
    litellm_params:
      model: openrouter/deepseek/deepseek-v3
      api_key: os.environ/OPENROUTER_API_KEY
      rpm: 60
      timeout: 60
    
  # Advanced tier - Complex Reasoning
  - model_name: advanced-model
    litellm_params:
      model: openrouter/meta-llama/llama-3.3-70b-instruct
      api_key: os.environ/OPENROUTER_API_KEY
      rpm: 30
      timeout: 90

# LiteLLM Settings
litellm_settings:
  set_verbose: False
  drop_params: True
  callbacks:
    - langfuse
  num_retries: 3
  request_timeout: 120
  fallbacks:
    - balanced-model: [fast-model]
    - advanced-model: [balanced-model]

# Langfuse Integration
langfuse:
  public_key: os.environ/LANGFUSE_PUBLIC_KEY
  secret_key: os.environ/LANGFUSE_SECRET_KEY
  host: https://cloud.langfuse.com
  enabled: true
  debug: false
```

### Environment Variables
```bash
# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# LiteLLM Proxy
LITELLM_MASTER_KEY=sk-1234  # Optional auth key for proxy
PORT=4000
```

### Langfuse Callbacks Configuration

#### Automatic Tracking
LiteLLM's Langfuse callback automatically tracks:
- **Traces**: Complete request lifecycle
- **Spans**: Individual operations (classification, retrieval, generation)
- **Generations**: LLM calls with prompts/completions
- **Scores**: Custom metrics (confidence, relevance)
- **Costs**: Token usage × provider pricing

#### Custom Metadata
```python
# In application code, add metadata to traces
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST
)

# Create trace with custom metadata
trace = langfuse.trace(
    id=request_id,
    name="rag_query",
    user_id=user_id,
    session_id=session_id,
    metadata={
        "intent": intent_type.value,
        "model_tier": tier.value,
        "query_length": len(query),
        "source": "api"
    }
)

# Add scores
trace.score(
    name="confidence",
    value=confidence_score,
    comment="Intent classification confidence"
)
```

### Docker Deployment

#### docker-compose.yml (LiteLLM Service)
```yaml
services:
  litellm-proxy:
    image: ghcr.io/berriai/litellm:main-v1.61.0
    container_name: litellm-proxy
    ports:
      - "4000:4000"
    volumes:
      - ./litellm_config.yaml:/app/config.yaml:ro
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
      - LANGFUSE_HOST=${LANGFUSE_HOST}
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
      - PORT=4000
    command: >
      --config /app/config.yaml
      --port 4000
      --host 0.0.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health/readiness"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    networks:
      - rag-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Model Routing Strategy

#### OpenRouter Model Selection
| Tier | Model | Use Case | Cost/1M tokens | Speed |
|------|-------|----------|----------------|-------|
| Fast | DeepSeek Chat | Intent classification, simple Q&A | ~$0.14 | Very Fast |
| Balanced | DeepSeek V3 | General chat, moderate complexity | ~$0.27 | Fast |
| Advanced | Llama 3.3 70B | Complex reasoning, nuanced queries | ~$0.40 | Moderate |

#### Fallback Chain
```
Advanced → Balanced → Fast
   ↓          ↓
Balanced → Fast
   ↓
Fast
```

### Health Checks

#### Readiness Endpoint
```bash
curl http://localhost:4000/health/readiness
# Returns: {"status": "healthy", "models": [...]}
```

#### Liveness Endpoint
```bash
curl http://localhost:4000/health/liveliness
# Returns: {"status": "alive"}
```

### Monitoring Dashboard (Langfuse)

#### Key Metrics to Track
1. **Latency**: P50, P90, P99 by model tier
2. **Token Usage**: Input/output tokens per request
3. **Costs**: Daily/weekly/monthly spend by model
4. **Error Rates**: By model and error type
5. **Throughput**: Requests per minute
6. **Quality Scores**: Custom scores from application

#### Alerts to Configure
- Error rate > 5% in 5 minutes
- P99 latency > 10s
- Daily cost exceeds budget
- Model availability issues

### Security Considerations

#### API Key Management
- Keys stored only in LiteLLM proxy container
- Application containers have no direct provider access
- Master key for proxy authentication (optional)
- Rotate keys monthly via environment variable updates

#### Rate Limiting
- Per-model RPM limits in config
- Global rate limiting via LiteLLM settings
- Client-specific limits (future enhancement)

## Acceptance Criteria
1. LiteLLM proxy runs as separate container
2. All three model tiers configured with OpenRouter
3. Langfuse captures all LLM calls automatically
4. Costs visible in Langfuse dashboard
5. Health checks pass for proxy service
6. Fallback chain works when models unavailable
7. Rate limiting enforced per model
8. No API keys in application containers
