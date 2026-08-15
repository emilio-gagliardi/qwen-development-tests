# Anti-Corruption Layer Design

## Protocol Definitions

### LLMGateway Protocol
```python
from typing import Protocol, AsyncIterator, Optional, Any
from app.domain.entities import LLMResponse, LLMChunk

class LLMGateway(Protocol):
    """Protocol for LLM provider abstraction."""
    
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Generate text completion from LLM.
        
        Args:
            prompt: Input prompt text
            model: Model identifier
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            stop_sequences: Sequences that stop generation
            **kwargs: Additional provider-specific parameters
        
        Returns:
            LLMResponse with generated text and metadata
        
        Raises:
            LiteLLMGatewayError: If generation fails
        """
        ...
    
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        **kwargs: Any
    ) -> AsyncIterator[LLMChunk]:
        """
        Generate streaming text completion.
        
        Yields:
            LLMChunk objects with incremental text
        
        Raises:
            LiteLLMGatewayError: If streaming fails
        """
        ...
    
    async def health_check(self) -> bool:
        """Check if gateway is operational."""
        ...
```

### IntentClassifier Protocol
```python
from typing import Protocol
from app.domain.entities import IntentClassification, IntentType

class IntentClassifier(Protocol):
    """Protocol for intent classification."""
    
    async def classify(self, query: str) -> IntentClassification:
        """
        Classify user query into intent type.
        
        Args:
            query: User's input query
        
        Returns:
            IntentClassification with intent type and confidence
        
        Raises:
            IntentClassificationError: If classification fails
            ConfidenceThresholdError: If confidence below threshold
        """
        ...
    
    async def classify_batch(
        self, 
        queries: List[str]
    ) -> List[IntentClassification]:
        """Classify multiple queries in batch."""
        ...
```

### ModelRouter Protocol
```python
from typing import Protocol
from app.domain.entities import ModelRoutingDecision, ModelTier, IntentType

class ModelRouter(Protocol):
    """Protocol for model routing decisions."""
    
    async def route(
        self,
        intent: IntentType,
        confidence: float,
        context: Optional[Dict[str, Any]] = None
    ) -> ModelRoutingDecision:
        """
        Determine optimal model tier based on intent and confidence.
        
        Args:
            intent: Classified intent type
            confidence: Classification confidence score (0.0-1.0)
            context: Additional routing context
        
        Returns:
            ModelRoutingDecision with selected tier and model
        
        Raises:
            ModelRoutingError: If routing decision fails
            InvalidModelTierError: If tier selection invalid
        """
        ...
    
    def get_routing_explanation(self, intent: IntentType) -> str:
        """Get human-readable explanation of routing strategy."""
        ...
```

### DocumentStore Protocol
```python
from typing import Protocol, List, Optional
from app.domain.entities import Document, RetrievedDocument

class DocumentStore(Protocol):
    """Protocol for document storage and retrieval."""
    
    async def add_documents(
        self,
        documents: List[Document],
        batch_size: int = 100
    ) -> None:
        """
        Add documents to store.
        
        Args:
            documents: List of documents to add
            batch_size: Batch size for bulk operations
        
        Raises:
            DocumentStoreError: If storage fails
        """
        ...
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedDocument]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Metadata filters
        
        Returns:
            List of retrieved documents with scores
        
        Raises:
            VectorSearchError: If search fails
        """
        ...
    
    async def delete_documents(self, document_ids: List[str]) -> None:
        """Delete documents by ID."""
        ...
    
    async def count(self) -> int:
        """Get total document count."""
        ...
```

### TelemetryClient Protocol
```python
from typing import Protocol, Optional, Dict, Any
from app.domain.entities import GenerationTrace, TokenUsage

class TelemetryClient(Protocol):
    """Protocol for observability telemetry."""
    
    async def trace_generation(
        self,
        trace_data: GenerationTrace
    ) -> None:
        """
        Record generation trace for observability.
        
        Args:
            trace_data: Generation trace with inputs/outputs
        
        Raises:
            LangfuseIntegrationError: If tracing fails
        """
        ...
    
    async def log_token_usage(
        self,
        usage_data: TokenUsage
    ) -> None:
        """
        Log token consumption metrics.
        
        Args:
            usage_data: Token usage with model and counts
        
        Raises:
            LangfuseIntegrationError: If logging fails
        """
        ...
    
    async def trace_error(
        self,
        error_code: str,
        message: str,
        context: Dict[str, Any]
    ) -> None:
        """Record error trace."""
        ...
```

## Registry Implementation

```python
from typing import Type, Dict, Any, Optional, Protocol, Callable
from app.core.exceptions import ConfigurationError

class ServiceRegistry:
    """Central registry for service implementations."""
    
    _services: Dict[str, Any] = {}
    _protocols: Dict[Type[Protocol], str] = {}
    _factories: Dict[str, Callable[[], Any]] = {}
    _initialized: Dict[str, bool] = {}
    
    @classmethod
    def register(
        cls,
        interface: Type[Protocol],
        implementation: Any,
        name: Optional[str] = None
    ) -> None:
        """Register a service implementation."""
        service_name = name or interface.__name__
        cls._protocols[interface] = service_name
        cls._services[service_name] = implementation
        cls._initialized[service_name] = True
    
    @classmethod
    def register_factory(
        cls,
        interface: Type[Protocol],
        factory: Callable[[], Any],
        name: Optional[str] = None
    ) -> None:
        """Register a factory for lazy initialization."""
        service_name = name or interface.__name__
        cls._protocols[interface] = service_name
        cls._factories[service_name] = factory
        cls._initialized[service_name] = False
    
    @classmethod
    def get(cls, interface: Type[Protocol]) -> Any:
        """Get service implementation by protocol."""
        name = cls._protocols.get(interface)
        if not name:
            raise ConfigurationError(
                f"No implementation registered for {interface.__name__}",
                context={"protocol": interface.__name__}
            )
        
        # Lazy initialization if factory registered
        if not cls._initialized.get(name, False) and name in cls._factories:
            cls._services[name] = cls._factories[name]()
            cls._initialized[name] = True
        
        service = cls._services.get(name)
        if not service:
            raise ConfigurationError(
                f"Service {name} not initialized",
                context={"service_name": name}
            )
        
        return service
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (for testing)."""
        cls._services.clear()
        cls._protocols.clear()
        cls._factories.clear()
        cls._initialized.clear()
```

## Adapter Implementations

### LiteLLM Gateway Adapter
```python
class LiteLLMGatewayAdapter:
    """Adapter implementing LLMGateway protocol using LiteLLM."""
    
    def __init__(
        self,
        proxy_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        self.proxy_url = proxy_url
        self.api_key = api_key
        self.timeout = timeout
        self._client = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        )
    
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        # Adapt LiteLLM response to domain LLMResponse
        ...
    
    async def health_check(self) -> bool:
        # Check proxy health
        ...
```

### Haystack Document Store Adapter
```python
class HaystackDocumentStoreAdapter:
    """Adapter implementing DocumentStore protocol using Haystack."""
    
    def __init__(self, document_store: InMemoryDocumentStore):
        self._store = document_store
        self._retriever = None
    
    async def add_documents(
        self,
        documents: List[Document],
        batch_size: int = 100
    ) -> None:
        # Convert domain Documents to Haystack Documents
        # Add to store
        ...
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[RetrievedDocument]:
        # Use Haystack retriever
        # Convert to domain RetrievedDocuments
        ...
```

## Usage Example

```python
# Register services at application startup
def bootstrap_services():
    # Register LiteLLM gateway
    gateway = LiteLLMGatewayAdapter(
        proxy_url=settings.LITELLM_PROXY_URL,
        api_key=settings.OPENROUTER_API_KEY
    )
    ServiceRegistry.register(LLMGateway, gateway, "litellm-gateway")
    
    # Register intent classifier with lazy factory
    def create_classifier():
        gateway = ServiceRegistry.get(LLMGateway)
        return IntentClassifierImpl(gateway)
    ServiceRegistry.register_factory(IntentClassifier, create_classifier)
    
    # Register document store
    store = HaystackDocumentStoreAdapter(InMemoryDocumentStore())
    ServiceRegistry.register(DocumentStore, store)

# Use in application layer
async def process_query(query: str):
    classifier = ServiceRegistry.get(IntentClassifier)
    intent = await classifier.classify(query)
    
    router = ServiceRegistry.get(ModelRouter)
    decision = await router.route(intent.intent_type, intent.confidence)
    
    gateway = ServiceRegistry.get(LLMGateway)
    response = await gateway.generate(prompt, decision.model_id)
    
    return response
```
