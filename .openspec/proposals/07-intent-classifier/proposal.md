# Proposal 07: Intent Classifier

## Overview
Implement LLM-based intent classifier using cheap, fast models to categorize user queries into predefined intent types for optimal model routing.

## Problem Statement
Without understanding query intent, we cannot route to appropriate model tiers, leading to either over-spending on complex models for simple queries or poor quality responses for complex queries.

## Solution Approach
Use a lightweight LLM (DeepSeek Chat) to classify queries into 6 intent types with confidence scoring. Include rule-based fallbacks for common patterns and timeout protection.

## Intent Types (6 Total)
1. **FACTUAL_QUERY**: Seeking factual information
2. **TECHNICAL_QUESTION**: Technical/programming questions
3. **CREATIVE_TASK**: Creative writing, brainstorming
4. **ANALYSIS_REQUEST**: Analysis, comparison, evaluation
5. **SIMPLE_CHAT**: Casual conversation, greetings
6. **COMPLEX_REASONING**: Multi-step reasoning, problem solving

## Model Selection
- Primary: `openrouter/deepseek-chat` (FAST tier)
- Fallback: Rule-based keyword matching
- Timeout: 5 seconds max

## Success Criteria
- Classification latency < 500ms p95
- Accuracy > 85% on test queries
- Confidence scores calibrated
- Graceful fallback on failures

## Dependencies
- Proposal 06 (LiteLLM Gateway)
- Proposal 02 (Exception Hierarchy)

## Timeline
2 days for implementation
