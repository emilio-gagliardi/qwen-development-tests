# Tasks

## Phase 1: Docker Configuration
- [ ] Create `docker-compose.yml` with two services
- [ ] Configure RAG app service with proper ports
- [ ] Configure LiteLLM proxy as sidecar (internal only)
- [ ] Set up isolated Docker network
- [ ] Configure named volumes for logs
- [ ] Add resource limits per container

## Phase 2: Dockerfile Creation
- [ ] Create `Dockerfile.app` for RAG application
- [ ] Use Python 3.11.9-slim base image (pinned)
- [ ] Create non-root user for security
- [ ] Optimize layer caching for dependencies
- [ ] Add health check configuration
- [ ] Set proper file permissions

## Phase 3: Environment Configuration
- [ ] Create `.env.example` template
- [ ] Document all required environment variables
- [ ] Add OpenRouter API key configuration
- [ ] Add Langfuse configuration options
- [ ] Test environment variable injection

## Phase 4: Security Hardening
- [ ] Add read-only filesystem option
- [ ] Drop all capabilities except needed
- [ ] Add security options (no-new-privileges)
- [ ] Configure log rotation
- [ ] Test security scanning with Trivy

## Phase 5: Hostinger Deployment Documentation
- [ ] Document VPS setup steps
- [ ] Write Docker installation commands
- [ ] Create deployment checklist
- [ ] Add firewall configuration
- [ ] Document monitoring commands

## Phase 6: Testing & Validation
- [ ] Test local deployment with docker compose
- [ ] Verify inter-service communication
- [ ] Test health checks
- [ ] Validate resource limits
- [ ] Test auto-restart on failure
- [ ] Document troubleshooting steps

## Acceptance Criteria
- One-command deployment works
- Both services healthy and communicating
- Security scan passes with zero critical vulnerabilities
- Resource limits enforced
- Logs rotating properly
- Auto-restart on failure verified
- Complete deployment documentation

## Notes
- Test on Hostinger VPS before production
- Document any VPS-specific quirks
- Monitor costs after deployment
- Keep deployment instructions updated
