# Docker Deployment Guide

This guide explains how to deploy the RAG pipeline with LiteLLM proxy as a sidecar container.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│                                                             │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │   RAG App        │         │   LiteLLM Proxy         │  │
│  │   (FastAPI +     │ ──────► │   (Sidecar)             │  │
│  │    Haystack)     │ :8000   │   - Routes to providers │  │
│  │                  │         │   - Langfuse logging    │  │
│  │  Port: 8000      │         │   - API key management  │  │
│  └──────────────────┘         │   Port: 4000            │  │
│                               └─────────────────────────┘  │
│                                         │                   │
└─────────────────────────────────────────┼───────────────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │   LLM Providers       │
                              │   - OpenAI            │
                              │   - Anthropic         │
                              │   - etc.              │
                              └───────────────────────┘
```

## Why Sidecar Pattern?

1. **Security**: API keys only exist in the proxy container, not in your app
2. **Isolation**: Proxy can be updated/restarted independently
3. **Observability**: Centralized logging of all LLM traffic via Langfuse
4. **Simplified Networking**: Services communicate via localhost within the pod/container group
5. **Resource Efficiency**: Low-latency communication between app and proxy

## Quick Start

### 1. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Configure API keys

Create a `.env` file with your credentials:

```bash
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
LANGFUSE_PUBLIC_KEY=pk-your-langfuse-key
LANGFUSE_SECRET_KEY=sk-your-langfuse-secret
```

### 3. Deploy with Docker Compose

```bash
docker-compose up -d
```

This will:
- Build the RAG application container
- Pull the LiteLLM proxy image
- Start both services on the same network
- Health check ensures proxy is ready before app starts

### 4. Verify deployment

```bash
# Check running containers
docker-compose ps

# View logs
docker-compose logs -f rag-app
docker-compose logs -f litellm-proxy

# Test the endpoint
curl http://localhost:8000/health
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Python?"}'
```

### 5. Access LiteLLM Proxy directly (optional)

```bash
# Check proxy health
curl http://localhost:4000/health/liveliness

# View available models
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-1234"
```

## Configuration Options

### LiteLLM Proxy Configuration

Edit `litellm_config.yaml` to:
- Add/remove model tiers
- Configure rate limits (rpm, tpm)
- Set up fallback strategies
- Enable/disable Langfuse integration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (proxy only) | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key (proxy only) | Optional |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | Optional |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | Optional |
| `LITELLM_PROXY_URL` | Proxy URL for app | `http://litellm-proxy:4000` |

## Langfuse Integration

The LiteLLM proxy is pre-configured to send all traces to Langfuse:

1. **Automatic Logging**: Every LLM call is logged with:
   - Token usage (prompt/completion/total)
   - Costs (calculated per provider)
   - Latency metrics
   - Model information
   - Request/response content

2. **View in Langfuse Dashboard**:
   - Navigate to your Langfuse project
   - See all traces from the proxy
   - Filter by model, cost, or time
   - Analyze patterns and optimize costs

3. **Disable Langfuse**: Remove the `callbacks` section from `litellm_config.yaml`

## Production Considerations

### Security
- Change the `master_key` in `litellm_config.yaml`
- Use secrets management (Docker secrets, Kubernetes secrets, AWS Secrets Manager)
- Enable HTTPS for external exposure
- Restrict network access to the proxy

### Scaling
- Scale the RAG app independently based on request load
- Scale the proxy based on LLM throughput needs
- Consider multiple proxy instances for high availability

### Monitoring
- Monitor proxy health endpoints
- Set up alerts for rate limit errors
- Track token consumption trends in Langfuse
- Monitor latency percentiles

### Kubernetes Deployment

For Kubernetes, convert the docker-compose to:
- Deployment for RAG app
- Deployment for LiteLLM proxy (or use LiteLLM Helm chart)
- Service for internal communication
- ConfigMap for `litellm_config.yaml`
- Secrets for API keys

Example pod structure:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: rag-pipeline
spec:
  containers:
  - name: rag-app
    image: your-registry/rag-app:latest
    env:
    - name: LITELLM_PROXY_URL
      value: "http://localhost:4000"
  - name: litellm-proxy
    image: ghcr.io/berriai/litellm:main-latest
    # ... proxy config
```

## Troubleshooting

### App can't connect to proxy
```bash
# Check network connectivity
docker-compose exec rag-app curl http://litellm-proxy:4000/health/liveliness

# Verify service names match docker-compose.yml
```

### Proxy returns authentication errors
```bash
# Check API keys are set correctly
docker-compose exec litellm-proxy env | grep API_KEY

# Verify master_key in requests matches litellm_config.yaml
```

### Langfuse not receiving data
```bash
# Check Langfuse credentials
docker-compose exec litellm-proxy env | grep LANGFUSE

# View proxy logs for callback errors
docker-compose logs litellm-proxy | grep langfuse
```

## Cost Optimization Tips

1. **Use appropriate model tiers**: The intent classifier routes simple queries to cheaper models
2. **Set rate limits**: Prevent runaway costs with rpm/tpm limits in config
3. **Monitor in Langfuse**: Identify expensive patterns and optimize
4. **Use fallbacks**: Automatically downgrade to cheaper models on errors
5. **Cache responses**: Implement caching for repeated queries (future enhancement)

## Next Steps

- Add persistent document storage (PostgreSQL, Pinecone, etc.)
- Implement response caching
- Add authentication to the FastAPI endpoint
- Set up CI/CD for automated deployments
- Configure horizontal pod autoscaling (Kubernetes)
