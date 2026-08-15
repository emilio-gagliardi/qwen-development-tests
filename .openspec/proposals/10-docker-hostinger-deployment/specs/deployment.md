# Docker Hostinger Deployment Design

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  # Main RAG Application
  rag-app:
    build:
      context: .
      dockerfile: Dockerfile.app
    container_name: rag-pipeline-app
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - LITELLM_PROXY_URL=http://litellm-proxy:4000
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
      - LANGFUSE_HOST=${LANGFUSE_HOST:-https://cloud.langfuse.com}
    depends_on:
      litellm-proxy:
        condition: service_healthy
    networks:
      - rag-network
    volumes:
      - app-logs:/app/logs
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # LiteLLM Proxy Sidecar
  litellm-proxy:
    image: ghcr.io/berriai/litellm:main-v1.61.0
    container_name: litellm-proxy
    restart: unless-stopped
    expose:
      - "4000"  # Internal only, not exposed to host
    volumes:
      - ./litellm_config.yaml:/app/config.yaml:ro
      - litellm-logs:/app/logs
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
      - LANGFUSE_HOST=${LANGFUSE_HOST:-https://cloud.langfuse.com}
    command: >
      --config /app/config.yaml
      --port 4000
      --detailed_debug
    networks:
      - rag-network
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  rag-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

volumes:
  app-logs:
    driver: local
  litellm-logs:
    driver: local
```

## Application Dockerfile (Dockerfile.app)

```dockerfile
FROM python:3.11.9-slim

# Security: Non-root user
RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

## Environment File (.env)

```bash
# OpenRouter API Key
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Optional: Custom Langfuse host for self-hosted
# LANGFUSE_HOST=https://langfuse.yourdomain.com
```

## Hostinger VPS Deployment Steps

### 1. Connect to VPS
```bash
ssh root@your-vps-ip
```

### 2. Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl enable docker
systemctl start docker
```

### 3. Install Docker Compose
```bash
apt-get update
apt-get install docker-compose-plugin
```

### 4. Clone Repository
```bash
git clone -b dev https://github.com/emilio-gagliardi/qwen-development-tests.git
cd qwen-development-tests
```

### 5. Configure Environment
```bash
cp .env.example .env
nano .env  # Edit with your API keys
```

### 6. Deploy
```bash
docker compose up -d --build
```

### 7. Verify Deployment
```bash
docker compose ps
docker compose logs -f rag-app
curl http://localhost:8000/health
```

### 8. Setup Firewall (Optional)
```bash
ufw allow 8000/tcp
ufw enable
```

## Security Hardening

### Read-Only Root Filesystem
```yaml
# Add to service definition
read_only: true
tmpfs:
  - /tmp
```

### Drop Capabilities
```yaml
# Add to service definition
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE
```

### Security Options
```yaml
security_opt:
  - no-new-privileges:true
```

## Monitoring Commands

```bash
# View logs
docker compose logs -f rag-app
docker compose logs -f litellm-proxy

# Check resource usage
docker stats

# Restart services
docker compose restart rag-app

# Update deployment
git pull
docker compose up -d --build

# Backup logs
docker run --rm -v app-logs:/source -v $(pwd):/backup alpine tar czf /backup/logs.tar.gz /source
```

## Troubleshooting

### Check Service Status
```bash
docker compose ps
docker inspect rag-app
```

### View Logs
```bash
docker compose logs --tail=100 rag-app
docker compose exec rag-app cat /app/logs/app.log
```

### Test Connectivity
```bash
docker compose exec rag-app curl http://litellm-proxy:4000/health
```

### Resource Limits
```bash
docker stats --no-stream
```
