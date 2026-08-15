# Proposal: Docker Deployment for Hostinger VPS

## Overview
Deploy the complete RAG pipeline on Hostinger VPS using Docker Compose with optimized resource usage, health checks, and production-ready configuration.

## Requirements

### Infrastructure Specifications

#### Target Environment: Hostinger VPS
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 2-4 vCPUs
- **RAM**: 4-8 GB
- **Storage**: 50-100 GB SSD
- **Network**: Public IP with firewall rules

#### Resource Allocation
| Service | CPU Limit | Memory Limit | Storage |
|---------|-----------|--------------|---------|
| LiteLLM Proxy | 0.5 cores | 512 MB | 100 MB |
| RAG API | 1.5 cores | 2 GB | 500 MB |
| (Optional) Redis | 0.25 cores | 256 MB | 100 MB |

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  # LiteLLM Proxy - Standalone LLM Gateway
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
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # RAG API Application
  rag-api:
    build:
      context: .
      dockerfile: Dockerfile.app
    container_name: rag-api
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - LITELLM_PROXY_URL=http://litellm-proxy:4000
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
      - LANGFUSE_HOST=${LANGFUSE_HOST}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    depends_on:
      litellm-proxy:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    networks:
      - rag-network
    deploy:
      resources:
        limits:
          cpus: '1.5'
          memory: 2G
        reservations:
          cpus: '0.75'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

networks:
  rag-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### Dockerfile for RAG Application

```dockerfile
# Dockerfile.app
FROM python:3.11.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup tests/ ./tests/

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### Environment Variables (.env)

```bash
# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com

# LiteLLM Proxy
LITELLM_MASTER_KEY=sk-master-key-change-this

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json

# Optional: Redis for caching (if added)
REDIS_URL=redis://redis:6379/0
```

### Deployment Script

```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 Deploying RAG Pipeline to Hostinger VPS..."

# Pull latest code
git pull origin dev

# Build Docker images
echo "📦 Building Docker images..."
docker-compose build

# Start services
echo "🏃 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Check health
echo "🏥 Checking service health..."
curl -f http://localhost:4000/health/readiness || echo "⚠️  LiteLLM proxy not ready yet"
curl -f http://localhost:8000/health || echo "⚠️  RAG API not ready yet"

# Show logs
echo "📋 Showing recent logs..."
docker-compose logs --tail=20

echo "✅ Deployment complete!"
echo ""
echo "Endpoints:"
echo "  - RAG API: http://$(hostname -I | awk '{print $1}'):8000"
echo "  - LiteLLM Proxy: http://$(hostname -I | awk '{print $1}'):4000"
echo "  - Langfuse Dashboard: https://cloud.langfuse.com"
```

### Firewall Configuration (Hostinger)

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (if using reverse proxy)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow application ports (restrict to specific IPs if possible)
sudo ufw allow 8000/tcp
sudo ufw allow 4000/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### Monitoring and Maintenance

#### Log Rotation
Already configured in docker-compose with:
- Max size: 10-50 MB per file
- Max files: 3-5 per service
- Automatic rotation when limit reached

#### Health Check Commands
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f rag-api
docker-compose logs -f litellm-proxy

# Restart services
docker-compose restart rag-api
docker-compose restart litellm-proxy

# Update and redeploy
docker-compose pull
docker-compose up -d --force-recreate
```

#### Backup Strategy
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/rag-pipeline"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration files
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    litellm_config.yaml \
    docker-compose.yml \
    .env

# Backup any persistent data (if using external DB)
# docker run --rm -v rag_pipeline_data:/data -v $BACKUP_DIR:/backup alpine tar -czf /backup/data_$DATE.tar.gz /data

echo "Backup completed: $BACKUP_DIR/config_$DATE.tar.gz"

# Keep only last 7 backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

### Performance Tuning

#### Uvicorn Workers
```python
# In production, use multiple workers
# Formula: (2 x CPU_CORES) + 1
# For 2-core VPS: 5 workers (but limited by memory)
# Recommended: 2-4 workers for 4GB RAM

# In docker-compose CMD:
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

#### Memory Optimization
```yaml
# In docker-compose, set appropriate limits
deploy:
  resources:
    limits:
      memory: 2G  # Prevent OOM kills
    reservations:
      memory: 1G  # Guaranteed memory
```

### Security Hardening

1. **Change default keys**: Update all placeholder API keys
2. **Restrict network access**: Use firewall rules to limit port access
3. **Non-root containers**: Both containers run as non-root users
4. **Read-only config volumes**: Config files mounted as read-only (`:ro`)
5. **Regular updates**: Schedule monthly `docker-compose pull` for security patches
6. **Secret management**: Consider HashiCorp Vault for production secrets

### Troubleshooting

#### Common Issues

**LiteLLM proxy won't start:**
```bash
docker-compose logs litellm-proxy
# Check config.yaml syntax
# Verify API keys are valid
```

**RAG API returns 500 errors:**
```bash
docker-compose logs rag-api
# Check connection to litellm-proxy
# Verify model names match config
```

**Out of memory:**
```bash
docker stats
# Reduce worker count or memory limits
# Consider upgrading VPS plan
```

**Slow responses:**
```bash
# Check Langfuse for latency metrics
# Verify reranker model is cached
# Consider adding Redis for query caching
```

## Acceptance Criteria
1. Docker Compose starts all services successfully
2. Health checks pass within 60 seconds
3. Resource limits prevent OOM issues
4. Logs rotate automatically
5. Services restart on failure
6. Network isolation between containers
7. Non-root users in containers
8. Backup script tested and working
9. Firewall configured correctly
10. Documentation includes troubleshooting guide
