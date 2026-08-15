# Proposal 04: Anti-Corruption Layer

## Overview
Implement a comprehensive anti-corruption layer (ACL) with well-defined interfaces, protocols, and registries to protect the domain model from external system complexities and changes.

## Problem Statement
Direct coupling to external services (LiteLLM, Haystack, Langfuse, OpenRouter) creates tight dependencies that make testing difficult and the system fragile to external API changes. We need clear boundaries with adaptation logic isolated in the infrastructure layer.

## Solution Approach
Define domain-focused protocols/interfaces that external implementations must satisfy. Use adapter pattern to translate between external APIs and our domain models. Register implementations in a service registry for dependency injection.

## Key Interfaces/Protocols (5 Total)

### 1. LLMGateway Protocol
```python
class LLMGateway(Protocol):
    """Protocol for LLM provider abstraction."""
    
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text completion."""
        ...
    
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> AsyncIterator[LLMChunk]:
        """Generate streaming text completion."""
        ...
```

### 2. IntentClassifier Protocol
```python
class IntentClassifier(Protocol):
    """Protocol for intent classification."""
    
    async def classify(self, query: str) -> IntentClassification:
        """Classify user query intent."""
        ...
```

### 3. ModelRouter Protocol
```python
class ModelRouter(Protocol):
    """Protocol for model routing decisions."""
    
    async def route(
        self,
        intent: IntentType,
        confidence: float
    ) -> ModelRoutingDecision:
        """Determine optimal model tier based on intent."""
        ...
```

### 4. DocumentStore Protocol
```python
class DocumentStore(Protocol):
    """Protocol for document storage and retrieval."""
    
    async def add_documents(self, documents: List[Document]) -> None:
        """Add documents to store."""
        ...
    
    async def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[RetrievedDocument]:
        """Search for relevant documents."""
        ...
```

### 5. TelemetryClient Protocol
```python
class TelemetryClient(Protocol):
    """Protocol for observability telemetry."""
    
    async def trace_generation(
        self,
        trace_data: GenerationTrace
    ) -> None:
        """Record generation trace."""
        ...
    
    async def log_token_usage(
        self,
        usage_data: TokenUsage
    ) -> None:
        """Log token consumption."""
        ...
```

## Registry Implementation
```python
class ServiceRegistry:
    _services: Dict[str, Any] = {}
    _protocols: Dict[Type[Protocol], str] = {}
    
    @classmethod
    def register(cls, interface: Type[Protocol], implementation: Any, name: str):
        cls._protocols[interface] = name
        cls._services[name] = implementation
    
    @classmethod
    def get(cls, interface: Type[Protocol]) -> Any:
        name = cls._protocols.get(interface)
        if not name:
            raise ConfigurationError(f"No implementation registered for {interface}")
        return cls._services.get(name)
```

## Success Criteria
- All external dependencies accessed through protocols
- Zero direct imports of external libraries in domain/application layers
- Easy mocking for unit tests
- Clear separation of concerns

## Dependencies
- Proposal 01 (Core Architecture)
- Proposal 02 (Exception Hierarchy)

## Timeline
2 days for implementation
