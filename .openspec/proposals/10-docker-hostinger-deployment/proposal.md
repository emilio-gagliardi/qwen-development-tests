# Proposal 10: Docker Hostinger Deployment

## Overview
Deploy complete RAG application to Hostinger VPS using Docker Compose with LiteLLM proxy sidecar, proper security hardening, and production configuration.

## Problem Statement
Production deployment requires containerization, service orchestration, security hardening, and proper environment management for reliable operation on Hostinger VPS.

## Solution Approach
Create Docker Compose setup with two services (RAG app + LiteLLM proxy), configure networking, add security best practices, and document Hostinger-specific deployment steps.

## Architecture
- **Service 1**: FastAPI RAG Application (port 8000)
- **Service 2**: LiteLLM Proxy sidecar (port 4000, internal only)
- **Network**: Isolated Docker network
- **Volumes**: Persistent config and logs

## Security Features
- Non-root user in containers
- Read-only filesystem where possible
- Environment variable secrets
- Internal-only proxy exposure
- Resource limits per container

## Success Criteria
- One-command deployment
- Zero security vulnerabilities in scan
- Auto-restart on failure
- Proper log rotation

## Dependencies
- All previous proposals implemented

## Timeline
2 days for implementation and testing
