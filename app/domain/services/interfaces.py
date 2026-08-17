"""Domain service protocols (interfaces) for business logic."""
from abc import ABC, abstractmethod
from typing import List, Optional, Protocol
import uuid

from app.domain.entities.document import Document
from app.domain.entities.document import Query
from app.domain.value_objects.types import ConfidenceScore, IntentType, ModelTier


class DocumentRepositoryProtocol(Protocol):
    """Protocol for document storage operations."""
    
    async def add(self, document: Document) -> None:
        """Add a document to the repository."""
        ...
    
    async def add_batch(self, documents: List[Document]) -> None:
        """Add multiple documents to the repository."""
        ...
    
    async def get_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        """Retrieve a document by its ID."""
        ...
    
    async def search(self, query: str, top_k: int = 10) -> List[Document]:
        """Search for documents matching a query."""
        ...
    
    async def delete(self, document_id: uuid.UUID) -> bool:
        """Delete a document by ID. Returns True if deleted."""
        ...
    
    async def count(self) -> int:
        """Return total number of documents."""
        ...


class IntentClassifierProtocol(Protocol):
    """Protocol for intent classification service."""
    
    async def classify(self, query: str) -> tuple[IntentType, ConfidenceScore]:
        """
        Classify the intent of a user query.
        
        Args:
            query: The user's query text
            
        Returns:
            Tuple of (IntentType, ConfidenceScore)
        """
        ...


class ModelRouterProtocol(Protocol):
    """Protocol for model routing service."""
    
    async def route(
        self, 
        intent: IntentType, 
        confidence: ConfidenceScore
    ) -> tuple[str, str]:
        """
        Route an intent to an appropriate model.
        
        Args:
            intent: The classified intent type
            confidence: Confidence score of the classification
            
        Returns:
            Tuple of (model_name, tier)
        """
        ...


class LLMGatewayProtocol(Protocol):
    """Protocol for LLM gateway service."""
    
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using an LLM.
        
        Args:
            prompt: The input prompt
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        ...
    
    async def generate_with_context(
        self,
        messages: List[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using chat-style messages.
        
        Args:
            messages: List of message dicts with role/content
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        ...


class RerankerProtocol(Protocol):
    """Protocol for document reranking service."""
    
    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 3,
    ) -> List[Document]:
        """
        Rerank documents based on relevance to query.
        
        Args:
            query: The search query
            documents: List of documents to rerank
            top_k: Number of top documents to return
            
        Returns:
            Reranked list of documents
        """
        ...


class IntentClassificationService(ABC):
    """Abstract base class for intent classification services."""
    
    @abstractmethod
    async def classify(self, query: str) -> tuple[IntentType, ConfidenceScore]:
        """Classify the intent of a query."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the service is healthy."""
        pass


class ModelRoutingService(ABC):
    """Abstract base class for model routing services."""
    
    @abstractmethod
    async def route(
        self, 
        intent: IntentType, 
        confidence: ConfidenceScore
    ) -> tuple[str, str]:
        """Route intent to appropriate model."""
        pass
    
    @abstractmethod
    def get_routing_explanation(self, intent: IntentType) -> str:
        """Get explanation for routing decision."""
        pass


__all__ = [
    'DocumentRepositoryProtocol',
    'IntentClassifierProtocol',
    'ModelRouterProtocol',
    'LLMGatewayProtocol',
    'RerankerProtocol',
    'IntentClassificationService',
    'ModelRoutingService',
]
