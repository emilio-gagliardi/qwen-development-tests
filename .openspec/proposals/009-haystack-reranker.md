# Proposal: Haystack RAG Pipeline with Reranker

## Overview
Implement a Haystack-based RAG pipeline with vector retrieval, cross-encoder reranking, and async generation for optimal response quality and cost efficiency.

## Requirements

### Pipeline Architecture

```
User Query → Intent Classification → Model Routing → [RAG Pipeline]
                                                    ↓
                                    ┌───────────────────────────────┐
                                    │ 1. Vector Retriever           │
                                    │    (top_k=10 documents)       │
                                    └───────────────┬───────────────┘
                                                    ↓
                                    ┌───────────────────────────────┐
                                    │ 2. Cross-Encoder Reranker     │
                                    │    (rerank to top_k=3)        │
                                    └───────────────┬───────────────┘
                                                    ↓
                                    ┌───────────────────────────────┐
                                    │ 3. Prompt Builder             │
                                    │    (context + query)          │
                                    └───────────────┬───────────────┘
                                                    ↓
                                    ┌───────────────────────────────┐
                                    │ 4. LLM Generator              │
                                    │    (routed model from tier)   │
                                    └───────────────┬───────────────┘
                                                    ↓
                                            Final Response
```

### Component Configuration

#### 1. Document Store
```python
from haystack.document_stores.in_memory import InMemoryDocumentStore

class AsyncDocumentStore:
    def __init__(self, settings: Settings):
        self._store = InMemoryDocumentStore(
            embedding_similarity_function="cosine",
            return_embedding=False
        )
        self._settings = settings
    
    async def search(self, query: str, top_k: int = 10) -> list[Document]:
        """Search documents asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._store.search(query, top_k)
        )
    
    async def add_documents(self, documents: list[Document]) -> None:
        """Add documents asynchronously"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._store.add_documents(documents)
        )
```

#### 2. Vector Retriever
```python
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever

class AsyncVectorRetriever:
    def __init__(self, document_store: AsyncDocumentStore, settings: Settings):
        self._retriever = InMemoryEmbeddingRetriever(
            document_store=document_store._store,
            top_k=settings.RETRIEVER_TOP_K,  # Default: 10
            scale_score=True
        )
        self._settings = settings
    
    async def retrieve(self, query: str) -> list[Document]:
        """Retrieve documents asynchronously"""
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self._retriever.run(query=query)
        )
        return results.get("documents", [])
```

#### 3. Cross-Encoder Reranker
```python
from haystack.components.rankers import SentenceTransformersRanker

class AsyncReranker:
    def __init__(self, settings: Settings):
        self._ranker = SentenceTransformersRanker(
            model=settings.RERANKER_MODEL,  # e.g., "ms-marco-MiniLM-L-6-v2"
            top_k=settings.RERANKER_TOP_K,   # Default: 3
            batch_size=settings.RERANKER_BATCH_SIZE
        )
        self._settings = settings
    
    async def rerank(
        self,
        query: str,
        documents: list[Document],
        top_k: int | None = None
    ) -> list[Document]:
        """Rerank documents asynchronously"""
        k = top_k or self._settings.RERANKER_TOP_K
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self._ranker.run(query=query, documents=documents, top_k=k)
        )
        
        reranked_docs = results.get("documents", [])
        
        # Log reranking scores
        logger.info(
            "Reranking completed",
            initial_count=len(documents),
            final_count=len(reranked_docs),
            scores=[doc.score for doc in reranked_docs] if reranked_docs else []
        )
        
        return reranked_docs
```

#### 4. Prompt Builder
```python
from haystack.components.builders import PromptBuilder

RAG_PROMPT_TEMPLATE = """
You are a helpful AI assistant. Answer the user's question based on the provided context.
If the context doesn't contain relevant information, say so clearly.

Context:
{% for doc in documents %}
Document {{ loop.index }}:
{{ doc.content }}
{% endfor %}

Question: {{ query }}

Answer:"""

class AsyncPromptBuilder:
    def __init__(self):
        self._builder = PromptBuilder(template=RAG_PROMPT_TEMPLATE)
    
    def build(self, query: str, documents: list[Document]) -> str:
        """Build prompt with context"""
        result = self._builder.run(template_variables={
            "query": query,
            "documents": documents
        })
        return result.get("prompt", "")
```

#### 5. Complete RAG Pipeline
```python
class AsyncRAGPipeline:
    def __init__(
        self,
        document_store: AsyncDocumentStore,
        retriever: AsyncVectorRetriever,
        reranker: AsyncReranker,
        prompt_builder: AsyncPromptBuilder,
        generator: ILLMGateway,
        settings: Settings
    ):
        self._document_store = document_store
        self._retriever = retriever
        self._reranker = reranker
        self._prompt_builder = prompt_builder
        self._generator = generator
        self._settings = settings
    
    async def execute(
        self,
        query: str,
        routing: ModelRoutingDecision
    ) -> RAGResponse:
        """Execute complete RAG pipeline"""
        start_time = time.perf_counter()
        
        try:
            # Step 1: Retrieve documents
            retrieved_docs = await self._retriever.retrieve(query)
            
            if not retrieved_docs:
                logger.warning("No documents retrieved", query_length=len(query))
                # Fall back to direct generation without context
                return await self._generate_without_context(query, routing)
            
            # Step 2: Rerank documents
            reranked_docs = await self._reranker.rerank(
                query=query,
                documents=retrieved_docs,
                top_k=self._settings.RERANKER_TOP_K
            )
            
            # Step 3: Build prompt
            prompt = self._prompt_builder.build(query, reranked_docs)
            
            # Step 4: Generate response
            llm_response = await self._generator.generate(
                prompt=prompt,
                model=routing.selected_model,
                temperature=routing.temperature,
                max_tokens=routing.max_tokens
            )
            
            # Calculate metrics
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            return RAGResponse(
                answer=llm_response.content,
                sources=[
                    {
                        "content": doc.content[:200],  # Truncate for response
                        "score": doc.score,
                        "metadata": doc.meta
                    }
                    for doc in reranked_docs
                ],
                model_used=routing.selected_model,
                tokens_used=llm_response.usage,
                intent_type=routing.intent_type,
                model_tier=routing.tier.value,
                processing_time_ms=duration_ms,
                documents_retrieved=len(retrieved_docs),
                documents_reranked=len(reranked_docs)
            )
        
        except Exception as e:
            logger.error("RAG pipeline failed", error=str(e), exc_info=True)
            raise GenerationException(
                error_code="GEN_001",
                message="Failed to generate response",
                context={"query": query[:100], "routing": routing.dict()}
            ) from e
    
    async def _generate_without_context(
        self,
        query: str,
        routing: ModelRoutingDecision
    ) -> RAGResponse:
        """Fallback: generate without RAG context"""
        prompt = f"Answer this question concisely:\n\n{query}"
        
        llm_response = await self._generator.generate(
            prompt=prompt,
            model=routing.selected_model,
            temperature=routing.temperature,
            max_tokens=routing.max_tokens
        )
        
        return RAGResponse(
            answer=llm_response.content,
            sources=[],
            model_used=routing.selected_model,
            tokens_used=llm_response.usage,
            intent_type=routing.intent_type,
            model_tier=routing.tier.value,
            processing_time_ms=0,
            documents_retrieved=0,
            documents_reranked=0,
            warning="No relevant documents found in knowledge base"
        )
```

### Reranker Model Selection

#### Recommended Models
| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| ms-marco-MiniLM-L-6-v2 | 80MB | Very Fast | Good | Default choice |
| ms-marco-TinyBERT-L-2-v2 | 16MB | Fastest | Moderate | Resource-constrained |
| bge-reranker-large | 670MB | Moderate | Excellent | High accuracy needed |

#### Configuration
```yaml
# In settings
RERANKER_MODEL: "ms-marco-MiniLM-L-6-v2"
RERANKER_TOP_K: 3
RERANKER_BATCH_SIZE: 16
RETRIEVER_TOP_K: 10
```

### Performance Optimization

#### Caching Strategy
```python
from cachetools import TTLCache

class CachedRAGPipeline:
    def __init__(self, pipeline: AsyncRAGPipeline, cache_ttl: int = 600):
        self._pipeline = pipeline
        self._cache: dict[str, RAGResponse] = TTLCache(maxsize=500, ttl=cache_ttl)
    
    async def execute(self, query: str, routing: ModelRoutingDecision) -> RAGResponse:
        # Normalize query for caching
        normalized = self._normalize_query(query)
        cache_key = f"{normalized}:{routing.tier.value}"
        
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.debug("RAG cache hit", query_hash=hash(normalized))
            return cached
        
        result = await self._pipeline.execute(query, routing)
        self._cache[cache_key] = result
        return result
```

#### Parallel Operations (Where Possible)
```python
async def execute_parallel(self, query: str, routing: ModelRoutingDecision):
    # Note: Reranking depends on retrieval, so these must be sequential
    # But we could parallelize other operations like:
    # - Logging metrics
    # - Updating usage statistics
    # - Sending webhooks
    
    retrieved_docs = await self._retriever.retrieve(query)
    reranked_docs = await self._reranker.rerank(query, retrieved_docs)
    
    # Parallel: Generate response AND log retrieval metrics
    gen_task = self._generator.generate(...)
    log_task = self._log_retrieval_metrics(retrieved_docs, reranked_docs)
    
    llm_response, _ = await asyncio.gather(gen_task, log_task)
    
    return self._build_response(llm_response, reranked_docs)
```

### Testing

#### Unit Tests
```python
async def test_rag_pipeline_with_documents():
    # Setup
    store = AsyncDocumentStore(settings)
    await store.add_documents(sample_documents)
    
    retriever = AsyncVectorRetriever(store, settings)
    reranker = AsyncReranker(settings)
    pipeline = AsyncRAGPipeline(store, retriever, reranker, ...)
    
    # Execute
    routing = ModelRoutingDecision(tier=ModelTier.BALANCED, ...)
    response = await pipeline.execute("What is Python?", routing)
    
    # Assert
    assert response.answer is not None
    assert len(response.sources) > 0
    assert response.documents_retrieved == 10
    assert response.documents_reranked == 3
```

#### Integration Tests
- Verify end-to-end latency < 3s (P95)
- Test fallback when no documents found
- Validate reranker improves relevance scores
- Measure token usage accuracy

## Acceptance Criteria
1. Haystack pipeline with 4 components (retriever, reranker, prompt builder, generator)
2. Cross-encoder reranker configured with MiniLM model
3. Retrieval returns top 10, reranking reduces to top 3
4. Fallback to direct generation when no documents found
5. All operations async with proper executor threads
6. Response includes sources with scores and metadata
7. Processing time tracked and returned
8. Cache layer for repeated queries
9. Unit and integration tests passing
