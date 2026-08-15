# Haystack RAG Pipeline Design

## Pipeline Architecture

```python
from haystack import Document, Pipeline
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.routers import TransformersTextRouter
from haystack.document_stores.in_memory import InMemoryDocumentStore
from sentence_transformers import SentenceTransformer
from app.core.protocol import DocumentStore as DocumentStoreProtocol
from typing import List

class HaystackRAGPipeline:
    """Two-stage RAG pipeline with vector retrieval and reranking."""
    
    def __init__(self):
        # Initialize document store
        self.document_store = InMemoryDocumentStore(
            embedding_similarity_function="cosine"
        )
        
        # Initialize embedding model (fast, free)
        self.embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Build retrieval pipeline
        self.retrieval_pipeline = self._build_retrieval_pipeline()
        
        # Initialize reranker
        self.reranker = self._load_reranker()
    
    def _build_retrieval_pipeline(self) -> Pipeline:
        """Build vector retrieval pipeline."""
        pipeline = Pipeline()
        
        # Add retriever component
        retriever = InMemoryEmbeddingRetriever(
            document_store=self.document_store,
            top_k=10,  # Retrieve 10 candidates
            scale_score=True
        )
        
        pipeline.add_component("retriever", retriever)
        return pipeline
    
    def _load_reranker(self):
        """Load cross-encoder reranker model."""
        from sentence_transformers import CrossEncoder
        
        return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    async def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the store with embeddings."""
        # Generate embeddings
        texts = [doc.content for doc in documents]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        
        # Attach embeddings to documents
        for doc, emb in zip(documents, embeddings):
            doc.embedding = emb
        
        # Write to store
        self.document_store.write_documents(documents)
    
    async def search_and_rerank(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Document]:
        """Two-stage retrieval: vector search + reranking."""
        # Stage 1: Vector retrieval (top 10)
        query_embedding = self.embedding_model.encode(
            [query], 
            convert_to_numpy=True
        )[0]
        
        retrieval_result = await self.retrieval_pipeline.run({
            "retriever": {
                "query_embedding": query_embedding,
                "top_k": 10
            }
        })
        
        candidate_docs = retrieval_result["retriever"]["documents"]
        
        if not candidate_docs:
            return []
        
        # Stage 2: Reranking
        pairs = [(query, doc.content) for doc in candidate_docs]
        scores = self.reranker.predict(pairs)
        
        # Sort by score and take top_k
        scored_docs = list(zip(candidate_docs, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Attach rerank scores
        reranked_docs = []
        for doc, score in scored_docs[:top_k]:
            doc.score = float(score)
            reranked_docs.append(doc)
        
        return reranked_docs
    
    async def count(self) -> int:
        """Get total document count."""
        return self.document_store.count_documents()
```

## Cost Analysis

```python
# Retrieval costs (per query)
EMBEDDING_COST = 0.0  # Local model, free
RERANKER_COST = 0.0   # Local model, free

# vs API-based alternatives:
# - OpenAI embeddings: $0.0001 per query (1000 tokens avg)
# - Cohere reranker: $0.0005 per query (10 candidates)
# Total savings: ~$0.0006 per query

# At 10,000 queries/day:
# - Local: $0/day
# - API-based: ~$6/day
# Monthly savings: ~$180
```

## Usage Example

```python
# Initialize pipeline
rag_pipeline = HaystackRAGPipeline()

# Add documents
docs = [
    Document(content="Python is a programming language..."),
    Document(content="Machine learning uses algorithms..."),
]
await rag_pipeline.add_documents(docs)

# Search with reranking
results = await rag_pipeline.search_and_rerank(
    query="What is Python?",
    top_k=3
)

for i, doc in enumerate(results, 1):
    print(f"{i}. Score: {doc.score:.3f}")
    print(f"   Content: {doc.content[:100]}...")
```
