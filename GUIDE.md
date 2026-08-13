# Build a LiteLLM-backed RAG Pipeline with Haystack

This guide demonstrates how to build a minimal RAG pipeline with:
- **LiteLLM** as a unified LLM gateway
- **Haystack** for RAG orchestration  
- **Intent classification** before model routing
- **Model router** that selects models based on query complexity
- **Pydantic** for all data contracts
- **FastAPI** for the API endpoint

## Architecture Overview

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User      │────▶│  FastAPI         │────▶│  Intent         │
│   Request   │     │  Endpoint        │     │  Classifier     │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                      │
                                                      ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   LLM       │◀────│  Model Router    │◀────│  Classification │
│  Response   │     │  (Tier Selection)│     │  Result         │
└──────┬──────┘     └──────────────────┘     └─────────────────┘
       │
       ▼
┌─────────────┐
│   LiteLLM   │
│   Gateway   │
│ (Unified    │
│  Interface) │
└─────────────┘
```

## Step 1: Set Up LiteLLM Gateway

LiteLLM provides a unified OpenAI-compatible API for multiple LLM providers.

### Install LiteLLM Proxy

```bash
pip install litellm[proxy]
```

### Configure LiteLLM

Create `litellm_config.yaml`:

```yaml
model_list:
  - model_name: gpt-3.5-turbo
    litellm_params:
      model: openai/gpt-3.5-turbo
      api_key: os.environ/OPENAI_API_KEY
      
  - model_name: gpt-4
    litellm_params:
      model: openai/gpt-4
      api_key: os.environ/OPENAI_API_KEY
      
  - model_name: gpt-4-turbo
    litellm_params:
      model: openai/gpt-4-turbo
      api_key: os.environ/OPENAI_API_KEY

general_settings:
  master_key: sk-1234
```

### Run LiteLLM Proxy

```bash
export OPENAI_API_KEY=your-key-here
litellm --config litellm_config.yaml
```

The proxy runs at `http://localhost:4000` by default.

## Step 2: Define Pydantic Data Contracts

All data structures use Pydantic for validation:

```python
# app/schemas.py
from pydantic import BaseModel, Field
from enum import Enum

class IntentType(str, Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"
    TECHNICAL = "technical"
    CREATIVE = "creative"

class ModelTier(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    ADVANCED = "advanced"

class RAGRequest(BaseModel):
    query: str
    include_sources: bool = True
    max_tokens: int = 512

class IntentClassification(BaseModel):
    intent_type: IntentType
    confidence: float
    reasoning: str | None

class ModelRoutingDecision(BaseModel):
    selected_model: str
    model_tier: ModelTier
    routing_reason: str

class RAGResponse(BaseModel):
    answer: str
    model_used: str
    intent: IntentClassification | None
    sources: list | None
    processing_time_ms: float
```

## Step 3: Build the LiteLLM Gateway Client

```python
# app/gateway.py
import httpx
from app.schemas import ModelTier

class LiteLLMGateway:
    def __init__(self, settings):
        self.base_url = settings.litellm_base_url
        self.api_key = settings.litellm_api_key
        self.settings = settings
    
    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Map tier to actual model name."""
        mapping = {
            ModelTier.FAST: self.settings.fast_model,
            ModelTier.BALANCED: self.settings.balanced_model,
            ModelTier.ADVANCED: self.settings.advanced_model,
        }
        return mapping.get(tier, self.settings.balanced_model)
    
    async def generate_completion(self, messages, model, max_tokens=512):
        """Call LiteLLM proxy for completions."""
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                }
            )
            return response.json()
```

## Step 4: Implement Intent Classifier

```python
# app/intent_classifier.py
from app.schemas import IntentType, IntentClassification

class IntentClassifier:
    def __init__(self, settings, gateway):
        self.settings = settings
        self.gateway = gateway
    
    async def classify(self, query: str) -> IntentClassification:
        """Classify query using LLM analysis."""
        
        system_prompt = """Classify queries as:
        - SIMPLE: Basic factual questions
        - COMPLEX: Multi-step reasoning
        - TECHNICAL: Programming/engineering
        - CREATIVE: Writing/brainstorming
        
        Respond in JSON: {"intent_type": "...", "confidence": 0.0-1.0, "reasoning": "..."}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Classify: {query}"}
        ]
        
        response = await self.gateway.generate_completion(
            messages=messages,
            model=self.settings.classifier_model,
            max_tokens=150,
            temperature=0.3
        )
        
        # Parse and return IntentClassification
        # ... parsing logic ...
```

## Step 5: Implement Model Router

```python
# app/model_router.py
from app.schemas import ModelTier, ModelRoutingDecision

class ModelRouter:
    def __init__(self, settings, gateway):
        self.settings = settings
        self.gateway = gateway
        
        self.intent_to_tier = {
            IntentType.SIMPLE: ModelTier.FAST,
            IntentType.COMPLEX: ModelTier.ADVANCED,
            IntentType.TECHNICAL: ModelTier.BALANCED,
            IntentType.CREATIVE: ModelTier.BALANCED,
        }
    
    def route(self, intent: IntentClassification) -> ModelRoutingDecision:
        """Route classified intent to appropriate model."""
        
        # Base tier from intent
        tier = self.intent_to_tier.get(intent.intent_type, ModelTier.BALANCED)
        
        # Upgrade for high-confidence complex/technical
        if intent.confidence >= 0.85:
            if intent.intent_type in [IntentType.TECHNICAL, IntentType.COMPLEX]:
                tier = ModelTier.ADVANCED
        
        # Get actual model name
        model = self.gateway.get_model_for_tier(tier)
        
        return ModelRoutingDecision(
            selected_model=model,
            model_tier=tier,
            routing_reason=f"Routed based on {intent.intent_type.value} intent"
        )
```

## Step 6: Build Haystack RAG Pipeline

```python
# app/rag_pipeline.py
from haystack import Pipeline
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder

class RAGPipeline:
    def __init__(self, settings, litellm_base_url):
        self.document_store = InMemoryDocumentStore()
        self.pipeline = self._build_pipeline(litellm_base_url)
    
    def _build_pipeline(self, base_url):
        pipeline = Pipeline()
        
        pipeline.add_component("retriever", 
            InMemoryEmbeddingRetriever(document_store=self.document_store))
        
        pipeline.add_component("prompt_builder", 
            PromptBuilder(template="""
            Context: {% for doc in documents %}{{ doc.content }}{% endfor %}
            Question: {{ query }}
            Answer:
            """))
        
        pipeline.add_component("generator",
            OpenAIGenerator(api_base_url=base_url, api_key="not-needed"))
        
        pipeline.connect("retriever.documents", "prompt_builder.documents")
        pipeline.connect("prompt_builder.prompt", "generator.prompt")
        
        return pipeline
    
    async def query(self, query, model, top_k=5):
        """Execute RAG query."""
        result = self.pipeline.run({
            "retriever": {"query": query},
            "prompt_builder": {"query": query},
        })
        return result["generator"]["replies"][0]
```

## Step 7: Create FastAPI Endpoint

```python
# app/main.py
from fastapi import FastAPI
from app.schemas import RAGRequest, RAGResponse
import time

app = FastAPI()

@app.post("/rag/query", response_model=RAGResponse)
async def rag_query(request: RAGRequest):
    start_time = time.time()
    
    # 1. Classify intent
    intent = await intent_classifier.classify(request.query)
    
    # 2. Route to model
    routing = model_router.route(intent)
    
    # 3. Execute RAG
    answer = await rag_pipeline.query(
        query=request.query,
        model=routing.selected_model
    )
    
    return RAGResponse(
        answer=answer,
        model_used=routing.selected_model,
        intent=intent,
        processing_time_ms=(time.time() - start_time) * 1000
    )
```

## Step 8: Run the Service

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export RAG_LITELLM_BASE_URL=http://localhost:4000
export OPENAI_API_KEY=your-key

# Run the API
uvicorn app.main:app --reload
```

## Test the Pipeline

```bash
# Simple query (routes to fast model)
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Python?", "include_sources": true}'

# Complex query (routes to advanced model)
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare and contrast microservices vs monolithic architecture"}'
```

## Key Benefits

1. **Cost Optimization**: Simple queries use cheaper models
2. **Performance**: Fast responses for straightforward questions
3. **Quality**: Complex queries get advanced model capabilities
4. **Flexibility**: Easy to add new providers via LiteLLM
5. **Type Safety**: Full Pydantic validation throughout

## Next Steps

- Add persistent vector store (Qdrant, Weaviate, Pinecone)
- Implement document ingestion pipeline
- Add streaming responses
- Configure retry logic and fallbacks
- Add monitoring and observability
