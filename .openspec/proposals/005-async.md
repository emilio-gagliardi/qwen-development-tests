# Proposal: Async-First Architecture

## Overview
Implement fully asynchronous architecture throughout the application to maximize throughput and minimize blocking operations, essential for VPS deployments with limited resources.

## Requirements

### Async Components

#### 1. FastAPI Application
```python
# All route handlers are async
@app.post("/rag/query")
async def rag_query(request: RAGRequest) -> RAGResponse:
    async with log_operation(logger, "rag_query", request_id=request_id):
        # All operations awaited
        intent = await classifier.classify(request.query)
        decision = router.route(intent)
        response = await pipeline.execute(request.query, decision)
        return response
```

#### 2. Intent Classifier
```python
class AsyncIntentClassifier:
    def __init__(self, gateway: ILLMGateway, settings: Settings):
        self._gateway = gateway
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_CLASSIFICATIONS)
    
    async def classify(self, query: str) -> IntentClassification:
        async with self._semaphore:
            # Non-blocking LLM call
            result = await self._gateway.classify(
                text=query,
                classes=self._supported_intents,
                model=self._settings.CLASSIFICATION_MODEL
            )
            return self._parse_result(result)
```

#### 3. LiteLLM Gateway Client
```python
class AsyncLiteLLMGateway:
    def __init__(self, proxy_url: str, settings: Settings):
        self._client = httpx.AsyncClient(
            base_url=proxy_url,
            timeout=httpx.Timeout(
                connect=settings.CONNECT_TIMEOUT,
                read=settings.READ_TIMEOUT,
                write=settings.WRITE_TIMEOUT
            ),
            limits=httpx.Limits(
                max_connections=settings.MAX_CONNECTIONS,
                max_keepalive_connections=settings.MAX_KEEPALIVE
            ),
            transport=httpx.AsyncHTTPTransport(retries=settings.RETRY_COUNT)
        )
    
    async def generate(self, prompt: str, model: str, **kwargs) -> LLMResponse:
        # Non-blocking HTTP request
        response = await self._client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                **kwargs
            }
        )
        response.raise_for_status()
        return self._parse_response(response.json())
    
    async def close(self):
        await self._client.aclose()
```

#### 4. Haystack Pipeline
```python
class AsyncRAGPipeline:
    def __init__(
        self,
        document_store: IDocumentStore,
        retriever: IRetriever,
        reranker: IReranker,
        generator: ILLMGateway
    ):
        self._document_store = document_store
        self._retriever = retriever
        self._reranker = reranker
        self._generator = generator
    
    async def execute(self, query: str, routing: ModelRoutingDecision) -> RAGResponse:
        # Parallel retrieval and other operations where possible
        docs_task = self._retriever.retrieve(query, top_k=10)
        
        # Await retrieval
        documents = await docs_task
        
        # Sequential reranking (depends on retrieval)
        reranked_docs = await self._reranker.rerank(query, documents, top_k=3)
        
        # Build prompt with context
        context = self._build_context(reranked_docs)
        prompt = self._build_prompt(query, context)
        
        # Generate response
        llm_response = await self._generator.generate(
            prompt=prompt,
            model=routing.selected_model,
            temperature=routing.temperature
        )
        
        return RAGResponse(
            answer=llm_response.content,
            sources=[doc.metadata for doc in reranked_docs],
            model_used=routing.selected_model,
            tokens_used=llm_response.usage
        )
```

#### 5. Document Store Operations
```python
class AsyncInMemoryDocumentStore:
    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._index = None  # FAISS or similar
        self._lock = asyncio.Lock()
    
    async def search(self, query: str, top_k: int = 5) -> list[Document]:
        # Run blocking index search in thread pool
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self._index.search(query, top_k)
        )
        return results
    
    async def add_documents(self, documents: list[Document]) -> None:
        async with self._lock:
            # Batch insert
            for doc in documents:
                self._documents[doc.id] = doc
            
            # Rebuild index in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._rebuild_index)
```

### Concurrency Controls

#### Semaphores for Rate Limiting
```python
class ConcurrencyManager:
    def __init__(self, settings: Settings):
        self._classification_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_CLASSIFICATIONS)
        self._generation_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_GENERATIONS)
        self._rerank_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_RERANKS)
    
    @asynccontextmanager
    async def acquire_classification(self):
        async with self._classification_semaphore:
            yield
    
    # Similar methods for generation and rerank
```

#### Timeout Handling
```python
async def with_timeout[T](coro: Coroutine[Any, Any, T], timeout: float, operation: str) -> T:
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"{operation} timed out after {timeout}s")
        raise GenerationException(
            error_code="GEN_002",
            message=f"{operation} timed out",
            context={"timeout": timeout, "operation": operation}
        )
```

#### Retry Logic with Exponential Backoff
```python
async def retry_with_backoff[T](
    coro_func: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[Exception]] = (GatewayException,)
) -> T:
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_func()
        except exceptions as e:
            last_exception = e
            if attempt == max_retries:
                break
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s", error=str(e))
            await asyncio.sleep(delay)
    raise last_exception
```

### Event Loop Configuration
```python
# Main entry point
def main():
    # Configure event loop for production
    if sys.platform != "win32":
        # Use uvloop for better performance on Unix
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    # Run FastAPI with uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=settings.WORKERS,  # Number of uvicorn workers
        loop="uvloop",
        http="httptools"
    )
```

## Acceptance Criteria
1. All I/O operations are async (no blocking calls)
2. Blocking operations run in thread pools
3. Concurrency limits enforced with semaphores
4. Timeouts on all external calls
5. Retry logic with exponential backoff
6. Proper cleanup in async context managers
7. No race conditions with shared state
8. Performance tests show linear scaling with concurrent requests
