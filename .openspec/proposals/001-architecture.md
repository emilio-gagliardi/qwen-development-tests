# Proposal: Production-Ready RAG Pipeline Architecture

## Overview
Build a production-grade RAG pipeline with LiteLLM gateway, Haystack, FastAPI, and comprehensive observability for deployment on Hostinger VPS using Docker.

## Goals
- Deployable on Hostinger VPS with Docker Compose
- Complete observability with Langfuse integration
- Cost-effective model routing (OpenRouter with DeepSeek for chat)
- Fast intent classification with cheap models
- Structured logging throughout
- Anti-corruption layer for external dependencies
- Custom exception hierarchy
- Protocol-based architecture with registries
- Async-first design
- Reranker in Haystack pipeline

## Non-Goals
- Multi-tenant support (future phase)
- Real-time streaming responses (future phase)
- Custom model fine-tuning

## Constraints
- Must run within 4GB RAM limit (typical VPS constraint)
- All API keys managed through LiteLLM proxy only
- OpenRouter as primary model provider
- DeepSeek-V3 or equivalent for cost-effective chat

## Acceptance Criteria
1. Docker Compose starts all services successfully
2. Health checks pass for all components
3. End-to-end query returns response in <5s
4. Langfuse captures all LLM calls with costs
5. Structured logs in JSON format
6. Graceful error handling with custom exceptions
