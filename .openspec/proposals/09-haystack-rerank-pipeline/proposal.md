# Proposal 09: Haystack RAG Pipeline with Reranker

## Overview
Implement Haystack-based RAG pipeline with vector retrieval followed by cross-encoder reranking to improve result quality while controlling costs.

## Problem Statement
Vector search alone returns semantically similar documents that may not be most relevant for the query. Reranking improves precision but adds latency and cost.

## Solution Approach
Use two-stage retrieval: (1) Vector search retrieves top-10 candidates using fast embedding model, (2) Cross-encoder reranker scores and re-ranks to top-3 for context. This balances quality and cost.

## Pipeline Components
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (fast, free)
- **Document Store**: Haystack InMemoryDocumentStore
- **Retriever**: EmbeddingRetriever (top_k=10)
- **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (top_k=3)

## Success Criteria
- Reranking improves answer relevance by > 20%
- Total retrieval latency < 500ms
- Cost per query < $0.001

## Dependencies
- Proposal 04 (Anti-Corruption Layer)
- Proposal 06 (LiteLLM Gateway)

## Timeline
2 days for implementation
