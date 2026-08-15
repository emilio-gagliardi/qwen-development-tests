# Proposal 06: LiteLLM Gateway with OpenRouter Integration

## Overview
Implement LiteLLM gateway client with OpenRouter provider integration, starting with cheap DeepSeek models for chat requests and configuring model tiers for cost optimization.

## Problem Statement
Multiple LLM providers require different API formats, authentication, and error handling. We need a unified interface that supports cost-effective model selection with OpenRouter as the primary provider.

## Solution Approach
Configure LiteLLM proxy to route through OpenRouter, define model tiers (FAST, BALANCED, ADVANCED), and implement gateway client with retry logic, timeout management, and Langfuse integration.

## Model Configuration
- **FAST Tier**: `openrouter/deepseek-chat` - $0.14/M input, $0.28/M output
- **BALANCED Tier**: `openrouter/meta-llama/llama-3.3-70b-instruct` - $0.39/M input, $0.50/M output  
- **ADVANCED Tier**: `openrouter/openai/gpt-4-turbo` - $10/M input, $30/M output

## Key Features
- OpenRouter API integration via LiteLLM
- Model tier mapping with cost tracking
- Automatic retry with exponential backoff
- Timeout configuration per tier
- Langfuse trace integration at proxy level

## Success Criteria
- All three tiers configured and tested
- Cost tracking via Langfuse
- Retry logic handles transient failures
- Sub-second latency for FAST tier

## Dependencies
- Proposal 03 (Structured Logging)
- Proposal 04 (Anti-Corruption Layer)

## Timeline
2 days for implementation
