"""Haystack-based RAG pipeline components."""

from typing import List, Optional
from haystack import Document, Pipeline
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder
from haystack.components.preprocessors import DocumentSplitter
from haystack.document_stores.types import DuplicatePolicy

from app.config import Settings
from app.schemas import DocumentSource


class RAGPipeline:
    """Minimal RAG pipeline using Haystack.
    
    This component handles document storage, retrieval, and generation
    using Haystack's modular pipeline architecture.
    
    Note: For production use, replace InMemoryDocumentStore with a 
    persistent store like Elasticsearch, Qdrant, or Weaviate.
    """
    
    def __init__(self, settings: Settings, litellm_base_url: str, api_key: Optional[str] = None):
        self.settings = settings
        self.litellm_base_url = litellm_base_url
        self.api_key = api_key
        
        # Initialize document store
        self.document_store = InMemoryDocumentStore()
        
        # Build the RAG pipeline
        self.pipeline = self._build_pipeline()
    
    def _build_pipeline(self) -> Pipeline:
        """Build the Haystack RAG pipeline.
        
        Returns:
            Configured Haystack Pipeline
        """
        pipeline = Pipeline()
        
        # Add components
        pipeline.add_component(
            "retriever", 
            InMemoryEmbeddingRetriever(document_store=self.document_store)
        )
        
        # Prompt template for RAG
        prompt_template = """
Given the following context documents, answer the user's question.
If the context doesn't contain relevant information, say so clearly.

Context Documents:
{% for doc in documents %}
Document {{ loop.index }}:
{{ doc.content }}
{% endfor %}

Question: {{ query }}

Answer:
"""
        
        pipeline.add_component(
            "prompt_builder",
            PromptBuilder(template=prompt_template)
        )
        
        # Use OpenAI generator pointing to LiteLLM
        # LiteLLM provides OpenAI-compatible API
        generator_api_key = self.api_key or "not-needed"
        
        pipeline.add_component(
            "generator",
            OpenAIGenerator(
                api_base_url=self.litellm_base_url,
                api_key=generator_api_key,
                generation_kwargs={
                    "max_tokens": 512,
                    "temperature": 0.7,
                }
            )
        )
        
        # Connect components
        pipeline.connect("retriever.documents", "prompt_builder.documents")
        pipeline.connect("prompt_builder.prompt", "generator.prompt")
        
        return pipeline
    
    def add_documents(self, documents: List[dict]) -> int:
        """Add documents to the document store.
        
        Args:
            documents: List of document dicts with 'content' and optional 'metadata'
            
        Returns:
            Number of documents added
        """
        haystack_docs = []
        for doc in documents:
            haystack_doc = Document(
                content=doc["content"],
                metadata=doc.get("metadata", {}),
                embedding=doc.get("embedding")  # Optional pre-computed embedding
            )
            haystack_docs.append(haystack_doc)
        
        self.document_store.write_documents(
            haystack_docs,
            policy=DuplicatePolicy.OVERWRITE
        )
        
        return len(haystack_docs)
    
    async def query(
        self,
        query: str,
        model: str,
        top_k: int = 5,
        include_sources: bool = True,
    ) -> tuple[str, List[DocumentSource]]:
        """Execute a RAG query.
        
        Args:
            query: User query string
            model: Model to use for generation (via LiteLLM)
            top_k: Number of documents to retrieve
            include_sources: Whether to return source documents
            
        Returns:
            Tuple of (answer, sources)
        """
        # Configure retriever for this query
        self.pipeline.get_component("retriever").top_k = top_k
        
        # Configure generator for the selected model
        generator = self.pipeline.get_component("generator")
        generator.model = model
        
        # Run the pipeline
        result = self.pipeline.run({
            "retriever": {"query": query},
            "prompt_builder": {"query": query},
        })
        
        # Extract answer
        answer = result["generator"]["replies"][0] if result.get("generator") else ""
        
        # Extract sources if requested
        sources = []
        if include_sources and result.get("retriever", {}).get("documents"):
            for doc in result["retriever"]["documents"]:
                source = DocumentSource(
                    content=doc.content[:500],  # Truncate long documents
                    metadata=doc.meta,
                    score=getattr(doc, 'score', 0.0)
                )
                sources.append(source)
        
        return answer, sources
    
    def get_document_count(self) -> int:
        """Get the number of documents in the store.
        
        Returns:
            Document count
        """
        return self.document_store.count_documents()
    
    def clear_documents(self):
        """Clear all documents from the store."""
        self.document_store.delete_documents()


def create_sample_documents() -> List[dict]:
    """Create sample documents for testing.
    
    Returns:
        List of sample documents
    """
    return [
        {
            "content": "LiteLLM is a unified interface for calling LLM APIs. It supports OpenAI, Anthropic, Cohere, and many other providers through a single API.",
            "metadata": {"source": "litellm_docs", "topic": "llm_providers"}
        },
        {
            "content": "Haystack is an open-source framework for building search and QA systems. It provides modular components for building RAG pipelines.",
            "metadata": {"source": "haystack_docs", "topic": "rag_frameworks"}
        },
        {
            "content": "FastAPI is a modern Python web framework for building APIs. It uses Pydantic for data validation and provides automatic OpenAPI documentation.",
            "metadata": {"source": "fastapi_docs", "topic": "web_frameworks"}
        },
        {
            "content": "Pydantic is a data validation library for Python that uses type hints. It provides BaseModel for creating structured data contracts.",
            "metadata": {"source": "pydantic_docs", "topic": "data_validation"}
        },
        {
            "content": "Model routing is the practice of directing different types of queries to different LLM models based on their complexity, cost, and capabilities.",
            "metadata": {"source": "ml_patterns", "topic": "model_management"}
        },
    ]
