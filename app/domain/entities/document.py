"""Domain entities representing core business concepts."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


@dataclass
class Document:
    """
    Represents a document in the RAG system.
    
    Attributes:
        id: Unique identifier for the document
        content: The actual text content of the document
        metadata: Additional information about the document
        embedding: Vector representation of the content (optional)
        created_at: Timestamp when document was created
        updated_at: Timestamp when document was last updated
    """
    content: str
    id: UUID = field(default_factory=uuid4)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self) -> None:
        """Validate document after initialization."""
        if not self.content or not self.content.strip():
            raise ValueError("Document content cannot be empty")
        
        # Ensure required metadata fields exist
        if 'source' not in self.metadata:
            self.metadata['source'] = 'unknown'
    
    def update_content(self, new_content: str) -> None:
        """
        Update document content with validation.
        
        Validates the new content before updating to maintain entity invariants.
        Updates the timestamp to reflect the modification time.
        
        Args:
            new_content: New content string for the document
            
        Raises:
            ValueError: If new_content is empty or whitespace-only
            
        Example:
            >>> doc = Document(content="Initial content")
            >>> doc.update_content("Updated content")
            >>> assert doc.content == "Updated content"
            
            >>> # This will raise ValueError
            >>> doc.update_content("")  # Raises ValueError
        """
        # Re-validate content to preserve invariant from __post_init__
        if not new_content or not new_content.strip():
            raise ValueError("Document content cannot be empty or whitespace-only")
        
        self.content = new_content
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary representation."""
        return {
            'id': str(self.id),
            'content': self.content,
            'metadata': self.metadata,
            'embedding': self.embedding,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create document from dictionary representation."""
        return cls(
            id=UUID(data['id']) if isinstance(data.get('id'), str) else data.get('id', uuid4()),
            content=data['content'],
            metadata=data.get('metadata', {}),
            embedding=data.get('embedding'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.utcnow(),
        )


@dataclass
class Query:
    """
    Represents a user query in the RAG system.
    
    Attributes:
        text: The raw query text from the user
        id: Unique identifier for the query
        normalized_text: Preprocessed/cleaned version of the query
        metadata: Additional query context
        created_at: Timestamp when query was created
    """
    text: str
    id: UUID = field(default_factory=uuid4)
    normalized_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self) -> None:
        """Validate and normalize query after initialization."""
        if not self.text or not self.text.strip():
            raise ValueError("Query text cannot be empty")
        
        # Auto-normalize if not provided
        if self.normalized_text is None:
            self.normalized_text = self._normalize(self.text)
    
    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize query text by cleaning whitespace and casing."""
        return ' '.join(text.lower().split())
    
    def with_metadata(self, **kwargs: Any) -> 'Query':
        """Create a new query with additional metadata."""
        new_metadata = {**self.metadata, **kwargs}
        return Query(
            text=self.text,
            id=self.id,
            normalized_text=self.normalized_text,
            metadata=new_metadata,
            created_at=self.created_at,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary representation."""
        return {
            'id': str(self.id),
            'text': self.text,
            'normalized_text': self.normalized_text,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
        }


__all__ = ['Document', 'Query']
