# Proposal: Anti-Corruption Layer and Protocol Architecture

## Overview
Design interfaces, protocols, and registries to isolate external dependencies (LiteLLM, Haystack, Langfuse) from core business logic, enabling easy testing and future replacements.

## Requirements

### Core Protocols (abc/typing.Protocol)

#### 1. LLM Gateway Protocol
```python
class ILLMGateway(Protocol):
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion from LLM"""
        ...
    
    async def classify(
        self,
        text: str,
        classes: list[str],
        model: str
    ) -> ClassificationResult:
        """Classify text into predefined classes"""
        ...
    
    @property
    def is_healthy(self) -> bool:
        """Check gateway health"""
        ...
```

#### 2. Intent Classifier Protocol
```python
class IIntentClassifier(Protocol):
    async def classify(self, query: str) -> IntentClassification:
        """Classify user query intent"""
        ...
    
    def get_supported_intents(self) -> list[IntentType]:
        """Return list of supported intent types"""
        ...
```

#### 3. Model Router Protocol
```python
class IModelRouter(Protocol):
    def route(self, intent: IntentClassification) -> ModelRoutingDecision:
        """Route intent to appropriate model tier"""
        ...
    
    def get_routing_strategy(self, intent_type: IntentType) -> RoutingStrategy:
        """Get routing strategy for intent type"""
        ...
```

#### 4. Document Store Protocol
```python
class IDocumentStore(Protocol):
    async def search(
        self,
        query: str,
        top_k: int = 5
    ) -> list[Document]:
        """Search documents by query"""
        ...
    
    async def add_documents(self, documents: list[Document]) -> None:
        """Add documents to store"""
        ...
```

#### 5. Reranker Protocol
```python
class IReranker(Protocol):
    async def rerank(
        self,
        query: str,
        documents: list[Document],
        top_k: int = 3
    ) -> list[Document]:
        """Rerank documents based on query relevance"""
        ...
```

### Registry Pattern

#### Model Registry
```python
class ModelRegistry:
    _instance: ClassVar['ModelRegistry'] = None
    
    def __init__(self):
        self._models: dict[ModelTier, list[str]] = {}
        self._fallbacks: dict[ModelTier, ModelTier] = {}
    
    def register_tier(self, tier: ModelTier, models: list[str]) -> None:
        """Register models for a tier"""
        ...
    
    def get_models(self, tier: ModelTier) -> list[str]:
        """Get models for tier"""
        ...
    
    def get_fallback(self, tier: ModelTier) -> ModelTier | None:
        """Get fallback tier"""
        ...
```

#### Component Registry
```python
class ComponentRegistry:
    _instance: ClassVar['ComponentRegistry'] = None
    
    def __init__(self):
        self._classifiers: dict[str, IIntentClassifier] = {}
        self._routers: dict[str, IModelRouter] = {}
        self._rerankers: dict[str, IReranker] = {}
    
    def register_classifier(self, name: str, classifier: IIntentClassifier) -> None:
        ...
    
    def get_classifier(self, name: str) -> IIntentClassifier:
        ...
    
    # Similar methods for routers and rerankers
```

### Anti-Corruption Implementations

#### LiteLLM Gateway Adapter
```python
class LiteLLMGatewayAdapter:
    """Adapter implementing ILLMGateway using LiteLLM proxy"""
    
    def __init__(
        self,
        proxy_url: str,
        api_key: str | None = None,
        timeout: int = 30
    ):
        self._client = httpx.AsyncClient(
            base_url=proxy_url,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout
        )
    
    async def generate(self, prompt: str, model: str, **kwargs) -> LLMResponse:
        # Translate internal request to LiteLLM API format
        # Handle retries, timeouts, errors
        # Return standardized LLMResponse
        ...
```

#### Haystack Reranker Adapter
```python
class HaystackRerankerAdapter:
    """Adapter implementing IReranker using Haystack SentenceTransformersReranker"""
    
    def __init__(self, model_name: str, top_k: int = 3):
        self._reranker = SentenceTransformersReranker(
            model=model_name,
            top_k=top_k
        )
    
    async def rerank(self, query: str, documents: list[Document], top_k: int) -> list[Document]:
        # Convert internal Document format to Haystack format
        # Call Haystack reranker
        # Convert back to internal Document format
        ...
```

### Dependency Injection
```python
class Container:
    """Dependency injection container"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache: dict[str, Any] = {}
    
    @singleton
    def get_gateway(self) -> ILLMGateway:
        if 'gateway' not in self._cache:
            self._cache['gateway'] = LiteLLMGatewayAdapter(
                proxy_url=settings.LITELLM_PROXY_URL,
                timeout=settings.GATEWAY_TIMEOUT
            )
        return self._cache['gateway']
    
    @singleton
    def get_classifier(self) -> IIntentClassifier:
        ...
    
    @singleton
    def get_reranker(self) -> IReranker:
        ...
```

## Acceptance Criteria
1. All protocols defined with clear interfaces
2. Adapters implemented for LiteLLM, Haystack, Langfuse
3. Registries support runtime component selection
4. Singleton pattern used for expensive resources
5. No direct imports of external libraries in core business logic
6. Unit tests can mock protocols easily
7. Dependency injection container resolves all components
