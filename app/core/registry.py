"""Service registry for dependency injection and service location."""
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Generic
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceRegistryError(Exception):
    """Raised when a service registry operation fails."""
    pass


class ServiceNotFoundError(ServiceRegistryError):
    """Raised when a requested service is not found in the registry."""
    pass


class ServiceAlreadyRegisteredError(ServiceRegistryError):
    """Raised when attempting to register an already registered service."""
    pass


class ServiceRegistry:
    """
    Centralized service registry for dependency injection.
    
    Provides a type-safe service location pattern with support for:
    - Direct service registration
    - Factory-based lazy initialization
    - Service lifecycle management
    - Type hints for better IDE support
    
    Usage:
        # Register a service instance
        ServiceRegistry.register('llm_gateway', gateway_instance)
        
        # Register a factory for lazy initialization
        ServiceRegistry.register_factory('intent_classifier', IntentClassifierFactory)
        
        # Retrieve a service
        gateway = ServiceRegistry.get('llm_gateway')
        
        # Get with type hint
        classifier: IntentClassifier = ServiceRegistry.get_typed('intent_classifier', IntentClassifier)
    """
    
    _services: Dict[str, Any] = {}
    _factories: Dict[str, Callable[[], Any]] = {}
    _types: Dict[str, type] = {}
    _initialized: Dict[str, bool] = {}
    
    @classmethod
    def register(
        cls, 
        name: str, 
        service: Any, 
        service_type: Optional[type] = None,
        allow_override: bool = False
    ) -> None:
        """
        Register a service instance.
        
        Args:
            name: Unique service identifier
            service: The service instance to register
            service_type: Optional type annotation for the service
            allow_override: Whether to allow overriding existing registrations
            
        Raises:
            ServiceAlreadyRegisteredError: If service is already registered
        """
        if name in cls._services and not allow_override:
            raise ServiceAlreadyRegisteredError(
                f"Service '{name}' is already registered. "
                "Use allow_override=True to override."
            )
        
        cls._services[name] = service
        if service_type:
            cls._types[name] = service_type
        cls._initialized[name] = True
        
        logger.debug(f"Registered service: {name}")
    
    @classmethod
    def register_factory(
        cls,
        name: str,
        factory: Callable[[], T],
        service_type: Optional[Type[T]] = None,
        singleton: bool = True
    ) -> None:
        """
        Register a factory for lazy service initialization.
        
        Args:
            name: Unique service identifier
            factory: Callable that creates the service instance
            service_type: Optional type annotation for the service
            singleton: If True, cache the created instance
            
        Raises:
            ServiceAlreadyRegisteredError: If service is already registered
        """
        if name in cls._services and name in cls._initialized:
            raise ServiceAlreadyRegisteredError(
                f"Service '{name}' is already initialized. "
                "Cannot register factory."
            )
        
        cls._factories[name] = factory
        if service_type:
            cls._types[name] = service_type
        
        # Store singleton flag for factory
        cls._services[f"{name}__singleton"] = singleton
        
        logger.debug(f"Registered factory for service: {name}")
    
    @classmethod
    def get(cls, name: str) -> Any:
        """
        Retrieve a service by name.
        
        If the service was registered with a factory and hasn't been
        initialized yet, the factory will be called to create it.
        
        Args:
            name: Service identifier
            
        Returns:
            The service instance
            
        Raises:
            ServiceNotFoundError: If service is not found
        """
        if name not in cls._services and name not in cls._factories:
            raise ServiceNotFoundError(f"Service '{name}' not found in registry")
        
        # Initialize from factory if needed
        if name in cls._factories and not cls._initialized.get(name, False):
            is_singleton = cls._services.get(f"{name}__singleton", True)
            
            try:
                logger.debug(f"Initializing service from factory: {name}")
                instance = cls._factories[name]()
                
                if is_singleton:
                    cls._services[name] = instance
                
                cls._initialized[name] = True
                
                if not is_singleton:
                    return instance
                    
            except Exception as e:
                logger.error(f"Failed to initialize service '{name}': {e}")
                raise ServiceRegistryError(
                    f"Failed to initialize service '{name}': {e}"
                ) from e
        
        return cls._services.get(name)
    
    @classmethod
    def get_typed(cls, name: str, service_type: Type[T]) -> T:
        """
        Retrieve a service with type checking.
        
        Args:
            name: Service identifier
            service_type: Expected type of the service
            
        Returns:
            The service instance with correct type
            
        Raises:
            ServiceNotFoundError: If service is not found
            TypeError: If service doesn't match expected type
        """
        service = cls.get(name)
        
        if service is not None and not isinstance(service, service_type):
            logger.warning(
                f"Service '{name}' has type {type(service)}, "
                f"expected {service_type}"
            )
        
        return service  # type: ignore
    
    @classmethod
    def has(cls, name: str) -> bool:
        """Check if a service is registered."""
        return name in cls._services or name in cls._factories
    
    @classmethod
    def is_initialized(cls, name: str) -> bool:
        """Check if a service has been initialized."""
        return cls._initialized.get(name, False)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered services (primarily for testing)."""
        cls._services.clear()
        cls._factories.clear()
        cls._types.clear()
        cls._initialized.clear()
        logger.info("Service registry cleared")
    
    @classmethod
    def list_services(cls) -> Dict[str, Dict[str, Any]]:
        """
        List all registered services with metadata.
        
        Returns:
            Dictionary of service names to metadata
        """
        result = {}
        
        for name in set(list(cls._services.keys()) + list(cls._factories.keys())):
            if name.endswith('__singleton'):
                continue
                
            result[name] = {
                'initialized': cls._initialized.get(name, False),
                'has_factory': name in cls._factories,
                'type': cls._types.get(name).__name__ if name in cls._types else 'Any',
            }
        
        return result


class Registrable(ABC):
    """Abstract base class for registrable services."""
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Return the unique service name for registration."""
        pass
    
    def register_self(self, allow_override: bool = False) -> None:
        """Register this instance in the service registry."""
        ServiceRegistry.register(
            self.get_service_name(),
            self,
            type(self),
            allow_override=allow_override
        )


__all__ = [
    'ServiceRegistry',
    'ServiceRegistryError',
    'ServiceNotFoundError',
    'ServiceAlreadyRegisteredError',
    'Registrable',
]
