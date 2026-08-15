# Design Specification

## Architecture Layers

### Domain Layer
The domain layer contains core business logic that is independent of external frameworks:
- **Entities**: `Document`, `Query`, `Intent`, `ModelDecision`
- **Value Objects**: `ModelTier`, `IntentType`, `ConfidenceScore`
- **Domain Services**: Pure business logic operations

### Application Layer
Orchestrates domain objects to execute use cases:
- **Use Cases**: `ProcessRAGQuery`, `ClassifyIntent`, `RouteModel`
- **DTOs**: Data transfer objects for inter-layer communication
- **Validators**: Business rule validation

### Infrastructure Layer
Implements interfaces defined in domain/application layers:
- **Repositories**: Document storage abstraction
- **External Services**: LiteLLM client, Langfuse integration
- **Message Bus**: Async event publishing

### Presentation Layer
FastAPI-based API endpoints:
- **Controllers**: Request/response handling
- **Middleware**: Authentication, logging, error handling
- **Schemas**: Pydantic models for API contracts

## Configuration Singleton

```python
class ConfigSingleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.settings = Settings()
        self._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'ConfigSingleton':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

## Registry Pattern

```python
class ServiceRegistry:
    _services: Dict[str, Any] = {}
    _factories: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, name: str, service: Any):
        cls._services[name] = service
    
    @classmethod
    def register_factory(cls, name: str, factory: Callable):
        cls._factories[name] = factory
    
    @classmethod
    def get(cls, name: str) -> Any:
        if name not in cls._services and name in cls._factories:
            cls._services[name] = cls._factories[name]()
        return cls._services.get(name)
```

## Dependency Flow
```\nPresentation → Application → Domain ← Infrastructure\n                    ↑\n              Configuration Singleton\n                    ↑\n              Service Registry\n```

## Module Structure
```
app/
├── domain/
│   ├── entities/
│   ├── value_objects/
│   └── services/
├── application/
│   ├── use_cases/
│   ├── dtos/
│   └── validators/
├── infrastructure/
│   ├── repositories/
│   ├── external/
│   └── messaging/
├── presentation/
│   ├── controllers/
│   ├── middleware/
│   └── schemas/
└── core/
    ├── config.py
    └── registry.py
```
